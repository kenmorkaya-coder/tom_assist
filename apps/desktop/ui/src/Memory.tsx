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

type StructureCandidate = {
  candidate_id: string;
  source_id: string;
  document_id: string;
  display_name: string;
  chunk_id: string;
  chunk_index: number;
  text: string;
  temporal_motif:
    | { relation_kind: "sequence"; source_event: "failure";
        intermediate_event: "substitute_action"; target_event: "cost_recovery" }
    | { relation_kind: "sequence"; source_event: "human_remains_discovered";
        intermediate_event: "stop_work"; target_event: "notify_authorities" };
  events: { kind: string; start: number; end: number; text: string }[];
  reviewed: boolean;
  reviewed_structure_count: number;
  discovery_channels?: {
    rgm_semantic_sweep: boolean;
    rgm_contextual_vector_pass: boolean;
    rgm_native_vector_pass: boolean;
    rgm_rrf_fusion: boolean;
    source_regex: boolean;
  };
  discovery_ranks?: {
    contextual_vector: number | null;
    native_vector: number | null;
    rrf: number | null;
  };
};

type ReviewDiscovery = {
  strategy: string;
  rgm_query_count: number;
  contextual_vector_candidate_count: number;
  native_vector_candidate_count: number;
  rgm_semantic_candidate_count: number;
  regex_candidate_count: number;
  validated_candidate_count: number;
  semantic_rejected_count: number;
};

type AuthoritySource = {
  source_id: string;
  text: string;
  text_sha256: string;
  document_active: boolean;
  provenance: { display_name: string; chunk_id: string; chunk_index: number; start: number; end: number };
};

type SourceAuthorityDecision = {
  decision_id: string;
  relation_kind: string;
  authority_scope: { kind: string; relation_kind?: string; temporal_motif?: {
    source_event: string; intermediate_event: string; target_event: string;
  } };
  controlling_source: AuthoritySource;
  replaced_sources: AuthoritySource[];
  effective_at: string;
  reason: string;
  created_at: string;
  effective_status: "active" | "future";
};

type StructuralMemoryStatus = {
  configured: boolean;
  learned_situations: number;
  learned_relationship_memories?: number;
  learned_structural_memories?: number;
  capacity: number;
  source_authority_links?: number;
};

type SourceAuthorityHistory = {
  as_of: string;
  decisions: SourceAuthorityDecision[];
  read_only: boolean;
  tree_calls: number;
};

function discoveryLabel(candidate: StructureCandidate) {
  const channels = candidate.discovery_channels;
  if (!channels) return "";
  return [
    channels.rgm_semantic_sweep && "RGM semantic sweep",
    channels.rgm_contextual_vector_pass && "contextual vector pass",
    channels.rgm_native_vector_pass && "native RGM vector pass",
    channels.rgm_rrf_fusion && "RRF rank fusion",
    channels.source_regex && "source regex",
  ].filter(Boolean).join(" · ");
}

function structureLabel(candidate: StructureCandidate) {
  return candidate.temporal_motif.source_event === "human_remains_discovered"
    ? "Save human remains discovered → stop work → notify authorities"
    : "Save failure → substitute action → cost recovery";
}

function authorityScopeLabel(decision: SourceAuthorityDecision) {
  const motif = decision.authority_scope.temporal_motif;
  if (motif) return [motif.source_event, motif.intermediate_event, motif.target_event]
    .map((value) => value.replaceAll("_", " ")).join(" → ");
  return (decision.authority_scope.relation_kind ?? decision.relation_kind).replaceAll("_", " ");
}

