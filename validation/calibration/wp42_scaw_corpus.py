#!/usr/bin/env python3
"""Prepare the owner-selected SCAW deed corpus outside the repository.

This is a validation-only utility. It has no gateway or product imports and
never invokes a model. Contract text is written only to an explicit external
output directory; the repository manifest contains provenance and hashes only.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
VERSION = "tom-assist-scaw-corpus-preparation/1.0"
MANIFEST_VERSION = "tom-assist-scaw-shortlist-manifest/1.0"
SHORTLIST_VERSION = "tom-assist-scaw-shortlist-text/1.0"
GLOSSARY_CANDIDATE_VERSION = "tom-assist-scaw-defined-terms/1.0"
SOURCE_FILE_NAME = "SCAW D_C Deed - Executed 1 March 2022.pdf"
SOURCE_SHA256 = "sha256:a9dda3b6376d27bd76a01adc4a7692838b4271a9967c53f69fa6883dafc14f99"
SOURCE_BYTES = 22_399_742
SOURCE_PDF_PAGES = 343
EXTRACTION_SHA256 = "sha256:7d0b79c1fb5403db044f1ea78da3a592707c2169f32fe5bb44ce138006951c12"
EXTRACTION_BYTES = 1_215_976
PDFTOTEXT_ARGUMENTS = ("-layout", "-enc", "UTF-8", "-eol", "unix")
FAMILIES = frozenset({"causation", "dependency", "rule_or_constraint", "supersession"})
DIFFICULTIES = frozenset({"easy", "medium", "hard"})
DEFINITION_START = (10, 41)
DEFINITION_END = (69, 33)
EXTRACTED_FILE_NAME = "SCAW_DEED_PDFTOTEXT_LAYOUT.txt"
SHORTLIST_FILE_NAME = "SCAW_SHORTLIST_TEXT.json"
GLOSSARY_FILE_NAME = "SCAW_DEFINED_TERMS_SURFACE_ONLY.json"
_DEFINITION_DELIMITER = re.compile(
    r"\s+(?:means|has the meaning(?: given)?(?: to that term)?(?: given)?"
    r"(?: in| under| set out| assigned)?|includes|is the process)\b",
    flags=re.IGNORECASE,
)


class CorpusPreparationError(RuntimeError):
    """A fail-closed corpus preparation error."""


def compact_json(value: Any) -> bytes:
    return (
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def pretty_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def source_identity(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise CorpusPreparationError(f"source PDF is unavailable: {path}")
    size = path.stat().st_size
    digest = sha256_bytes(path.read_bytes())
    if size != SOURCE_BYTES or digest != SOURCE_SHA256:
        raise CorpusPreparationError(
            "source PDF identity mismatch: "
            f"expected {SOURCE_BYTES} bytes/{SOURCE_SHA256}, got {size}/{digest}"
        )
    return {
        "file_name": SOURCE_FILE_NAME,
        "byte_count": size,
        "pdf_page_count": SOURCE_PDF_PAGES,
        "sha256": digest,
    }


def pdftotext_version(executable: str) -> str:
    try:
        result = subprocess.run(
            [executable, "-v"], check=True, capture_output=True, text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise CorpusPreparationError(f"pdftotext is unavailable: {error}") from None
    output = (result.stdout + result.stderr).strip().splitlines()
    if not output:
        raise CorpusPreparationError("pdftotext did not report a version")
    match = re.search(r"pdftotext version ([0-9.]+)", output[0])
    if not match:
        raise CorpusPreparationError(
            f"pdftotext version is not recognisable: {output[0]}"
        )
    return match.group(1)


def poppler_extract(source: Path, destination: Path, executable: str) -> bytes:
    command = [executable, *PDFTOTEXT_ARGUMENTS, str(source), str(destination)]
    try:
        subprocess.run(command, check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError) as error:
        raise CorpusPreparationError(f"pdftotext extraction failed: {error}") from None
    if not destination.is_file():
        raise CorpusPreparationError("pdftotext produced no extraction")
    return destination.read_bytes()


def extract_twice(
    source: Path,
    extractor: Callable[[Path, Path], bytes],
    *,
    expected_sha256: str | None = None,
    expected_bytes: int | None = None,
    expected_pages: int | None = None,
) -> str:
    """Run an extractor twice and return the byte-identical UTF-8 text."""
    with tempfile.TemporaryDirectory(prefix="tom-assist-wp42-extract-") as temporary:
        directory = Path(temporary)
        first = extractor(source, directory / "run-1.txt")
        second = extractor(source, directory / "run-2.txt")
    if first != second:
        raise CorpusPreparationError("pdftotext extraction is not byte-identical")
    if expected_bytes is not None and len(first) != expected_bytes:
        raise CorpusPreparationError(
            f"extraction byte count mismatch: expected {expected_bytes}, got {len(first)}"
        )
    digest = sha256_bytes(first)
    if expected_sha256 is not None and digest != expected_sha256:
        raise CorpusPreparationError(
            f"extraction hash mismatch: expected {expected_sha256}, got {digest}"
        )
    try:
        text = first.decode("utf-8")
    except UnicodeDecodeError as error:
        raise CorpusPreparationError(f"extraction is not UTF-8: {error}") from None
    pages = split_pdf_pages(text)
    if expected_pages is not None and len(pages) != expected_pages:
        raise CorpusPreparationError(
            f"extraction page count mismatch: expected {expected_pages}, got {len(pages)}"
        )
    return text


def split_pdf_pages(text: str) -> list[tuple[int, str]]:
    pieces = text.split("\f")
    if pieces and pieces[-1] == "":
        pieces.pop()
    pages = []
    offset = 0
    for piece in pieces:
        pages.append((offset, piece))
        offset += len(piece) + 1
    return pages


def _page_line_slice(
    pages: Sequence[tuple[int, str]], page: int, line_start: int, line_end: int,
) -> tuple[int, int, str]:
    if page < 1 or page > len(pages):
        raise CorpusPreparationError(f"selection page is outside extraction: {page}")
    page_offset, page_text = pages[page - 1]
    lines = page_text.splitlines(keepends=True)
    if line_start < 1 or line_end < line_start or line_end > len(lines):
        raise CorpusPreparationError(
            f"selection line range is invalid on page {page}: {line_start}-{line_end}"
        )
    local_start = sum(len(line) for line in lines[:line_start - 1])
    local_end = sum(len(line) for line in lines[:line_end])
    passage = page_text[local_start:local_end]
    if not passage.strip():
        raise CorpusPreparationError(f"selection is empty on page {page}")
    return page_offset + local_start, page_offset + local_end, passage


def extract_defined_terms(
    text: str,
    *,
    start: tuple[int, int] = DEFINITION_START,
    end: tuple[int, int] = DEFINITION_END,
) -> list[str]:
    """Extract only surface forms from bounded definition-entry blocks."""
    pages = split_pdf_pages(text)
    start_page, start_line = start
    end_page, end_line = end
    if start_page > end_page:
        raise CorpusPreparationError("definition page bounds are reversed")
    blocks = []
    for page_number in range(start_page, end_page + 1):
        _offset, page_text = pages[page_number - 1]
        lines = page_text.splitlines()
        low = start_line - 1 if page_number == start_page else 0
        high = end_line if page_number == end_page else len(lines)
        cleaned = [
            line for line in lines[low:high]
            if not re.fullmatch(r"\s*\d+\s*", line)
            and not line.strip().startswith("ME_")
        ]
        blocks.append("\n".join(cleaned))
    region = "\n\n".join(blocks)
    terms = []
    for block in re.split(r"\n\s*\n", region):
        collapsed = " ".join(block.split())
        match = _DEFINITION_DELIMITER.search(collapsed)
        if not match:
            continue
        term = collapsed[:match.start()].strip()
        if not (
            1 <= len(term) <= 100
            and term[0].isupper()
            and not re.match(r"^\([a-zivx]+\)", term, flags=re.IGNORECASE)
            and not any(character in term for character in ".;:")
        ):
            continue
        if _DEFINITION_DELIMITER.search(term) or "\n" in term:
            raise CorpusPreparationError("defined-term extraction included definition text")
        terms.append(term)
    folded = [term.casefold() for term in terms]
    if len(folded) != len(set(folded)):
        raise CorpusPreparationError("defined-term extraction contains duplicates")
    if not terms:
        raise CorpusPreparationError("defined-term extraction returned no surfaces")
    return terms


def load_selection_plan(path: Path) -> list[dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CorpusPreparationError(f"selection plan is unreadable: {error}") from None
    if not isinstance(value, list):
        raise CorpusPreparationError("selection plan must be an array")
    expected = {
        "passage_id", "pdf_page", "line_start", "line_end",
        "clause_identifier", "families", "difficulty",
    }
    seen = set()
    result = []
    for item in value:
        if not isinstance(item, Mapping) or set(item) != expected:
            raise CorpusPreparationError("selection-plan fields mismatch")
        passage_id = item["passage_id"]
        if not isinstance(passage_id, str) or not re.fullmatch(r"SCAW-[0-9]{3}", passage_id):
            raise CorpusPreparationError("selection passage ID is invalid")
        if passage_id in seen:
            raise CorpusPreparationError("selection passage IDs are not unique")
        seen.add(passage_id)
        families = item["families"]
        if (
            not isinstance(families, list)
            or len(families) != len(set(families))
            or not set(families) <= FAMILIES
        ):
            raise CorpusPreparationError(f"selection families are invalid: {passage_id}")
        if item["difficulty"] not in DIFFICULTIES:
            raise CorpusPreparationError(f"selection difficulty is invalid: {passage_id}")
        if not isinstance(item["clause_identifier"], str) or not item["clause_identifier"]:
            raise CorpusPreparationError(f"selection clause identifier is invalid: {passage_id}")
        if any(type(item[name]) is not int for name in ("pdf_page", "line_start", "line_end")):
            raise CorpusPreparationError(f"selection location is invalid: {passage_id}")
        result.append(dict(item))
    return result


def build_passages(text: str, plan: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pages = split_pdf_pages(text)
    manifest_rows = []
    text_rows = []
    for item in plan:
        start, end, passage = _page_line_slice(
            pages, item["pdf_page"], item["line_start"], item["line_end"],
        )
        digest = sha256_bytes(passage.encode("utf-8"))
        manifest_row = {
            "passage_id": item["passage_id"],
            "pdf_pages": [item["pdf_page"]],
            "clause_identifier": item["clause_identifier"],
            "extraction_start": start,
            "extraction_end": end,
            "character_count": len(passage),
            "text_sha256": digest,
            "families": list(item["families"]),
            "difficulty": item["difficulty"],
        }
        manifest_rows.append(manifest_row)
        text_rows.append({**manifest_row, "text": passage})
    return manifest_rows, text_rows


def validate_manifest_against_text(manifest: Mapping[str, Any], text: str) -> None:
    for row in manifest["passages"]:
        passage = text[row["extraction_start"]:row["extraction_end"]]
        if len(passage) != row["character_count"]:
            raise CorpusPreparationError(
                f"passage length does not replay: {row['passage_id']}"
            )
        if sha256_bytes(passage.encode("utf-8")) != row["text_sha256"]:
            raise CorpusPreparationError(
                f"passage hash does not replay: {row['passage_id']}"
            )


def _assert_external_output(directory: Path) -> Path:
    resolved = directory.resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise CorpusPreparationError(
            "contract-text output must be outside the repository"
        )
    return resolved


def _atomic_write(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def prepare(
    source: Path,
    selection_plan: Path,
    external_output: Path,
    manifest_output: Path,
    *,
    pdftotext: str = "pdftotext",
) -> dict[str, Any]:
    source_row = source_identity(source)
    tool_version = pdftotext_version(pdftotext)
    text = extract_twice(
        source,
        lambda source_path, output_path: poppler_extract(
            source_path, output_path, pdftotext,
        ),
        expected_sha256=EXTRACTION_SHA256,
        expected_bytes=EXTRACTION_BYTES,
        expected_pages=SOURCE_PDF_PAGES,
    )
    plan = load_selection_plan(selection_plan)
    manifest_rows, text_rows = build_passages(text, plan)
    terms = extract_defined_terms(text)

    shortlist = {
        "version": SHORTLIST_VERSION,
        "source_pdf_sha256": SOURCE_SHA256,
        "extraction_sha256": EXTRACTION_SHA256,
        "passages": text_rows,
    }
    term_payload = {
        "version": GLOSSARY_CANDIDATE_VERSION,
        "source_pdf_sha256": SOURCE_SHA256,
        "extraction_sha256": EXTRACTION_SHA256,
        "surface_forms_only": True,
        "terms": terms,
        "term_count": len(terms),
        "total_characters": sum(len(term) for term in terms),
        "terms_sha256": sha256_bytes(compact_json(terms)),
    }
    extracted_bytes = text.encode("utf-8")
    shortlist_bytes = pretty_json(shortlist)
    term_bytes = pretty_json(term_payload)
    family_counts = Counter(
        family for row in manifest_rows for family in row["families"]
    )
    difficulty_counts = Counter(row["difficulty"] for row in manifest_rows)
    manifest = {
        "version": MANIFEST_VERSION,
        "contract_text_committed": False,
        "source": source_row,
        "extraction": {
            "tool": "pdftotext",
            "tool_version": tool_version,
            "arguments": list(PDFTOTEXT_ARGUMENTS),
            "sha256": sha256_bytes(extracted_bytes),
            "byte_count": len(extracted_bytes),
            "character_count": len(text),
            "pdf_page_count": len(split_pdf_pages(text)),
            "external_file_name": EXTRACTED_FILE_NAME,
        },
        "glossary_candidate": {
            "version": GLOSSARY_CANDIDATE_VERSION,
            "definition_pdf_pages": [DEFINITION_START[0], DEFINITION_END[0]],
            "surface_forms_only": True,
            "term_count": len(terms),
            "total_characters": sum(len(term) for term in terms),
            "terms_sha256": term_payload["terms_sha256"],
            "external_file_name": GLOSSARY_FILE_NAME,
            "external_file_sha256": sha256_bytes(term_bytes),
            "external_file_bytes": len(term_bytes),
        },
        "shortlist": {
            "passage_count": len(manifest_rows),
            "total_contract_characters": sum(
                row["character_count"] for row in manifest_rows
            ),
            "family_coverage": {
                family: family_counts[family] for family in sorted(FAMILIES)
            },
            "difficulty_coverage": {
                difficulty: difficulty_counts[difficulty]
                for difficulty in sorted(DIFFICULTIES)
            },
            "external_file_name": SHORTLIST_FILE_NAME,
            "external_file_sha256": sha256_bytes(shortlist_bytes),
            "external_file_bytes": len(shortlist_bytes),
        },
        "passages": manifest_rows,
    }
    validate_manifest_against_text(manifest, text)
    encoded_manifest = pretty_json(manifest)
    if b"/Volumes/" in encoded_manifest or str(source).encode("utf-8") in encoded_manifest:
        raise CorpusPreparationError("manifest depends on the removable source path")

    directory = _assert_external_output(external_output)
    _atomic_write(directory / EXTRACTED_FILE_NAME, extracted_bytes)
    _atomic_write(directory / SHORTLIST_FILE_NAME, shortlist_bytes)
    _atomic_write(directory / GLOSSARY_FILE_NAME, term_bytes)
    _atomic_write(manifest_output, encoded_manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-pdf", type=Path, required=True)
    parser.add_argument("--selection-plan", type=Path, required=True)
    parser.add_argument("--external-output", type=Path, required=True)
    parser.add_argument("--manifest-output", type=Path, required=True)
    parser.add_argument("--pdftotext", default="pdftotext")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = prepare(
            args.source_pdf,
            args.selection_plan,
            args.external_output,
            args.manifest_output,
            pdftotext=args.pdftotext,
        )
    except CorpusPreparationError as error:
        raise SystemExit(f"WP-42 corpus preparation failed closed: {error}") from None
    print(json.dumps({
        "version": VERSION,
        "source_sha256": manifest["source"]["sha256"],
        "extraction_sha256": manifest["extraction"]["sha256"],
        "passage_count": manifest["shortlist"]["passage_count"],
        "term_count": manifest["glossary_candidate"]["term_count"],
        "contract_text_committed": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
