import { render } from "preact";
import { useEffect, useState } from "preact/hooks";
import "./styles.css";

interface StoredSummary {
  objective?: string;
  decisions?: string[];
  rejected?: string[];
  dependencies?: string[];
  interventions?: string[];
}

function App() {
  const [projectId, setProjectId] = useState("");
  const [projectName, setProjectName] = useState("");
  const [summary, setSummary] = useState<StoredSummary>({});
  useEffect(() => { void chrome.storage.local.get(["activeProjectId", "activeProjectName", "ledgerSummary"]).then((stored) => { setProjectId(String(stored.activeProjectId ?? "")); setProjectName(String(stored.activeProjectName ?? "")); setSummary((stored.ledgerSummary as StoredSummary | undefined) ?? {}); }); }, []);
  const attach = async () => { await chrome.storage.local.set({ activeProjectId: projectId, activeProjectName: projectName || projectId }); };
  const detach = async () => { await chrome.storage.local.remove(["activeProjectId", "activeProjectName", "ledgerSummary"]); setProjectId(""); setProjectName(""); setSummary({}); };
  return <section class="shell"><p class="eyebrow">TOM ASSIST</p><h1>Project continuity</h1><label>Project ID<input aria-label="Project ID" value={projectId} onInput={(event) => setProjectId(event.currentTarget.value)}/></label><label>Project name<input aria-label="Project name" value={projectName} onInput={(event) => setProjectName(event.currentTarget.value)}/></label><div><button disabled={!projectId.trim()} onClick={() => void attach()}>Attach project</button><button disabled={!projectId} onClick={() => void detach()}>Detach</button></div><span class="status">{projectId ? `Attached · ${projectName || projectId}` : "Awaiting project"}</span><Summary title="Active objective" values={summary.objective ? [summary.objective] : []}/><Summary title="Held decisions" values={summary.decisions}/><Summary title="Rejected paths" values={summary.rejected}/><Summary title="Unresolved dependencies" values={summary.dependencies}/><Summary title="Recent interventions" values={summary.interventions}/><p class="privacy">Local native messaging only. No cookies or private provider APIs.</p></section>;
}

function Summary({ title, values = [] }: { title: string; values?: string[] }) { return <section class="summary"><h2>{title}</h2>{values.length ? <ul>{values.map((value) => <li>{value}</li>)}</ul> : <p>None captured.</p>}</section>; }

render(<App />, document.getElementById("app")!);
