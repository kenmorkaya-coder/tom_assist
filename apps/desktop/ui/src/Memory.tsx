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
  useEffect(() => {
    let current = true;
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
  }, [projectId, backend]);

  return (
    <section class="memory-view" aria-label="Project memory">
      <p class="memory-boundary">
        This memory belongs only to the selected project. Nothing on these shelves is
        searched from another project.
      </p>
      {error && <p role="alert">{error}</p>}
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
            stored whole. Documents never push the tree.
          </p>
        </article>
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
