import { useState } from "preact/hooks";
import type { DesktopBackend } from "./backend";
import type { Project } from "./types";

export function Recovery({ projectId, backend, onImported }: { projectId?: string; backend: DesktopBackend; onImported(project: Project): Promise<void> }) {
  const [directory, setDirectory] = useState("/tmp/tom-assist-recovery");
  const [message, setMessage] = useState("");
  const [verified, setVerified] = useState(false);
  const [busy, setBusy] = useState(false);
  async function run(action: () => Promise<string>) { setBusy(true); setMessage(""); try { setMessage(await action()); } catch (e) { setMessage(String(e)); } finally { setBusy(false); } }
  return <section class="settings"><h3>Complete project recovery</h3>
    <p>Archives and backups include the full retained conversation content, permanent library, runtime, checkpoints and ledger. They are local and unencrypted—not redacted diagnostics. Import preserves project identity and never overwrites an existing project.</p>
    <label>Recovery directory<input aria-label="Recovery directory" value={directory} onInput={e => { setDirectory(e.currentTarget.value); setVerified(false); }}/></label>
    <button disabled={busy || !projectId || !directory.trim()} onClick={() => projectId && void run(async () => `Complete archive saved: ${await backend.exportProject(projectId, directory)}`)}>Export complete project archive</button>
    <button disabled={busy || !projectId || !directory.trim()} onClick={() => projectId && void run(async () => `Verified backup saved: ${await backend.backupProject(projectId, `${directory}-backup-${Date.now()}`)}`)}>Create complete project backup</button>
    <button disabled={busy || !directory.trim()} onClick={() => void run(async () => { setVerified(false); const result = await backend.verifyArchive(directory); setVerified(true); return `Archive verified: ${JSON.stringify(result)}`; })}>Verify recovery archive</button>
    <button disabled={busy || !verified} onClick={() => void run(async () => { const project = await backend.importProject(directory); await onImported(project); return `Project recovered: ${project.name}`; })}>Import verified recovery archive</button>
    {message && <p role="status">{message}</p>}
  </section>;
}
