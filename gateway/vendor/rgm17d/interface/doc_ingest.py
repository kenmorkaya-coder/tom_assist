"""
B8: Document Ingestion MVP

Minimal implementation for ingesting TXT and PDF documents into LTM as reference_doc anchors.

Features:
- TXT file reading
- PDF file reading (requires pypdf)
- Text chunking (configurable size)
- Summarization (placeholder - integrate with LLM)
- Memory anchor creation with source_ref

Usage:
    from interface.doc_ingest import ingest_document, DocIngestResult

    result = ingest_document("/path/to/file.pdf", controller)
    print(f"Ingested {result.chunks_created} chunks, {result.anchors_written} anchors")
"""

import hashlib
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
import time


# =============================================================================
# CONFIGURATION
# =============================================================================

DEFAULT_CHUNK_SIZE = 1000  # characters per chunk
DEFAULT_CHUNK_OVERLAP = 100  # overlap between chunks
MAX_SUMMARY_LENGTH = 200  # max chars for summary
SUPPORTED_EXTENSIONS = {
    # Documents
    ".txt", ".pdf", ".md",
    ".doc", ".docx",                       # Word (legacy + modern)
    ".xls", ".xlsx", ".xlsm",             # Excel (legacy + modern + macro)
    ".ppt", ".pptx",                       # PowerPoint (legacy + modern)
    # Email
    ".eml", ".msg",
    # Markup / data
    ".csv", ".tsv", ".json", ".jsonl", ".ndjson",
    ".html", ".htm", ".mht",              # Web pages + MHTML archives
    ".xml", ".svg",
    ".yaml", ".yml", ".rst", ".rtf", ".log",
    # Config
    ".ini", ".cfg", ".conf", ".toml", ".env", ".properties",
    # CAD / engineering
    ".dxf",                                # DXF is text-based
    # Documentation
    ".tex", ".bib", ".adoc",
    # DevOps / infrastructure
    ".tf", ".hcl", ".proto", ".gradle", ".dockerfile",
    # Source code - systems
    ".py", ".rb", ".go", ".java", ".c", ".cpp", ".h", ".hpp",
    ".cs", ".fs", ".rs", ".swift", ".kt", ".scala", ".m",
    ".zig", ".nim", ".dart", ".lua", ".pl", ".php",
    ".groovy", ".r", ".ex", ".exs", ".erl", ".hs", ".clj",
    # Source code - web/frontend
    ".js", ".ts", ".jsx", ".tsx", ".vue", ".svelte",
    ".css", ".scss", ".sass", ".less",
    ".graphql", ".gql",
    # Source code - shell/scripting
    ".sh", ".bat", ".ps1", ".vb", ".vbs",
    # Source code - data/query
    ".sql",
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class DocChunk:
    """A chunk of document text."""
    chunk_id: str
    content: str
    start_char: int
    end_char: int
    page_num: Optional[int] = None  # For PDFs


@dataclass
class HeadingChunk:
    """A chunk of document text split by heading (for MD files)."""
    chunk_id: str
    section_id: str          # e.g., "7" for "## 7. Memory Architecture"
    section_title: str       # e.g., "Memory Architecture"
    heading_level: int       # 1 for #, 2 for ##, 3 for ###
    content: str
    start_line: int
    end_line: int
    parent_section: Optional[str] = None


@dataclass
class DocIngestResult:
    """Result of document ingestion."""
    success: bool
    source_path: str
    source_ref: str  # URI or path
    content_hash: str
    total_chars: int
    chunks_created: int
    anchors_written: int
    anchor_ids: List[str] = field(default_factory=list)
    error: Optional[str] = None
    telemetry: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MDIngestResult(DocIngestResult):
    """Extended result for markdown ingestion with heading-based chunking."""
    doc_id: str = ""
    sections_found: int = 0
    heading_chunks: List[HeadingChunk] = field(default_factory=list)


# =============================================================================
# PR4: BLOCK TYPE AND HEADING PATH HELPERS
# =============================================================================

def infer_block_type(content: str) -> str:
    """
    Infer block_type from content structure for PR4 evidence policy.

    Returns one of:
    - "code_kv": key: value or key = value patterns
    - "table_cell": | delimited content
    - "definition_list": term: definition
    - "list_item": * or - prefixed
    - "prose": default
    """
    content = content.strip()

    # Check for code key-value (e.g., "threshold: 0.2" or "PARAM = 5")
    if re.match(r'^[A-Za-z_]\w*\s*[:=]\s*.+$', content):
        return "code_kv"

    # Check for table cell (pipe-delimited)
    if '|' in content and content.count('|') >= 2:
        return "table_cell"

    # Check for list item
    if re.match(r'^[*\-]\s+', content):
        return "list_item"

    # Check for definition list (term: definition format)
    if re.match(r'^.{1,50}:\s+.+', content) and ':' in content[:60]:
        return "definition_list"

    return "prose"


def construct_heading_path(
    section_title: str,
    section_id: str,
    parent_section: Optional[str] = None,
) -> str:
    """
    Construct heading_path from section info for PR4 evidence provenance.

    Args:
        section_title: Current section title
        section_id: Current section ID
        parent_section: Parent section ID (if nested)

    Returns:
        Heading path string, e.g., "7. Memory Architecture" or "7 > 7.1 RGM"
    """
    if parent_section:
        return f"{parent_section} > {section_id}. {section_title}"
    elif section_id and section_id != "INTRO":
        return f"{section_id}. {section_title}"
    else:
        return section_title


# =============================================================================
# SEI EXTRACTION HELPERS
# =============================================================================

def _find_section_for_line(
    line_num: int,
    chunks: List["HeadingChunk"],
) -> str:
    """Map a line number to the section_id of the containing HeadingChunk."""
    for chunk in reversed(chunks):
        if line_num >= chunk.start_line:
            return chunk.section_id
    return ""


def _extract_sei_facts(
    heading_chunks: List["HeadingChunk"],
    full_text: str,
) -> Dict[str, Dict[str, Any]]:
    """
    Extract key-value facts from full document text for SEI.

    Scans every line for patterns like:
        - `min_health_for_llm`: 0.20
        - min_stability_for_llm = 0.25
        - some_threshold: 75%

    Returns dict keyed by variable name.
    """
    fact_pattern = re.compile(
        r'^[\s\-*]*`?([a-zA-Z_]\w+)`?\s*[:=]\s*([\d.]+(?:\s*%)?)\s*$'
    )

    facts: Dict[str, Dict[str, Any]] = {}
    lines = full_text.split("\n")

    for line_num, line in enumerate(lines, 1):
        match = fact_pattern.match(line)
        if match:
            key = match.group(1)
            value = match.group(2).strip()
            section_id = _find_section_for_line(line_num, heading_chunks)
            facts[key] = {
                "value": value,
                "section_id": section_id,
                "line": line_num,
                "raw": line.strip(),
            }

    return facts


def _extract_sei_headings(full_text: str) -> List[Dict[str, Any]]:
    """
    Extract ALL markdown headings with section hierarchy for SEI.

    Unlike chunk_markdown_by_headings() which only creates chunks at level <= 2,
    this extracts every heading at every level to support counting queries
    like "how many ### subsections under ## 12?"
    """
    heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    num_pattern = re.compile(r'^(\d+(?:\.\d+)*)\s*[.\-:)]\s*(.+)$')

    headings: List[Dict[str, Any]] = []
    parent_by_level: Dict[int, str] = {}  # level -> section_id (numeric prefix)

    for match in heading_pattern.finditer(full_text):
        level = len(match.group(1))
        raw_title = match.group(2).strip()

        num_match = num_pattern.match(raw_title)
        if num_match:
            section_id = num_match.group(1)   # e.g., "12.1"
            title = num_match.group(2).strip()
        else:
            section_id = re.sub(r'[^a-zA-Z0-9]+', '_', raw_title)[:20]
            title = raw_title

        parent = parent_by_level.get(level - 1) if level > 1 else None

        # Update parent tracking
        parent_by_level[level] = section_id
        # Clear deeper levels
        for deeper in list(parent_by_level.keys()):
            if deeper > level:
                del parent_by_level[deeper]

        headings.append({
            "section_id": section_id,
            "title": title,
            "level": level,
            "parent": parent,
        })

    return headings


def _extract_dsi_skills(
    heading_chunks: List[HeadingChunk],
    doc_id: str = "",
) -> List[Dict[str, Any]]:
    """Extract Document Skills Index entries with subsection offsets.

    For each ### (level 3+) subsection within a parent ## chunk:
    1. Compute character offsets within the parent chunk's .content
    2. Extract topic terms from title + bold terms + list leaders
    3. Map to parent HeadingChunk section_id

    Offsets are computed against the actual stored chunk content,
    so chunk.content[start:end] works correctly.
    """
    import logging
    _log = logging.getLogger(__name__)

    subsection_pattern = re.compile(r'^(#{3,6})\s+(.+)$', re.MULTILINE)
    bold_pattern = re.compile(r'\*\*([^*]+)\*\*')
    list_leader_pattern = re.compile(r'^\d+\.\s+\*?\*?([^:*\n]+)', re.MULTILINE)
    num_pattern = re.compile(r'^(\d+(?:\.\d+)*)\s*[.\-:)]\s*(.+)$')

    skills: List[Dict[str, Any]] = []

    for chunk in heading_chunks:
        content = chunk.content
        if not content:
            continue

        # Find all ### subsection headings within this chunk's content
        matches = list(subsection_pattern.finditer(content))
        if not matches:
            continue

        for i, match in enumerate(matches):
            level = len(match.group(1))
            raw_title = match.group(2).strip()
            content_start = match.start()
            content_end = matches[i + 1].start() if i + 1 < len(matches) else len(content)

            # Parse section_id from numbered heading
            num_match = num_pattern.match(raw_title)
            if num_match:
                section_id = num_match.group(1)
                title = num_match.group(2).strip()
            else:
                section_id = re.sub(r'[^a-zA-Z0-9]+', '_', raw_title)[:20]
                title = raw_title

            # Extract subsection text for topic mining
            subsection_text = content[content_start:content_end]

            # Extract topics from multiple sources
            # Uses Unicode tokenisation — works for any language
            import unicodedata
            def _unicode_tokens(text: str) -> List[str]:
                norm = unicodedata.normalize("NFKC", text).casefold()
                return [t for t in re.findall(r'[\w]+', norm, re.UNICODE) if len(t) >= 2]

            topics: List[str] = []
            seen_topics: set = set()

            # Source 1: Title words (all tokens, IDF handles weighting)
            for w in _unicode_tokens(title):
                if w not in seen_topics:
                    topics.append(w)
                    seen_topics.add(w)

            # Source 2: Bold terms
            for bold_match in bold_pattern.finditer(subsection_text):
                bold_text = bold_match.group(1).strip()
                for w in _unicode_tokens(bold_text):
                    if w not in seen_topics:
                        topics.append(w)
                        seen_topics.add(w)

            # Source 3: Numbered list leaders (first 3 tokens per item)
            for list_match in list_leader_pattern.finditer(subsection_text):
                leader = list_match.group(1).strip()
                for w in _unicode_tokens(leader)[:3]:
                    if w not in seen_topics:
                        topics.append(w)
                        seen_topics.add(w)

            if not topics:
                continue

            # Verification: assert slice begins with expected heading text
            slice_text = content[content_start:content_end]
            title_lower = title.lower()
            verified = title_lower in slice_text[:150].lower()

            if not verified:
                _log.warning(
                    "DSI offset mismatch for '%s' in chunk %s, skipping",
                    title, chunk.section_id,
                )
                continue

            # All tokens from full subsection content (for IDF computation)
            # Uses same Unicode tokenisation as persistent_store._dsi_tokenize
            content_tokens = list(set(_unicode_tokens(subsection_text)))

            skills.append({
                "section_id": section_id,
                "doc_id": doc_id,
                "parent_chunk_id": chunk.section_id,
                "title": title,
                "level": level,
                "content_start": content_start,
                "content_end": content_end,
                "verified": True,
                "topics": topics,
                "content_tokens": content_tokens,
            })

    return skills


# =============================================================================
# TEXT EXTRACTION
# =============================================================================

def read_txt_file(file_path: str) -> Tuple[str, Optional[str]]:
    """Read text from a text-based file with encoding fallback."""
    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read(), None
        except UnicodeDecodeError:
            continue
        except Exception as e:
            return "", str(e)
    return "", "Could not decode file with any supported encoding"


def read_html_file(file_path: str) -> Tuple[str, Optional[str]]:
    """Read text from an HTML/MHT file, stripping tags."""
    from html.parser import HTMLParser

    class _TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self._parts: list = []
            self._skip = False

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style", "noscript"):
                self._skip = True

        def handle_endtag(self, tag):
            if tag in ("script", "style", "noscript"):
                self._skip = False
            if tag in ("p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"):
                self._parts.append("\n")

        def handle_data(self, data):
            if not self._skip:
                self._parts.append(data)

    try:
        text, err = read_txt_file(file_path)
        if err:
            return "", f"HTML read error: {err}"
        extractor = _TextExtractor()
        extractor.feed(text)
        result = "".join(extractor._parts).strip()
        result = re.sub(r'\n{3,}', '\n\n', result)
        return result, None
    except Exception as e:
        return "", f"HTML read error: {e}"


def read_csv_file(file_path: str, delimiter: str = ",") -> Tuple[str, Optional[str]]:
    """Read text from a CSV/TSV file as pipe-delimited table."""
    import csv
    MAX_ROWS = 10000

    try:
        text, err = read_txt_file(file_path)
        if err:
            return "", f"CSV read error: {err}"
        parts = []
        reader = csv.reader(text.splitlines(), delimiter=delimiter)
        for i, row in enumerate(reader):
            if i >= MAX_ROWS:
                parts.append(f"... (truncated at {MAX_ROWS} rows)")
                break
            parts.append("| " + " | ".join(cell.strip() for cell in row) + " |")
        return "\n".join(parts), None
    except Exception as e:
        return "", f"CSV read error: {e}"


def read_pdf_file(file_path: str) -> Tuple[str, Optional[str]]:
    """
    Read text from a PDF file.
    Primary: pypdf. Fallback: pdfplumber (if installed).
    """
    pypdf_available = False
    page_count = 0

    # --- Try pypdf first ---
    try:
        try:
            from pypdf import PdfReader
            pypdf_available = True
        except ImportError:
            try:
                from PyPDF2 import PdfReader
                pypdf_available = True
            except ImportError:
                pass

        if pypdf_available:
            reader = PdfReader(file_path)
            page_count = len(reader.pages)
            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text and text.strip():
                    text_parts.append(text)
            if text_parts:
                return "\n\n".join(text_parts), None
    except Exception:
        pass  # pypdf failed — try pdfplumber below

    # --- Fallback: pdfplumber ---
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            page_count = len(pdf.pages)
            text_parts = []
            for page in pdf.pages:
                text = page.extract_text()
                if text and text.strip():
                    text_parts.append(text)
            if text_parts:
                return "\n\n".join(text_parts), None
    except ImportError:
        pass  # pdfplumber not installed
    except Exception:
        pass  # pdfplumber also failed

    # --- Neither produced text ---
    if not pypdf_available:
        return "", "PDF support requires pypdf: pip install pypdf"
    if page_count > 0:
        return "", (
            f"PDF has {page_count} page(s) but no extractable text. "
            "It may contain scanned images. OCR is not yet supported."
        )
    return "", "PDF appears to be empty or corrupt."


def read_docx_file(file_path: str) -> Tuple[str, Optional[str]]:
    """
    Read text from a DOCX file.
    Requires python-docx: pip install python-docx
    """
    try:
        from docx import Document
    except ImportError:
        return "", "DOCX support requires python-docx: pip install python-docx"

    try:
        doc = Document(file_path)
        parts = []

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            # Convert heading styles to markdown syntax
            style_name = (para.style.name or "").lower()
            if style_name.startswith("heading"):
                try:
                    level = int(style_name.replace("heading", "").strip())
                    parts.append(f"{'#' * level} {text}")
                except ValueError:
                    parts.append(text)
            else:
                parts.append(text)

        # Extract tables as pipe-delimited rows
        for table in doc.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                parts.append("| " + " | ".join(cells) + " |")

        return "\n\n".join(parts), None
    except Exception as e:
        return "", f"DOCX read error: {e}"


def read_xlsx_file(file_path: str) -> Tuple[str, Optional[str]]:
    """
    Read text from an XLSX file.
    Requires openpyxl: pip install openpyxl
    """
    try:
        from openpyxl import load_workbook
    except ImportError:
        return "", "XLSX support requires openpyxl: pip install openpyxl"

    try:
        wb = load_workbook(file_path, read_only=True, data_only=True)
        parts = []

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            parts.append(f"## {sheet_name}")

            for row in ws.iter_rows(values_only=True):
                cells = [str(cell) if cell is not None else "" for cell in row]
                if any(c.strip() for c in cells):
                    parts.append("| " + " | ".join(cells) + " |")

        wb.close()
        return "\n\n".join(parts), None
    except Exception as e:
        return "", f"XLSX read error: {e}"


def read_pptx_file(file_path: str) -> Tuple[str, Optional[str]]:
    """
    Read text from a PPTX file.
    Requires python-pptx: pip install python-pptx
    """
    try:
        from pptx import Presentation
    except ImportError:
        return "", "PPTX support requires python-pptx: pip install python-pptx"

    try:
        prs = Presentation(file_path)
        parts = []

        for slide_num, slide in enumerate(prs.slides, 1):
            parts.append(f"## Slide {slide_num}")
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        text = paragraph.text.strip()
                        if text:
                            parts.append(text)

        return "\n\n".join(parts), None
    except Exception as e:
        return "", f"PPTX read error: {e}"


def read_xls_file(file_path: str) -> Tuple[str, Optional[str]]:
    """
    Read text from a legacy .xls (pre-2007) Excel file.
    Requires xlrd: pip install xlrd
    """
    try:
        import xlrd
    except ImportError:
        return "", "Legacy .xls support requires xlrd: pip install xlrd"

    try:
        wb = xlrd.open_workbook(file_path)
        parts = []

        for sheet in wb.sheets():
            parts.append(f"## {sheet.name}")
            for row_idx in range(sheet.nrows):
                cells = [str(sheet.cell_value(row_idx, col)) for col in range(sheet.ncols)]
                if any(c.strip() for c in cells):
                    parts.append("| " + " | ".join(cells) + " |")

        return "\n\n".join(parts), None
    except Exception as e:
        return "", f"XLS read error: {e}"


def read_doc_file(file_path: str) -> Tuple[str, Optional[str]]:
    """
    Read text from a legacy .doc (pre-2007) Word file.
    Tries textract first, then basic binary text extraction.
    """
    # Try textract (if installed)
    try:
        import textract
        text = textract.process(file_path).decode("utf-8", errors="replace")
        if text.strip():
            return text, None
    except ImportError:
        pass
    except Exception:
        pass

    # Fallback: extract readable text from binary OLE stream
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        # .doc files store text as UTF-16LE in the binary stream
        # Extract runs of printable characters
        text = data.decode("utf-16-le", errors="ignore")
        # Keep only printable chars and whitespace
        cleaned = re.sub(r'[^\x20-\x7E\n\r\t\u00A0-\uFFFF]+', ' ', text)
        cleaned = re.sub(r' {3,}', '\n', cleaned)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()
        if len(cleaned) > 100:
            return cleaned, None
    except Exception:
        pass

    return "", (
        "Legacy .doc format could not be parsed. "
        "Install textract (pip install textract) or convert to .docx format."
    )


def read_ppt_file(file_path: str) -> Tuple[str, Optional[str]]:
    """
    Read text from a legacy .ppt (pre-2007) PowerPoint file.
    Requires textract: pip install textract
    """
    # Try textract (if installed)
    try:
        import textract
        text = textract.process(file_path).decode("utf-8", errors="replace")
        if text.strip():
            return text, None
    except ImportError:
        pass
    except Exception:
        pass

    return "", (
        "Legacy .ppt format requires textract: pip install textract. "
        "Alternatively, convert to .pptx format."
    )


def read_eml_file(file_path: str) -> Tuple[str, Optional[str]]:
    """Read text from an .eml email file using stdlib email module."""
    import email
    import email.policy

    try:
        with open(file_path, "rb") as f:
            msg = email.message_from_binary_file(f, policy=email.policy.default)

        parts = []
        # Header metadata
        for header in ("Subject", "From", "To", "Date"):
            val = msg.get(header)
            if val:
                parts.append(f"{header}: {val}")

        parts.append("")  # blank line before body

        # Body text
        body = msg.get_body(preferencelist=("plain", "html"))
        if body:
            content = body.get_content()
            content_type = body.get_content_type()
            if content_type == "text/html":
                # Strip HTML tags for clean text
                stripped, _ = read_html_file.__wrapped__(content) if hasattr(read_html_file, '__wrapped__') else (content, None)
                # Use inline HTML stripping
                from html.parser import HTMLParser

                class _Strip(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self._t: list = []
                    def handle_data(self, d):
                        self._t.append(d)

                s = _Strip()
                s.feed(content)
                content = "".join(s._t)
            parts.append(content.strip())

        return "\n".join(parts), None
    except Exception as e:
        return "", f"EML read error: {e}"


def read_msg_file(file_path: str) -> Tuple[str, Optional[str]]:
    """
    Read text from an Outlook .msg email file.
    Requires extract-msg: pip install extract-msg
    """
    try:
        import extract_msg
    except ImportError:
        return "", "Outlook .msg support requires extract-msg: pip install extract-msg"

    try:
        msg = extract_msg.Message(file_path)
        parts = []
        if msg.subject:
            parts.append(f"Subject: {msg.subject}")
        if msg.sender:
            parts.append(f"From: {msg.sender}")
        if msg.to:
            parts.append(f"To: {msg.to}")
        if msg.date:
            parts.append(f"Date: {msg.date}")
        parts.append("")
        if msg.body:
            parts.append(msg.body.strip())
        msg.close()
        return "\n".join(parts), None
    except Exception as e:
        return "", f"MSG read error: {e}"


def extract_text(file_path: str) -> Tuple[str, Optional[str]]:
    """Extract text from supported file types."""
    ext = os.path.splitext(file_path)[1].lower()

    # Library-dependent formats (dedicated readers)
    if ext == ".pdf":
        return read_pdf_file(file_path)
    elif ext == ".docx":
        return read_docx_file(file_path)
    elif ext == ".doc":
        return read_doc_file(file_path)
    elif ext in {".xlsx", ".xlsm"}:
        return read_xlsx_file(file_path)
    elif ext == ".xls":
        return read_xls_file(file_path)
    elif ext == ".pptx":
        return read_pptx_file(file_path)
    elif ext == ".ppt":
        return read_ppt_file(file_path)
    elif ext == ".eml":
        return read_eml_file(file_path)
    elif ext == ".msg":
        return read_msg_file(file_path)
    # Structured text formats (stdlib readers)
    elif ext in {".html", ".htm", ".mht"}:
        return read_html_file(file_path)
    elif ext == ".csv":
        return read_csv_file(file_path, delimiter=",")
    elif ext == ".tsv":
        return read_csv_file(file_path, delimiter="\t")
    # Everything else in SUPPORTED_EXTENSIONS is plain text
    elif ext in SUPPORTED_EXTENSIONS:
        return read_txt_file(file_path)
    else:
        return "", f"Unsupported file type: {ext}"


# =============================================================================
# CHUNKING
# =============================================================================

def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[DocChunk]:
    """
    Split text into overlapping chunks.

    Args:
        text: Full document text
        chunk_size: Max characters per chunk
        overlap: Characters to overlap between chunks

    Returns:
        List of DocChunk objects
    """
    if not text:
        return []

    chunks = []
    start = 0
    chunk_num = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence end in last 20% of chunk
            search_start = max(start, end - int(chunk_size * 0.2))
            for sep in [". ", ".\n", "? ", "?\n", "! ", "!\n"]:
                last_sep = text.rfind(sep, search_start, end)
                if last_sep > start:
                    end = last_sep + len(sep)
                    break

        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(DocChunk(
                chunk_id=f"chunk_{chunk_num}",
                content=chunk_text,
                start_char=start,
                end_char=end,
            ))
            chunk_num += 1

        start = end - overlap if end < len(text) else end

    return chunks


# =============================================================================
# HEADING DETECTION FOR PLAIN TEXT (PDF, TXT)
# =============================================================================

def detect_headings_in_plain_text(
    text: str,
    *,
    source_hint: str = "pdf",
    min_confidence_headings: int = 3,
) -> Tuple[str, Dict[str, Any]]:
    """
    Detect heading patterns in plain text and enrich with markdown heading syntax.

    DOCX/PPTX/XLSX readers already emit markdown headings — this function handles
    PDF and TXT files that lack heading markup.

    Detection heuristics (deterministic, no LLM):
    1. Numbered sections: "1. Introduction", "2.1 Background", "Chapter 3: Methods"
    2. ALL CAPS lines: Short uppercase lines (5-80 chars) followed by content

    False positive guards:
    - TOC lines (dotted page refs) rejected
    - Short numeric titles (< 3 chars) rejected
    - Repeated headers/footers stripped
    - Legal boilerplate caps clustering filtered

    Returns:
        (enriched_text, detection_meta) where detection_meta includes:
        - headings_detected: int
        - detection_method: "numbered" | "caps" | "mixed" | "none"
        - lines_stripped: int
    """
    if not text or not text.strip():
        return text, {"headings_detected": 0, "detection_method": "none", "lines_stripped": 0}

    lines = text.split("\n")
    total_lines = len(lines)

    # --- Pre-pass: strip repeated headers/footers ---
    # If the same short line (< 60 chars) appears at 3+ page boundaries, strip it
    page_sep_indices = [i for i, ln in enumerate(lines) if ln.strip() == ""]
    line_counts: Dict[str, int] = {}
    for i, ln in enumerate(lines):
        stripped = ln.strip()
        if stripped and len(stripped) < 60:
            # Check if near a page boundary (blank line)
            near_boundary = any(abs(i - sep) <= 2 for sep in page_sep_indices)
            if near_boundary:
                line_counts[stripped] = line_counts.get(stripped, 0) + 1

    repeated_lines = {ln for ln, count in line_counts.items() if count >= 3}
    lines_stripped = 0
    if repeated_lines:
        cleaned = []
        for ln in lines:
            if ln.strip() in repeated_lines:
                lines_stripped += 1
            else:
                cleaned.append(ln)
        lines = cleaned

    # --- Detect headings ---
    # Regex patterns
    numbered_re = re.compile(
        r'^\s*(?:(?:Chapter|Section|Part)\s+)?(\d+(?:\.\d+)*)\s*[.\-:)]?\s+(.{3,})$'
    )
    caps_re = re.compile(r'^[A-Z][A-Z\s\d\-:,&]{4,78}$')
    toc_re = re.compile(r'\.{3,}\s*\d+\s*$')

    numbered_hits = []  # (line_index, level, full_match)
    caps_hits = []      # (line_index,)

    for i, ln in enumerate(lines):
        stripped = ln.strip()
        if not stripped:
            continue

        # Skip TOC lines
        if toc_re.search(stripped):
            continue

        # Check numbered sections
        m = numbered_re.match(stripped)
        if m:
            number_part = m.group(1)
            # Determine heading level from numbering depth
            depth = number_part.count(".")
            level = 2 if depth == 0 else 3  # top-level → ##, sub → ###
            numbered_hits.append((i, level, stripped))
            continue

        # Check ALL CAPS lines
        if caps_re.match(stripped) and len(stripped) >= 5:
            # Must not be all digits or punctuation
            alpha_chars = sum(1 for c in stripped if c.isalpha())
            if alpha_chars >= 3:
                caps_hits.append((i,))

    # --- Legal boilerplate caps filter ---
    # If > 50% of caps detections are in the first 10% of the document, filter those
    if caps_hits and total_lines > 0:
        first_10pct = total_lines * 0.1
        early_caps = [h for h in caps_hits if h[0] < first_10pct]
        if len(early_caps) > len(caps_hits) * 0.5 and len(caps_hits) > 2:
            # Only trust caps detections outside the first 10%
            caps_hits = [h for h in caps_hits if h[0] >= first_10pct]

    # --- Determine detection method ---
    total_headings = len(numbered_hits) + len(caps_hits)

    if total_headings < min_confidence_headings:
        return "\n".join(lines), {
            "headings_detected": total_headings,
            "detection_method": "none",
            "lines_stripped": lines_stripped,
        }

    if numbered_hits and caps_hits:
        method = "mixed"
    elif numbered_hits:
        method = "numbered"
    else:
        method = "caps"

    # --- Enrich lines with markdown heading syntax ---
    heading_line_indices = {}
    for (idx, level, _) in numbered_hits:
        heading_line_indices[idx] = level
    for (idx,) in caps_hits:
        heading_line_indices[idx] = 2  # ALL CAPS → ##

    enriched = []
    for i, ln in enumerate(lines):
        if i in heading_line_indices:
            level = heading_line_indices[i]
            prefix = "#" * level
            enriched.append(f"{prefix} {ln.strip()}")
        else:
            enriched.append(ln)

    return "\n".join(enriched), {
        "headings_detected": total_headings,
        "detection_method": method,
        "lines_stripped": lines_stripped,
    }


def chunk_markdown_by_headings(
    text: str,
    *,
    min_heading_level: int = 2,
    max_chunk_chars: int = 4000,  # Increased for B8 Type C (section 5 is large)
) -> List[HeadingChunk]:
    """
    Split markdown text into chunks based on heading structure.

    Args:
        text: Full markdown document text
        min_heading_level: Minimum heading level to treat as chunk boundary (2 = ##)
        max_chunk_chars: Maximum chars per chunk (truncate if exceeded)

    Returns:
        List of HeadingChunk objects, each representing a semantic section
    """
    if not text:
        return []

    lines = text.split("\n")
    chunks: List[HeadingChunk] = []

    # Regex to match markdown headings: # Title, ## Title, ### Title, etc.
    heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$')

    current_chunk: Optional[Dict[str, Any]] = None
    current_lines: List[str] = []
    current_start_line = 0

    def extract_section_id(title: str) -> str:
        """Extract section ID from title like '7. Memory Architecture' -> '7_MEMORY'"""
        # Try to extract leading number
        match = re.match(r'^(\d+(?:\.\d+)?)\s*[.\-:]\s*(.+)$', title)
        if match:
            num = match.group(1).replace(".", "_")
            rest = match.group(2).strip()
            # Create slug from first word
            slug = re.sub(r'[^a-zA-Z0-9]', '_', rest.split()[0].upper()) if rest else ""
            return f"{num}_{slug}" if slug else num
        # Fallback: slugify the title
        return re.sub(r'[^a-zA-Z0-9]+', '_', title.upper())[:20]

    def finalize_chunk():
        """Save current chunk if it has content."""
        nonlocal current_chunk, current_lines
        if current_chunk is not None and current_lines:
            content = "\n".join(current_lines).strip()
            if content:
                # Truncate if too long
                if len(content) > max_chunk_chars:
                    content = content[:max_chunk_chars] + "..."
                chunks.append(HeadingChunk(
                    chunk_id=f"section_{len(chunks)}",
                    section_id=current_chunk["section_id"],
                    section_title=current_chunk["section_title"],
                    heading_level=current_chunk["heading_level"],
                    content=content,
                    start_line=current_chunk["start_line"],
                    end_line=current_start_line - 1,
                    parent_section=current_chunk.get("parent_section"),
                ))
        current_lines = []

    parent_sections: Dict[int, str] = {}  # level -> section_id

    for line_num, line in enumerate(lines, 1):
        match = heading_pattern.match(line)

        if match:
            level = len(match.group(1))  # Count # symbols
            title = match.group(2).strip()

            if level <= min_heading_level:
                # This is a new major section boundary
                finalize_chunk()

                section_id = extract_section_id(title)
                parent_section = parent_sections.get(level - 1) if level > 1 else None

                # Update parent tracking
                parent_sections[level] = section_id
                # Clear deeper levels
                for deeper_level in list(parent_sections.keys()):
                    if deeper_level > level:
                        del parent_sections[deeper_level]

                current_chunk = {
                    "section_id": section_id,
                    "section_title": title,
                    "heading_level": level,
                    "start_line": line_num,
                    "parent_section": parent_section,
                }
                current_start_line = line_num
                current_lines = [line]
            else:
                # Subsection - include in current chunk
                current_lines.append(line)
        else:
            # Regular content line
            if current_chunk is not None:
                current_lines.append(line)
            elif line.strip():
                # Content before first heading - create "intro" section
                if not current_lines:
                    current_chunk = {
                        "section_id": "INTRO",
                        "section_title": "Introduction",
                        "heading_level": 1,
                        "start_line": line_num,
                        "parent_section": None,
                    }
                    current_start_line = line_num
                current_lines.append(line)

    # Finalize last chunk
    if current_chunk is not None:
        current_chunk["end_line"] = len(lines)
    finalize_chunk()

    return chunks


# =============================================================================
# SUMMARIZATION
# =============================================================================

def summarize_chunk(chunk: DocChunk, llm_interface: Any = None) -> str:
    """
    Create a summary of a chunk.

    If llm_interface is provided, uses LLM for summarization.
    Otherwise, uses simple extraction (first N chars).
    """
    if llm_interface is not None:
        # TODO: Implement LLM-based summarization
        # prompt = f"Summarize the following text in 1-2 sentences:\n\n{chunk.content}"
        # return llm_interface(prompt)
        pass

    # Simple extraction: first N chars, break at sentence
    text = chunk.content[:MAX_SUMMARY_LENGTH]
    for sep in [". ", ".\n"]:
        last_sep = text.rfind(sep)
        if last_sep > 0:
            text = text[:last_sep + 1]
            break
    return text.strip()


def summarize_document(chunks: List[DocChunk], llm_interface: Any = None) -> str:
    """Create an overall document summary from chunks."""
    if not chunks:
        return ""

    # Combine first chunk summaries
    summaries = [summarize_chunk(c, llm_interface) for c in chunks[:3]]
    combined = " ".join(summaries)

    if len(combined) > MAX_SUMMARY_LENGTH * 2:
        combined = combined[:MAX_SUMMARY_LENGTH * 2]
        # Break at sentence
        for sep in [". ", ".\n"]:
            last_sep = combined.rfind(sep)
            if last_sep > 0:
                combined = combined[:last_sep + 1]
                break

    return combined.strip()


def summarize_section(chunk: HeadingChunk) -> str:
    """
    Create a key-point summary for a HeadingChunk.

    Extractive (no LLM). Provenance rule: this value goes into content_summary
    only — the original chunk.content stays untouched.

    Algorithm:
    1. Strip the heading line from the content
    2. If section < 200 chars, use full content
    3. Extract first 2 sentences
    4. Prefix with section title
    5. Cap at 200 chars at a sentence boundary
    """
    # Strip leading heading line (the ## line itself)
    body = chunk.content
    first_newline = body.find("\n")
    if first_newline > 0 and body[:first_newline].strip().startswith("#"):
        body = body[first_newline + 1:].strip()

    if not body:
        return chunk.section_title

    # Short section — use full content
    if len(body) < 200:
        return f"{chunk.section_title}: {body}"

    # Extract first 2 sentences
    sentence_ends = []
    for sep in (". ", ".\n", "? ", "! "):
        idx = 0
        while True:
            pos = body.find(sep, idx)
            if pos < 0:
                break
            sentence_ends.append(pos + 1)
            idx = pos + 1

    sentence_ends.sort()
    if len(sentence_ends) >= 2:
        excerpt = body[:sentence_ends[1]].strip()
    elif sentence_ends:
        excerpt = body[:sentence_ends[0]].strip()
    else:
        excerpt = body[:200].strip()

    summary = f"{chunk.section_title}: {excerpt}"

    # Cap at 200 chars, break at sentence boundary
    if len(summary) > 200:
        truncated = summary[:200]
        for sep in (". ", ".\n"):
            last = truncated.rfind(sep)
            if last > 0:
                truncated = truncated[:last + 1]
                break
        summary = truncated.strip()

    return summary


# =============================================================================
# MEMORY ANCHOR CREATION
# =============================================================================

def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content for deduplication."""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def create_reference_doc_anchor(
    chunk: Union[DocChunk, HeadingChunk],
    source_ref: str,
    doc_summary: str,
    content_hash: str,
    *,
    doc_id: Optional[str] = None,
    section_summary: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a reference_doc memory anchor.

    Args:
        chunk: DocChunk or HeadingChunk
        source_ref: Full path or URI to source document
        doc_summary: Overall document summary
        content_hash: Content hash for deduplication
        doc_id: Optional document ID for DOC: semantic tag
        section_summary: Optional extractive summary for HeadingChunk (from summarize_section)

    Returns:
        Anchor dict ready for memory store, with DOC:/SECTION: tags if doc_id provided.
    """
    # Build semantic tags
    semantic_tags = ["document", "reference"]
    if doc_id:
        semantic_tags.append(f"DOC:{doc_id}")

    # Handle HeadingChunk-specific fields
    if isinstance(chunk, HeadingChunk):
        if doc_id:
            semantic_tags.append(f"SECTION:{chunk.section_id}")

        # For HeadingChunk, use extractive summary if provided, else fallback
        content_summary = section_summary or f"{chunk.section_title}: {chunk.content[:150]}..."

        # PR4: Compute heading_path and block_type for evidence policy
        heading_path = construct_heading_path(
            chunk.section_title,
            chunk.section_id,
            chunk.parent_section,
        )
        block_type = infer_block_type(chunk.content)

        return {
            "anchor_type": "reference_doc",
            "content": chunk.content[:4000],  # Increased for B8 Type C (section 5 is large)
            "content_summary": content_summary,
            "source_ref": {
                "doc_id": doc_id,
                "filename": os.path.basename(source_ref) if source_ref else None,
                "path": source_ref,
                "chunk_id": chunk.chunk_id,
                "section_id": chunk.section_id,
                "section_title": chunk.section_title,
                "heading_path": heading_path,  # PR4: full heading path
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "content_hash": content_hash,
            },
            "content_hash": content_hash,
            "chunk_id": chunk.chunk_id,
            "section_id": chunk.section_id,
            "section_title": chunk.section_title,
            "heading_path": heading_path,  # PR4: full heading path
            "block_type": block_type,  # PR4: structural type for evidence filtering
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "doc_summary": doc_summary[:200],
            "created_tick": 0,
            "strength": 0.7,
            "access_count": 0,
            "semantic_tags": semantic_tags,
        }
    else:
        # Original DocChunk handling (PDF/TXT)
        # PR4: Infer block_type for evidence policy
        block_type = infer_block_type(chunk.content)
        # For non-markdown, heading_path is just the chunk ID with page info
        heading_path = f"Page {chunk.page_num}" if chunk.page_num else f"Chunk {chunk.chunk_id}"

        return {
            "anchor_type": "reference_doc",
            "content": chunk.content[:4000],  # Increased for B8 Type C (section 5 is large)
            "content_summary": summarize_chunk(chunk),
            "source_ref": source_ref,
            "content_hash": content_hash,
            "chunk_id": chunk.chunk_id,
            "heading_path": heading_path,  # PR4: provenance path
            "block_type": block_type,  # PR4: structural type
            "start_char": chunk.start_char,
            "end_char": chunk.end_char,
            "page_num": chunk.page_num,
            "doc_summary": doc_summary[:200],
            "created_tick": 0,
            "strength": 0.7,
            "access_count": 0,
            "semantic_tags": semantic_tags,
        }


# =============================================================================
# MAIN INGESTION FUNCTION
# =============================================================================

def ingest_document(
    file_path: str,
    controller: Any = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    write_to_memory: bool = True,
    tenant_id: str = "default",
    storage_policy: str = "owner_full_copy",
) -> DocIngestResult:
    """
    Ingest a document into LTM as reference_doc anchors.

    Args:
        file_path: Path to document file
        controller: ToMController instance (optional, for memory writes)
        chunk_size: Characters per chunk
        chunk_overlap: Overlap between chunks
        write_to_memory: Whether to actually write to memory store
        tenant_id: Tenant ID for persistent store

    Returns:
        DocIngestResult with ingestion details
    """
    start_time = time.time()

    # Validate file exists
    if not os.path.exists(file_path):
        return DocIngestResult(
            success=False,
            source_path=file_path,
            source_ref=file_path,
            content_hash="",
            total_chars=0,
            chunks_created=0,
            anchors_written=0,
            error=f"File not found: {file_path}",
        )

    # Check extension
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return DocIngestResult(
            success=False,
            source_path=file_path,
            source_ref=file_path,
            content_hash="",
            total_chars=0,
            chunks_created=0,
            anchors_written=0,
            error=f"Unsupported file type: {ext}. Supported: {SUPPORTED_EXTENSIONS}",
        )

    # Extract text
    text, extract_error = extract_text(file_path)
    if extract_error:
        return DocIngestResult(
            success=False,
            source_path=file_path,
            source_ref=file_path,
            content_hash="",
            total_chars=0,
            chunks_created=0,
            anchors_written=0,
            error=extract_error,
        )

    if not text.strip():
        return DocIngestResult(
            success=False,
            source_path=file_path,
            source_ref=file_path,
            content_hash="",
            total_chars=0,
            chunks_created=0,
            anchors_written=0,
            error="Document is empty or unreadable",
        )

    # Compute content hash for deduplication
    content_hash = compute_content_hash(text)

    # Chunk the text
    chunks = chunk_text(text, chunk_size, chunk_overlap)

    # Create document summary
    doc_summary = summarize_document(chunks)

    # Create source reference
    source_ref = os.path.abspath(file_path)

    # Create anchors
    anchor_ids = []
    anchors_written = 0

    for chunk in chunks:
        anchor = create_reference_doc_anchor(
            chunk=chunk,
            source_ref=source_ref,
            doc_summary=doc_summary,
            content_hash=f"{content_hash}_{chunk.chunk_id}",
        )

        anchor_id = f"doc_{content_hash}_{chunk.chunk_id}"
        anchor["anchor_id"] = anchor_id
        anchor_ids.append(anchor_id)

        # Write to memory (controller state + persistent store)
        if write_to_memory:
            written = _write_anchor_to_memory(
                anchor=anchor,
                anchor_id=anchor_id,
                controller=controller,
                tenant_id=tenant_id,
                storage_policy=storage_policy,
            )
            if written:
                anchors_written += 1

    elapsed_ms = round((time.time() - start_time) * 1000, 2)

    return DocIngestResult(
        success=True,
        source_path=file_path,
        source_ref=source_ref,
        content_hash=content_hash,
        total_chars=len(text),
        chunks_created=len(chunks),
        anchors_written=anchors_written,
        anchor_ids=anchor_ids,
        telemetry={
            "elapsed_ms": elapsed_ms,
            "chars_per_chunk": chunk_size,
            "overlap": chunk_overlap,
            "doc_summary_len": len(doc_summary),
        },
    )


# =============================================================================
# MARKDOWN-SPECIFIC INGESTION (B8)
# =============================================================================

# Bounds for document ingestion (configurable via TOM_DOC_MAX_SIZE_BYTES / TOM_DOC_MAX_ANCHORS)
# Defaults used only when config system is unavailable
MAX_DOC_SIZE_BYTES = 10 * 1024 * 1024  # 10MB default (was 100KB)
MAX_ANCHORS_PER_DOC = 50


def ingest_markdown_document(
    file_path: str,
    *,
    doc_id: Optional[str] = None,
    controller: Any = None,
    write_to_memory: bool = True,
    tenant_id: str = "default",
    storage_policy: str = "owner_full_copy",
) -> MDIngestResult:
    """Backward-compatible wrapper — delegates to ingest_structured_document(mode='sections')."""
    return ingest_structured_document(
        file_path,
        doc_id=doc_id,
        controller=controller,
        write_to_memory=write_to_memory,
        tenant_id=tenant_id,
        mode="sections",
        storage_policy=storage_policy,
    )


def ingest_structured_document(
    file_path: str,
    *,
    doc_id: Optional[str] = None,
    controller: Any = None,
    write_to_memory: bool = True,
    tenant_id: str = "default",
    mode: str = "auto",
    storage_policy: str = "owner_full_copy",
) -> MDIngestResult:
    """
    Ingest a document with heading-aware semantic chunking.

    Works for ALL supported formats (PDF, DOCX, PPTX, XLSX, TXT, MD, etc.).
    DOCX/PPTX/XLSX readers already emit markdown heading syntax.
    PDF/TXT get heading detection via detect_headings_in_plain_text().

    Args:
        file_path: Path to document file
        doc_id: Unique document ID (defaults to filename-based hash)
        controller: ToMController for memory writes
        write_to_memory: Whether to persist to memory store
        tenant_id: Tenant ID for persistent store
        mode: Ingestion mode:
            "auto" — try heading detection; if confident (>= 3 headings), use
                     sections; else fall back to full chunking
            "sections" — force heading-aware chunking
            "full" — delegate to ingest_document() (fixed-size chunks, entire doc)

    Returns:
        MDIngestResult with ingestion details and heading chunks

    Hard Guarantees:
        - Max file size from config system
        - Max 50 anchors per document
        - Content hash deduplication
        - DOC: tag filtering support
    """
    # Validate mode
    if mode not in ("auto", "sections", "full"):
        mode = "auto"

    start_time = time.time()

    # Validate file exists
    if not os.path.exists(file_path):
        return MDIngestResult(
            success=False,
            source_path=file_path,
            source_ref=file_path,
            content_hash="",
            total_chars=0,
            chunks_created=0,
            anchors_written=0,
            error=f"File not found: {file_path}",
        )

    # Check file size (use config system limit)
    effective_max = _get_max_file_size()
    file_size = os.path.getsize(file_path)
    if file_size > effective_max:
        return MDIngestResult(
            success=False,
            source_path=file_path,
            source_ref=file_path,
            content_hash="",
            total_chars=0,
            chunks_created=0,
            anchors_written=0,
            error=f"File exceeds {effective_max // 1024}KB limit ({file_size // 1024}KB)",
        )

    ext = os.path.splitext(file_path)[1].lower()

    # mode="full" delegates entirely to existing ingest_document()
    if mode == "full":
        result = ingest_document(
            file_path,
            controller=controller,
            write_to_memory=write_to_memory,
            tenant_id=tenant_id,
        )
        # Wrap DocIngestResult as MDIngestResult for uniform return type
        return MDIngestResult(
            success=result.success,
            source_path=result.source_path,
            source_ref=result.source_ref,
            content_hash=result.content_hash,
            total_chars=result.total_chars,
            chunks_created=result.chunks_created,
            anchors_written=result.anchors_written,
            anchor_ids=result.anchor_ids,
            error=result.error,
            telemetry={
                **result.telemetry,
                "mode_requested": "full",
                "mode_effective": "full",
            },
        )

    # Extract text using format-agnostic reader
    text, extract_error = extract_text(file_path)
    if extract_error:
        return MDIngestResult(
            success=False,
            source_path=file_path,
            source_ref=file_path,
            content_hash="",
            total_chars=0,
            chunks_created=0,
            anchors_written=0,
            error=extract_error,
        )

    if not text.strip():
        return MDIngestResult(
            success=False,
            source_path=file_path,
            source_ref=file_path,
            content_hash="",
            total_chars=0,
            chunks_created=0,
            anchors_written=0,
            error="Document is empty or unreadable",
        )

    # Heading enrichment for plain-text formats (PDF, TXT, etc.)
    # DOCX/PPTX/XLSX already have markdown headings from their readers
    detect_meta = {"headings_detected": 0, "detection_method": "native_markdown", "lines_stripped": 0}
    if ext in {".pdf", ".txt", ".log", ".rst"}:
        text, detect_meta = detect_headings_in_plain_text(text, source_hint=ext.lstrip("."))
    elif ext == ".md":
        detect_meta = {"headings_detected": -1, "detection_method": "native_markdown", "lines_stripped": 0}

    # Compute content hash for deduplication
    content_hash = compute_content_hash(text)

    # Generate doc_id if not provided
    if doc_id is None:
        filename = os.path.basename(file_path)
        name_without_ext = os.path.splitext(filename)[0]
        doc_id = re.sub(r'[^a-zA-Z0-9]+', '_', name_without_ext).lower()
        doc_id = f"{doc_id}_{content_hash[:8]}"

    # Chunk by headings
    heading_chunks = chunk_markdown_by_headings(text)

    # mode="auto" fallback: if heading detection found < min_confidence_headings
    # and this is not a native markdown file, fall back to full chunking.
    # Note: chunk_markdown_by_headings may return a default chunk even without
    # real headings, so we check detect_meta, not heading_chunks.
    detected_count = detect_meta.get("headings_detected", 0)
    if mode == "auto" and ext != ".md" and detected_count < 3:
            result = ingest_document(
                file_path,
                controller=controller,
                write_to_memory=write_to_memory,
                tenant_id=tenant_id,
                storage_policy=storage_policy,
            )
            return MDIngestResult(
                success=result.success,
                source_path=result.source_path,
                source_ref=result.source_ref,
                content_hash=result.content_hash,
                total_chars=result.total_chars,
                chunks_created=result.chunks_created,
                anchors_written=result.anchors_written,
                anchor_ids=result.anchor_ids,
                error=result.error,
                telemetry={
                    **result.telemetry,
                    "mode_requested": "auto",
                    "mode_effective": "full",
                    "heading_detected_count": detected_count,
                    "heading_detection_method": detect_meta.get("detection_method", "none"),
                },
            )

    # If no headings found, fall back to fixed-size chunking as pseudo-HeadingChunks
    fallback_count = 0
    if not heading_chunks:
        print(f"[doc_ingest] No headings found in {file_path}, falling back to fixed-size chunking", file=sys.stderr)
        fixed_chunks = chunk_text(text)
        heading_chunks = [
            HeadingChunk(
                chunk_id=f"section_{i}",
                section_id=f"PART_{i+1}",
                section_title=f"Part {i+1}",
                heading_level=2,
                content=c.content,
                start_line=0,
                end_line=0,
            )
            for i, c in enumerate(fixed_chunks)
        ]
        fallback_count = len(heading_chunks)

    # Limit to configurable max anchors
    max_anchors = _get_max_anchors()
    if len(heading_chunks) > max_anchors:
        print(f"[doc_ingest] Limiting to {max_anchors} anchors (found {len(heading_chunks)})", file=sys.stderr)
        heading_chunks = heading_chunks[:max_anchors]

    # Create source reference
    source_ref = os.path.abspath(file_path)

    # Create document summary from first few chunks
    doc_summary = " ".join(
        chunk.section_title for chunk in heading_chunks[:5]
    )[:200]

    # Create anchors with section summaries
    anchor_ids = []
    anchors_written = 0

    for chunk in heading_chunks:
        # Generate extractive section summary
        sec_summary = summarize_section(chunk)

        anchor = create_reference_doc_anchor(
            chunk=chunk,
            source_ref=source_ref,
            doc_summary=doc_summary,
            content_hash=f"{content_hash}_{chunk.chunk_id}",
            doc_id=doc_id,
            section_summary=sec_summary,
        )

        anchor_id = f"doc_{doc_id}_{chunk.chunk_id}"
        anchor["anchor_id"] = anchor_id
        anchor["id"] = anchor_id
        anchor_ids.append(anchor_id)

        # Write to memory
        if write_to_memory:
            written = _write_anchor_to_memory(
                anchor=anchor,
                anchor_id=anchor_id,
                controller=controller,
                tenant_id=tenant_id,
                storage_policy=storage_policy,
            )
            if written:
                anchors_written += 1

    # Populate SEI for this document
    from gateway.vendor.rgm17d.memory.persistent_store import register_sei
    sei_facts = _extract_sei_facts(heading_chunks, text)
    sei_headings = _extract_sei_headings(text)
    register_sei(tenant_id, doc_id, content_hash, sei_facts, sei_headings)

    # Populate DSI (Document Skills Index) for subsection navigation
    from gateway.vendor.rgm17d.memory.persistent_store import register_dsi
    dsi_skills = _extract_dsi_skills(heading_chunks, doc_id=doc_id)
    register_dsi(tenant_id, doc_id, content_hash, dsi_skills)

    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    effective_mode = "full" if fallback_count == len(heading_chunks) and fallback_count > 0 else "sections"

    return MDIngestResult(
        success=True,
        source_path=file_path,
        source_ref=source_ref,
        content_hash=content_hash,
        total_chars=len(text),
        chunks_created=len(heading_chunks),
        anchors_written=anchors_written,
        anchor_ids=anchor_ids,
        doc_id=doc_id,
        sections_found=len(heading_chunks),
        heading_chunks=heading_chunks,
        telemetry={
            "elapsed_ms": elapsed_ms,
            "doc_id": doc_id,
            "sections_found": len(heading_chunks),
            "anchors_written": anchors_written,
            "content_hash": content_hash,
            "heading_detected_count": detect_meta.get("headings_detected", 0),
            "heading_detection_method": detect_meta.get("detection_method", "native_markdown"),
            "sections_created": len(heading_chunks),
            "fallback_chunk_pct": round(fallback_count / max(len(heading_chunks), 1) * 100, 1),
            "mode_requested": mode,
            "mode_effective": effective_mode,
            "lines_stripped": detect_meta.get("lines_stripped", 0),
        },
    )


def _normalize_metadata(anchor: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize anchor source_ref into a dict suitable for persistent store metadata."""
    source_ref = anchor.get("source_ref", {})
    if isinstance(source_ref, dict):
        return source_ref
    # Non-markdown files store source_ref as a plain file path string
    return {
        "path": str(source_ref) if source_ref else "",
        "filename": os.path.basename(str(source_ref)) if source_ref else "",
        "doc_id": anchor.get("semantic_tags", [""])[0].replace("DOC:", "") if any(
            str(t).startswith("DOC:") for t in anchor.get("semantic_tags", [])
        ) else "",
        "section_title": anchor.get("heading_path", ""),
        "content_hash": anchor.get("content_hash", ""),
        "chunk_id": anchor.get("chunk_id"),
        "page_num": anchor.get("page_num"),
    }


def _write_anchor_to_memory(
    anchor: Dict[str, Any],
    anchor_id: str,
    controller: Any = None,
    tenant_id: str = "default",
    storage_policy: str = "owner_full_copy",
) -> bool:
    """
    Write an anchor to both controller state and persistent store.

    M5/DEF-04: When storage_policy is "zero_copy_strict", raw content is NOT
    persisted. Instead, content_summary and raw_content_ref are stored, and
    source_content_hash is used for dedup.

    Returns True if successfully written.
    """
    written = False

    # M5/DEF-04: Compute zero-copy fields before writing
    original_content = anchor.get("content", "")
    source_content_hash = None
    content_summary = anchor.get("content_summary", "")
    raw_content_ref = None
    source_version = None

    if storage_policy == "zero_copy_strict":
        # Compute source hash from original content (before stripping)
        import hashlib
        source_content_hash = hashlib.sha256(
            original_content.encode()
        ).hexdigest()[:12] if original_content else None
        # Build raw_content_ref from file source
        source_ref = anchor.get("source_ref", "")
        if isinstance(source_ref, dict):
            ref_path = source_ref.get("path", "")
            chunk_id = source_ref.get("chunk_id", "")
            raw_content_ref = f"file://{ref_path}#{chunk_id}" if ref_path else None
        elif source_ref:
            chunk_id = anchor.get("chunk_id", "")
            start_char = anchor.get("start_char", 0)
            end_char = anchor.get("end_char", 0)
            if start_char and end_char:
                raw_content_ref = f"file://{source_ref}#{start_char}:{end_char - start_char}"
            else:
                raw_content_ref = f"file://{source_ref}#{chunk_id}" if chunk_id else f"file://{source_ref}"
        # Generate summary if not already present
        if not content_summary and original_content:
            content_summary = original_content[:150].strip() + "..." if len(original_content) > 150 else original_content.strip()

    # Write to controller state if provided
    if controller is not None:
        try:
            state = getattr(controller, "state", None)
            if state is not None:
                memory = getattr(state, "memory", None)
                if memory is None:
                    # Try to create memory state
                    try:
                        from types import SimpleNamespace
                        state.memory = SimpleNamespace(anchors={})
                        memory = state.memory
                    except Exception:
                        pass

                if memory is not None:
                    anchors = getattr(memory, "anchors", None)
                    if anchors is None:
                        memory.anchors = {}
                        anchors = memory.anchors

                    # Check for duplicate by content_hash
                    content_hash = anchor.get("content_hash", "")
                    is_duplicate = False
                    if isinstance(anchors, dict):
                        for existing in anchors.values():
                            if isinstance(existing, dict) and existing.get("content_hash") == content_hash:
                                is_duplicate = True
                                break
                    elif isinstance(anchors, list):
                        for existing in anchors:
                            if isinstance(existing, dict) and existing.get("content_hash") == content_hash:
                                is_duplicate = True
                                break

                    if not is_duplicate:
                        # M5/DEF-04: Enrich anchor with zero-copy fields for controller state
                        enriched_anchor = dict(anchor)
                        if storage_policy == "zero_copy_strict":
                            enriched_anchor["content"] = ""
                            enriched_anchor["storage_policy"] = "zero_copy_strict"
                            enriched_anchor["source_content_hash"] = source_content_hash
                            enriched_anchor["raw_content_ref"] = raw_content_ref
                            if content_summary:
                                enriched_anchor["content_summary"] = content_summary
                            # M9: If summary-in-content is enabled, place summary
                            # in content field for RGM embedding path only.
                            # Persisted content remains "" (see persist_memory below).
                            from gateway.vendor.rgm17d.config.compat import get_bool as _gb
                            if _gb("tunable.memory.allow_summary_in_content_for_embedding",
                                   "TOM_MEMORY_SUMMARY_IN_CONTENT", default=False) and content_summary:
                                enriched_anchor["content"] = content_summary
                        else:
                            enriched_anchor["storage_policy"] = "owner_full_copy"

                        if isinstance(anchors, dict):
                            anchors[anchor_id] = enriched_anchor
                        else:
                            anchors.append(enriched_anchor)
                        written = True
        except Exception as e:
            print(f"[doc_ingest] Controller write failed for {anchor_id}: {e}", file=sys.stderr)

    # Also persist to persistent store
    try:
        from gateway.vendor.rgm17d.memory.persistent_store import persist_memory, register_active_doc

        # M5/DEF-04: Zero-copy records have content stripped before persistence
        persist_content = "" if storage_policy == "zero_copy_strict" else anchor.get("content", "")

        persisted = persist_memory(
            memory_id=anchor_id,
            content=persist_content,
            anchor_type="reference_doc",
            tenant_id=tenant_id,
            axis_hint=None,  # Raw documents have no cognitive axis until processed by ToM
            session_id=None,
            semantic_tags=anchor.get("semantic_tags", []),
            strength=anchor.get("strength", 0.7),
            metadata=_normalize_metadata(anchor),
            source_content_hash=source_content_hash,
            storage_policy=storage_policy,
            content_summary=content_summary,
            raw_content_ref=raw_content_ref,
            source_version=source_version,
        )
        if persisted:
            written = True
            # Register doc_id as active for deterministic retrieval scoping
            semantic_tags = anchor.get("semantic_tags", [])
            for tag in semantic_tags:
                if str(tag).startswith("DOC:"):
                    doc_id = str(tag)[4:]  # Extract doc_id from "DOC:doc_id"
                    register_active_doc(tenant_id, doc_id)
                    break
    except Exception as e:
        print(f"[doc_ingest] Persistent store write failed for {anchor_id}: {e}", file=sys.stderr)

    return written


# =============================================================================
# UNIFIED INGESTION ENTRY POINT
# =============================================================================

@dataclass
class IngestResult:
    """Standardized result for the unified ingestion API."""
    success: bool
    doc_id: str
    anchors_written: int
    chunks_created: int
    reason_code: str  # "ok", "unsupported_extension", "file_too_large", "parse_error", "file_not_found", "empty_document"
    error_detail: Optional[str] = None


def _get_max_file_size() -> int:
    """Get max file size from config system, falling back to default."""
    try:
        from gateway.vendor.rgm17d.config.compat import get_config_value
        val = get_config_value(
            "doc_ingest.max_file_size_bytes",
            "TOM_DOC_MAX_SIZE_BYTES",
            default=10 * 1024 * 1024,
        )
        return int(val)
    except Exception:
        return 10 * 1024 * 1024  # 10MB default


def _get_max_anchors() -> int:
    """Get max anchors per doc from config system, falling back to default."""
    try:
        from gateway.vendor.rgm17d.config.compat import get_config_value
        val = get_config_value(
            "doc_ingest.max_anchors_per_doc",
            "TOM_DOC_MAX_ANCHORS",
            default=50,
        )
        return int(val)
    except Exception:
        return 50


def ingest_any_document(
    file_path: str,
    *,
    controller: Any = None,
    tenant_id: str = "default",
    write_to_memory: bool = True,
    max_file_size: Optional[int] = None,
    storage_policy: Optional[str] = None,
    mode: str = "auto",
) -> IngestResult:
    """
    Unified document ingestion entry point.

    Routes all supported types through ingest_structured_document() for
    heading-aware semantic chunking. Uses mode to control behavior:
      "auto"     — try heading detection; fall back to full if < 3 headings
      "sections" — force heading-aware chunking
      "full"     — delegate to ingest_document() (fixed-size chunks, entire doc)

    Args:
        file_path: Path to the document file
        controller: ToMController instance (optional)
        tenant_id: Tenant ID for persistent store
        write_to_memory: Whether to persist to memory store
        max_file_size: Override max file size (bytes). Defaults to config value.
        mode: Ingestion mode ("auto", "sections", "full")

    Returns:
        IngestResult with standardized fields and reason_code
    """
    # Resolve storage_policy from config if not explicitly provided
    if storage_policy is None:
        from gateway.vendor.rgm17d.config.compat import get_str
        storage_policy = get_str(
            "tunable.memory.default_storage_policy",
            "TOM_MEMORY_STORAGE_POLICY",
            default="zero_copy_strict",
        )

    # Validate mode
    if mode not in ("auto", "sections", "full"):
        mode = "auto"

    # Validate file exists
    if not os.path.exists(file_path):
        return IngestResult(
            success=False,
            doc_id="",
            anchors_written=0,
            chunks_created=0,
            reason_code="file_not_found",
            error_detail=f"File not found: {file_path}",
        )

    # Check extension
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return IngestResult(
            success=False,
            doc_id="",
            anchors_written=0,
            chunks_created=0,
            reason_code="unsupported_extension",
            error_detail=f"Unsupported file type: {ext}. Supported: {sorted(SUPPORTED_EXTENSIONS)}",
        )

    # Check file size
    effective_max = max_file_size if max_file_size is not None else _get_max_file_size()
    file_size = os.path.getsize(file_path)
    if file_size > effective_max:
        return IngestResult(
            success=False,
            doc_id="",
            anchors_written=0,
            chunks_created=0,
            reason_code="file_too_large",
            error_detail=f"File size {file_size} bytes exceeds limit of {effective_max} bytes",
        )

    # Route through structured ingestion for all formats
    try:
        if mode == "full":
            result = ingest_document(
                file_path,
                controller=controller,
                write_to_memory=write_to_memory,
                tenant_id=tenant_id,
                storage_policy=storage_policy,
            )
            doc_id = result.content_hash or ""
            return IngestResult(
                success=result.success,
                doc_id=doc_id,
                anchors_written=result.anchors_written,
                chunks_created=result.chunks_created,
                reason_code="ok" if result.success else "parse_error",
                error_detail=result.error,
            )
        else:
            result = ingest_structured_document(
                file_path,
                controller=controller,
                write_to_memory=write_to_memory,
                tenant_id=tenant_id,
                mode=mode,
                storage_policy=storage_policy,
            )
            return IngestResult(
                success=result.success,
                doc_id=getattr(result, "doc_id", "") or "",
                anchors_written=result.anchors_written,
                chunks_created=result.chunks_created,
                reason_code="ok" if result.success else "parse_error",
                error_detail=result.error,
            )
    except Exception as e:
        return IngestResult(
            success=False,
            doc_id="",
            anchors_written=0,
            chunks_created=0,
            reason_code="parse_error",
            error_detail=str(e),
        )


# =============================================================================
# CAPABILITY REPORTING
# =============================================================================

@dataclass
class CapabilityStatus:
    """Reports whether a file extension is supported and its provider health."""
    extension: str
    supported: bool
    mode: str  # "native", "library", "unsupported"
    reason_code: str  # "ok", "missing_library", "not_implemented"
    required_provider: Optional[str] = None
    org_id: Optional[str] = None
    source_id: Optional[str] = None
    provider_healthy: bool = False


# Map extensions to their required libraries and import test
_N = {"provider": None, "mode": "native", "import_check": None}  # Native (no library)

_EXTENSION_PROVIDERS = {
    # Documents - native
    ".txt": _N, ".md": _N,
    # Documents - library-dependent
    ".pdf":  {"provider": "pypdf", "mode": "library", "import_check": "pypdf"},
    ".docx": {"provider": "python-docx", "mode": "library", "import_check": "docx"},
    ".doc":  {"provider": "textract", "mode": "library", "import_check": "textract"},
    ".xlsx": {"provider": "openpyxl", "mode": "library", "import_check": "openpyxl"},
    ".xlsm": {"provider": "openpyxl", "mode": "library", "import_check": "openpyxl"},
    ".xls":  {"provider": "xlrd", "mode": "library", "import_check": "xlrd"},
    ".pptx": {"provider": "python-pptx", "mode": "library", "import_check": "pptx"},
    ".ppt":  {"provider": "textract", "mode": "library", "import_check": "textract"},
    # Email
    ".eml": _N,  # stdlib email module
    ".msg": {"provider": "extract-msg", "mode": "library", "import_check": "extract_msg"},
    # Markup / data - native
    ".csv": _N, ".tsv": _N, ".json": _N, ".jsonl": _N, ".ndjson": _N,
    ".html": _N, ".htm": _N, ".mht": _N,
    ".xml": _N, ".svg": _N,
    ".yaml": _N, ".yml": _N, ".rst": _N, ".rtf": _N, ".log": _N,
    # Config - native
    ".ini": _N, ".cfg": _N, ".conf": _N, ".toml": _N, ".env": _N, ".properties": _N,
    # CAD - native
    ".dxf": _N,
    # Documentation - native
    ".tex": _N, ".bib": _N, ".adoc": _N,
    # DevOps - native
    ".tf": _N, ".hcl": _N, ".proto": _N, ".gradle": _N, ".dockerfile": _N,
    # Source code - systems
    ".py": _N, ".rb": _N, ".go": _N, ".java": _N,
    ".c": _N, ".cpp": _N, ".h": _N, ".hpp": _N,
    ".cs": _N, ".fs": _N, ".rs": _N, ".swift": _N, ".kt": _N, ".scala": _N, ".m": _N,
    ".zig": _N, ".nim": _N, ".dart": _N, ".lua": _N, ".pl": _N, ".php": _N,
    ".groovy": _N, ".r": _N, ".ex": _N, ".exs": _N, ".erl": _N, ".hs": _N, ".clj": _N,
    # Source code - web/frontend
    ".js": _N, ".ts": _N, ".jsx": _N, ".tsx": _N, ".vue": _N, ".svelte": _N,
    ".css": _N, ".scss": _N, ".sass": _N, ".less": _N,
    ".graphql": _N, ".gql": _N,
    # Source code - shell/scripting
    ".sh": _N, ".bat": _N, ".ps1": _N, ".vb": _N, ".vbs": _N,
    # Source code - data/query
    ".sql": _N,
}

del _N  # cleanup temp alias


def _check_library_available(import_name: str) -> bool:
    """Check if a Python library is importable."""
    try:
        __import__(import_name)
        return True
    except ImportError:
        return False


def get_supported_capabilities(
    org_id: Optional[str] = None,
    source_id: Optional[str] = None,
) -> List[CapabilityStatus]:
    """
    Report which file extensions are supported and their provider health.

    Args:
        org_id: If provided, scope results to this org
        source_id: If provided, scope results to this source

    Returns:
        List of CapabilityStatus, one per known extension
    """
    capabilities = []

    for ext, info in _EXTENSION_PROVIDERS.items():
        import_check = info["import_check"]
        provider = info["provider"]
        mode = info["mode"]

        if import_check is None:
            # Native support, no library needed
            capabilities.append(CapabilityStatus(
                extension=ext,
                supported=True,
                mode=mode,
                reason_code="ok",
                required_provider=provider,
                org_id=org_id,
                source_id=source_id,
                provider_healthy=True,
            ))
        else:
            healthy = _check_library_available(import_check)
            capabilities.append(CapabilityStatus(
                extension=ext,
                supported=healthy,
                mode=mode,
                reason_code="ok" if healthy else "missing_library",
                required_provider=provider,
                org_id=org_id,
                source_id=source_id,
                provider_healthy=healthy,
            ))

    return capabilities


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingest document into ToMchatbot LTM")
    parser.add_argument("file", help="Path to document file")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--overlap", type=int, default=DEFAULT_CHUNK_OVERLAP)
    parser.add_argument("--dry-run", action="store_true", help="Don't write to memory")

    args = parser.parse_args()

    result = ingest_document(
        args.file,
        controller=None,
        chunk_size=args.chunk_size,
        chunk_overlap=args.overlap,
        write_to_memory=not args.dry_run,
    )

    print(f"\nDocument Ingestion Result:")
    print(f"  Success: {result.success}")
    print(f"  Source: {result.source_path}")
    print(f"  Hash: {result.content_hash}")
    print(f"  Total chars: {result.total_chars}")
    print(f"  Chunks: {result.chunks_created}")
    print(f"  Anchors written: {result.anchors_written}")
    if result.error:
        print(f"  Error: {result.error}")
    if result.telemetry:
        print(f"  Telemetry: {result.telemetry}")
