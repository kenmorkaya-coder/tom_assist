import { useEffect, useState } from "preact/hooks";
import type { DesktopBackend } from "./backend";
import { tauriBackend } from "./backend";
import type { AuditEvent, InterventionRecord, Project, StateObject } from "./types";

type View = "Overview" | "Ledger" | "Interventions" | "Audit" | "Settings" | "Diagnostics";
const views: View[] = ["Overview", "Ledger", "Interventions", "Audit", "Settings", "Diagnostics"];

export function App({ backend = tauriBackend }: { backend?: DesktopBackend }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [active, setActive] = useState<Project>();
  const [objects, setObjects] = useState<StateObject[]>([]);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [interventions, setInterventions] = useState<InterventionRecord[]>([]);
  const [view, setView] = useState<View>("Overview");
  const [diagnostics, setDiagnostics] = useState<Record<string, unknown>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [projectName, setProjectName] = useState("");

  const refresh = async (preferredId?: string) => {
    const rows = await backend.listProjects();
    const chosen = rows.find((row) => row.id === (preferredId ?? active?.id)) ?? rows[0];
    setProjects(rows); setActive(chosen);
    setProjectName(chosen?.name ?? "");
    if (chosen) {
      const [state, audit, reviews] = await Promise.all([backend.state(chosen.id), backend.audit(chosen.id), backend.interventions(chosen.id)]);
      setObjects(state.objects); setEvents(audit); setInterventions(reviews);
    }
  };
  useEffect(() => {
    void backend.seedDemo().then((project) => refresh(project.id)).catch((reason) => setError(String(reason)));
  }, []);
  const run = async (work: () => Promise<void>) => {
    setBusy(true); setError("");
    try { await work(); await refresh(); } catch (reason) { setError(String(reason)); } finally { setBusy(false); }
  };

  return <div class="app-shell">
    <aside>
      <p class="brand">TOM ASSIST</p><h1>Release console</h1>
      <label>Project<select aria-label="Active project" value={active?.id} onChange={(event) => void refresh(event.currentTarget.value)}>{projects.map((project) => <option value={project.id}>{project.name}</option>)}</select></label>
      <button onClick={() => void (async () => { setBusy(true); try { const project = await backend.createProject("New Project"); await refresh(project.id); } finally { setBusy(false); } })()}>＋ New project</button>
      <nav>{views.map((item) => <button class={view === item ? "active" : ""} onClick={() => setView(item)}>{item}</button>)}</nav>
      <p class="local-badge">● Local only · SQLite WAL</p>
    </aside>
    <main>
      <header><div><p class="eyebrow">{view}</p><h2>{active?.name ?? "No project"}</h2></div><span class="version">STATE V{active?.state_version ?? 0}</span></header>
      {error && <p role="alert" class="error-banner">{error}</p>}
      {view === "Overview" && <section class="overview"><article><span>State objects</span><strong>{objects.length}</strong></article><article><span>Audit events</span><strong>{events.length}</strong></article><article><span>Open interventions</span><strong>{interventions.filter((row) => row.status === "open").length}</strong></article><button disabled={!active || busy} onClick={() => active && void run(() => backend.capture(active, "Document user-gated workflow"))}>Quick capture decision</button></section>}
      {view === "Ledger" && <section class="card-grid">{objects.map((object) => <StateCard object={object} onSupersede={() => active && void run(() => backend.supersede(active, object))}/>)}</section>}
      {view === "Interventions" && <section>{interventions.length ? interventions.map((item) => <article class="intervention"><strong>{item.code}</strong><span>{item.severity} · {item.status}</span><p>{item.summary}</p><small>Evidence: {item.conflicting_state_ids.join(", ") || "none"}</small>{item.status === "open" && <div><button onClick={() => void run(() => backend.resolveIntervention(item.id, "accepted"))}>Accept finding</button><button onClick={() => void run(() => backend.resolveIntervention(item.id, "false_positive"))}>Mark false positive</button></div>}</article>) : <Empty text="No open interventions in this project."/>}</section>}
      {view === "Audit" && <section class="timeline">{events.map((event) => <article><span>{event.event_type}</span><strong>V{event.base_state_version} → V{event.base_state_version + (event.event_type === "PROJECT_CREATED" ? 0 : 1)}</strong><code>{event.resulting_digest.slice(0, 24)}</code></article>)}</section>}
      {view === "Settings" && <section class="settings"><label>Project name<input aria-label="Project name" value={projectName} onInput={(event) => setProjectName(event.currentTarget.value)}/></label><button disabled={!active || !projectName.trim()} onClick={() => active && void run(async () => { await backend.rename(active, projectName); })}>Rename project</button><label>Packet budget<input aria-label="Packet budget" type="number" value="500" min="1" max="1200"/></label><label>Retention<select><option>State-focused</option><option>Full local</option><option>Ephemeral transcript</option></select></label><label>Export directory<input aria-label="Export directory" value="/tmp/tom-assist-export"/></label><button disabled={!active} onClick={() => active && void run(async () => { await backend.exportProject(active.id, "/tmp/tom-assist-export"); })}>Export verified archive</button><button onClick={() => void run(async () => { const imported = await backend.importProject("/tmp/tom-assist-export"); await refresh(imported.id); })}>Import verified archive</button><button disabled={!active} onClick={() => active && void run(async () => { await backend.archive(active); })}>Archive project</button></section>}
      {view === "Diagnostics" && <section><button onClick={() => void backend.diagnostics().then(setDiagnostics)}>Run local diagnostics</button><pre>{JSON.stringify(diagnostics, null, 2)}</pre></section>}
    </main>
  </div>;
}

function StateCard({ object, onSupersede }: { object: StateObject; onSupersede(): void }) {
  return <article class="state-card" data-testid={`state-${object.id}`}>
    <div class="card-top"><span>{object.type}</span><b>{object.status}</b></div><h3>{object.title}</h3><p>{object.canonical_text}</p>
    <dl><dt>Binding</dt><dd>{object.binding_strength ?? "none"}</dd><dt>Authority</dt><dd>{object.authority}</dd><dt>Effective</dt><dd>{object.effective_at}</dd><dt>Sources</dt><dd>{[...object.source_turn_ids, ...object.evidence_ids].join(", ") || "none"}</dd><dt>Supersession</dt><dd>{object.supersedes_id ? `replaces ${object.supersedes_id}` : object.status === "superseded" ? "superseded" : "current"}</dd><dt>Last packet</dt><dd>{object.last_selection_reason ?? "not selected in latest packet"}</dd></dl>
    {object.status !== "superseded" && <button onClick={onSupersede}>Supersede with reason</button>}
  </article>;
}
function Empty({ text }: { text: string }) { return <p class="empty">{text}</p>; }
