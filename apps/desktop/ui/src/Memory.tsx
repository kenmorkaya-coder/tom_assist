import { useEffect, useState } from "preact/hooks";
import type { DesktopBackend, ProjectDocument } from "./backend";

interface MemoryReport {
  front_row_capacity?: number;
  front_row_count?: number;
  library_count?: number;
  demotion_count?: number;
  document_count?: number;
  document_count_all?: number;
  document_bytes?: number;
  document_chunk_count?: number;
}

function count(value: number | undefined) {
  return Number.isFinite(value) ? Number(value).toLocaleString() : "—";
}

function bytes(value: number) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KiB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MiB`;
}

export function Memory({
  projectId,
  backend,
}: {
  projectId: string;
  backend: DesktopBackend;
}) {
  const [report, setReport] = useState<MemoryReport>();
  const [documents, setDocuments] = useState<ProjectDocument[]>([]);
  const [error, setError] = useState("");
  const [canImport, setCanImport] = useState(false);
  const [structural, setStructural] = useState<{ configured: boolean; learned_situations: number; learned_relationship_memories?: number; learned_structural_memories?: number; capacity: number }>();
  const [sourcePath, setSourcePath] = useState("");
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState("");
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let current = true;
    setCanImport(false);
    void backend.chat(projectId, "conversation.native_answer", { action: "status" })
      .then((state) => { if (current) {
        const status = state as { engine?: string; structural_memory?: { configured: boolean; learned_situations: number; learned_relationship_memories?: number; capacity: number } };
        setCanImport(Boolean(status.engine?.startsWith("rgm")));
        setStructural(status.structural_memory);
      } })
      .catch(() => {});
    void Promise.all([backend.diagnostics(projectId), backend.documents(projectId)])
      .then(([diagnostics, rows]) => {
        if (!current) return;
        setReport((diagnostics.memory ?? {}) as MemoryReport);
        setDocuments(rows);
      })
      .catch((reason) => current && setError(String(reason)));
    return () => {
      current = false;
    };
  }, [projectId, backend, revision]);

  async function importDocument() {
    setImporting(true); setError(""); setImportResult("");
    try {
      const result = await backend.chat(projectId, "document.ingest", {
        explicit_user_action: true, source_path: sourcePath.trim(),
      }) as { display_name: string; chunk_count: number; duplicate: boolean };
      setImportResult(`${result.duplicate ? "Already imported" : "Imported"}: ${result.display_name} · ${result.chunk_count} passages`);
      setRevision((value) => value + 1);
    } catch (reason) { setError(String(reason)); }
    finally { setImporting(false); }
  }

  return (
    <section class="memory-view" aria-label="Project memory">
      <p class="memory-boundary">
        This memory belongs only to the selected project. Nothing on these shelves is
        searched from another project.
      </p>
      {error && <p role="alert">{error}</p>}
      {canImport && <section aria-label="Import project document">
        <h3>Import a document</h3>
        <p>PDF, text or Markdown. The file stays on this computer.</p>
        <label>Full file path<input aria-label="Document file path" value={sourcePath}
          onInput={(event) => setSourcePath(event.currentTarget.value)} disabled={importing} /></label>
        <button disabled={importing || !sourcePath.trim()} onClick={() => void importDocument()}>
          {importing ? "Importing document…" : "Import document"}
        </button>
        {importing && <p role="status">Reading the document and preparing its passages.</p>}
        {importResult && <p role="status">{importResult}</p>}
      </section>}
      <div class="memory-shelves">
        <article>
          <span>Front shelf</span>
          <strong>
            {count(report?.front_row_count)} / {count(report?.front_row_capacity)}
          </strong>
          <p>What is in play now. Bounded; faded or displaced records move off it.</p>
        </article>
        <article>
          <span>Long shelf</span>
          <strong>{count(report?.library_count)} permanent records</strong>
          <p>
            Original committed words are retained. {count(report?.demotion_count)} shelf
            moves have been recorded.
          </p>
        </article>
        <article>
          <span>Documents</span>
          <strong>{count(report?.document_count)} active documents</strong>
          <p>
            {count(report?.document_chunk_count)} finding chunks · {bytes(report?.document_bytes ?? 0)}
            stored whole. Import alone never changes the tree.
          </p>
        </article>
        {structural?.configured && <article>
          <span>Reviewed structural memories</span>
          <strong>{count(structural.learned_structural_memories ?? structural.learned_relationship_memories ?? structural.learned_situations)} / {count(structural.capacity)}</strong>
          <p>Saved in the small ToM tree only after an explicit source review.</p>
        </article>}
      </div>
      <h3>Permanent project documents</h3>
      {documents.length ? (
        <div class="memory-documents">
          {documents.map((document) => (
            <article key={document.document_id}>
              <div>
                <h4>{document.display_name}</h4>
                <p>
                  {bytes(document.byte_length)} · {document.chunk_count.toLocaleString()} finding
                  chunks · {document.tombstoned_at ? "withdrawn" : "active"}
                </p>
              </div>
              <code>{document.content_sha256}</code>
            </article>
          ))}
        </div>
      ) : (
        <p class="empty">No permanent documents in this project.</p>
      )}
    </section>
  );
}