function sourceLabel(source: AuthoritySource) {
  return `${source.provenance.display_name} · ${source.provenance.chunk_id}`;
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
  const [structural, setStructural] = useState<StructuralMemoryStatus>();
  const [authorityHistory, setAuthorityHistory] = useState<SourceAuthorityHistory>();
  const [sourcePath, setSourcePath] = useState("");
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState("");
  const [candidates, setCandidates] = useState<StructureCandidate[]>();
  const [candidateDiscovery, setCandidateDiscovery] = useState<ReviewDiscovery>();
  const [candidateScanBusy, setCandidateScanBusy] = useState(false);
  const [savingCandidate, setSavingCandidate] = useState("");
  const [candidateMessage, setCandidateMessage] = useState("");
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let current = true;
    setCanImport(false);
    void backend.chat(projectId, "conversation.native_answer", { action: "status" })
      .then(async (state) => { if (current) {
        const status = state as { engine?: string; structural_memory?: StructuralMemoryStatus };
        setCanImport(Boolean(status.engine?.startsWith("rgm")));
        setStructural(status.structural_memory);
        if (status.structural_memory?.source_authority_links) {
          const history = await backend.chat(projectId, "conversation.native_answer", {
            action: "source_authority_history",
          }) as SourceAuthorityHistory;
          if (current) setAuthorityHistory(history);
        } else {
          setAuthorityHistory(undefined);
        }
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

  async function findStructureCandidates() {
    setCandidateScanBusy(true); setError(""); setCandidateMessage("");
    try {
      const result = await backend.chat(projectId, "conversation.native_answer", {
        action: "review_candidates",
      }) as { candidates: StructureCandidate[]; discovery: ReviewDiscovery };
      setCandidates(result.candidates);
      setCandidateDiscovery(result.discovery);
    } catch (reason) { setError(String(reason)); }
    finally { setCandidateScanBusy(false); }
  }

  async function saveStructureCandidate(candidate: StructureCandidate) {
    setSavingCandidate(candidate.candidate_id); setError(""); setCandidateMessage("");
    try {
      const result = await backend.chat(projectId, "conversation.native_answer", {
        action: "learn_situation", explicit_user_action: true,
        document_id: candidate.document_id, chunk_index: candidate.chunk_index,
        temporal_motif: candidate.temporal_motif,
      }) as { duplicate?: boolean; write_count?: number };
      setCandidates((current) => current?.map((item) => item.candidate_id === candidate.candidate_id
        ? { ...item, reviewed: true, reviewed_structure_count: item.reviewed_structure_count + (result.duplicate ? 0 : 1) }
        : item));
      setCandidateMessage(result.duplicate
        ? "This exact structure was already reviewed."
        : result.write_count === 0
          ? "Linked this passage to the existing distributed ToM memories."
          : `Saved this structure across ${Number(result.write_count ?? 0).toLocaleString()} ToM memory locations.`);
      setRevision((value) => value + 1);
    } catch (reason) { setError(String(reason)); }
    finally { setSavingCandidate(""); }
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
      {!!authorityHistory?.decisions.length &&
        <section class="authority-history" aria-label="Source authority history">
          <h3>Source authority history</h3>
          <p>Read-only decisions made by a user. Every passage below is still retained with its source details.</p>
          <div>
            {authorityHistory.decisions.map((decision) => <article key={decision.decision_id}>
              <header>
                <h4>{authorityScopeLabel(decision)}</h4>
                <span class={`authority-status ${decision.effective_status}`}>{decision.effective_status === "active" ? "Active" : "Future"}</span>
              </header>
              <p><strong>Effective:</strong> <time dateTime={decision.effective_at}>{decision.effective_at}</time></p>
              <p><strong>Reason:</strong> {decision.reason}</p>
              <section aria-label="Controlling source">
                <h5>Controlling source</h5>
                <p>{sourceLabel(decision.controlling_source)}</p>
                <blockquote>{decision.controlling_source.text}</blockquote>
              </section>
              <details>
                <summary>Replaced sources ({decision.replaced_sources.length})</summary>
                {decision.replaced_sources.map((source) => <section key={source.source_id}>
                  <h5>{sourceLabel(source)}</h5>
                  <blockquote>{source.text}</blockquote>
                </section>)}
              </details>
            </article>)}
          </div>
        </section>}
      {canImport && documents.length > 0 && <section aria-label="Review detected document structures">
        <h3>Structures to review</h3>
        <p>Run the RGM semantic and vector sweeps, its rank fusion, and the full-source structure check. Nothing is saved in ToM until you review a passage and press Save.</p>
        <button disabled={candidateScanBusy || Boolean(savingCandidate)}
          onClick={() => void findStructureCandidates()}>
          {candidateScanBusy ? "Checking document passages…" : "Find structures to review"}
        </button>
        {candidateDiscovery && <p role="status">RGM semantic candidates: {count(candidateDiscovery.rgm_semantic_candidate_count)} · contextual vector pass: {count(candidateDiscovery.contextual_vector_candidate_count)} · native RGM vector pass: {count(candidateDiscovery.native_vector_candidate_count)} · source regex: {count(candidateDiscovery.regex_candidate_count)} · rejected by local order check: {count(candidateDiscovery.semantic_rejected_count)} · validated: {count(candidateDiscovery.validated_candidate_count)}</p>}
        {candidates && !candidates.length && <p role="status">No matching procedures were found.</p>}
        {!!candidates?.length && <div class="memory-documents">
          {candidates.map((candidate) => <article key={candidate.candidate_id}>
            <div>
              <h4>{candidate.display_name} · {candidate.chunk_id}</h4>
              <p>Detected: {candidate.events.map((event) =>
                `${event.kind.replaceAll("_", " ")} “${event.text.replaceAll(/\s+/g, " ")}”`).join(" → ")}</p>
              {candidate.discovery_channels && <p>Found by: {discoveryLabel(candidate)}</p>}
              {candidate.reviewed_structure_count > 0 && !candidate.reviewed
                && <p>This passage already has {candidate.reviewed_structure_count} other reviewed structure{candidate.reviewed_structure_count === 1 ? "" : "s"}. This one can be stored separately.</p>}
              <details><summary>Review exact passage</summary>
                <p style={{ whiteSpace: "pre-wrap" }}>{candidate.text}</p>
              </details>
              <button disabled={candidate.reviewed || Boolean(savingCandidate)}
                onClick={() => void saveStructureCandidate(candidate)}>
                {candidate.reviewed ? "Already reviewed in ToM"
                  : savingCandidate === candidate.candidate_id ? "Saving reviewed structure…"
                    : structureLabel(candidate)}
              </button>
            </div>
          </article>)}
        </div>}
        {candidateMessage && <p role="status">{candidateMessage}</p>}
      </section>}
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
