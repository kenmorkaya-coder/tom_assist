import type { DesktopBackend } from "./backend";
import type { AuditEvent, CanonicalState, InterventionRecord, Project, StateObject } from "./types";

export class FakeDesktopBackend implements DesktopBackend {
  private projects: Project[] = [];
  private states = new Map<string, CanonicalState>();
  private events = new Map<string, AuditEvent[]>();

  async seedDemo(): Promise<Project> {
    if (this.projects.length) return this.projects[0]!;
    return this.createProject("Local Release Console");
  }
  async listProjects(): Promise<Project[]> { return structuredClone(this.projects); }
  async createProject(name: string): Promise<Project> {
    const project: Project = { id: crypto.randomUUID(), name, status: "active", state_version: 0, state_digest: "sha256:empty", retention_profile: "state-focused", policy_profile: "context-policy/1.1", created_at: new Date().toISOString(), updated_at: new Date().toISOString() };
    this.projects.unshift(project); this.states.set(project.id, { project_id: project.id, state_version: 0, objects: [], edges: [] });
    this.events.set(project.id, [this.event("PROJECT_CREATED", 0)]); return structuredClone(project);
  }
  async rename(project: Project, name: string): Promise<Project> { project.name = name; return structuredClone(project); }
  async state(projectId: string): Promise<CanonicalState> { return structuredClone(this.states.get(projectId)!); }
  async capture(project: Project, title: string): Promise<void> {
    const state = this.states.get(project.id)!; state.state_version += 1;
    state.objects.push(this.object(project.id, title, state.state_version)); this.update(project.id, state.state_version);
    this.events.get(project.id)!.push(this.event("STATE_COMMITTED", state.state_version - 1));
  }
  async supersede(project: Project, object: StateObject): Promise<void> {
    const state = this.states.get(project.id)!; state.state_version += 1;
    const stored = state.objects.find((row) => row.id === object.id)!; stored.status = "superseded"; stored.state_version = state.state_version;
    state.objects.push({ ...this.object(project.id, `${object.title} · revised`, state.state_version), supersedes_id: object.id });
    this.update(project.id, state.state_version); this.events.get(project.id)!.push(this.event("STATE_SUPERSEDED", state.state_version - 1));
  }
  async audit(projectId: string): Promise<AuditEvent[]> { return structuredClone(this.events.get(projectId) ?? []); }
  async interventions(_projectId: string): Promise<InterventionRecord[]> { return []; }
  async resolveIntervention(_interventionId: string, _status: "accepted" | "false_positive"): Promise<void> {}
  async archive(project: Project): Promise<Project> { project.status = "archived"; return structuredClone(project); }
  async diagnostics(): Promise<Record<string, unknown>> { return { database_replay_ok: true, network_services: false }; }
  async exportProject(_projectId: string, directory: string): Promise<string> { return directory; }
  async importProject(_directory: string): Promise<Project> { return this.createProject("Imported project"); }
  private update(id: string, version: number) { const project = this.projects.find((row) => row.id === id)!; project.state_version = version; project.state_digest = `sha256:v${version}`; }
  private event(type: string, base: number): AuditEvent { return { id: crypto.randomUUID(), event_type: type, actor_type: "user", actor_id: "desktop", base_state_version: base, prior_digest: `sha256:v${base}`, resulting_digest: `sha256:v${base + 1}`, created_at: new Date().toISOString() }; }
  private object(projectId: string, title: string, version: number): StateObject { const at = new Date().toISOString(); return { id: crypto.randomUUID(), project_id: projectId, type: "DECISION", title, canonical_text: title, status: "active", authority: "user", confidence: 1, binding_strength: "hard", source_turn_ids: ["desktop-capture"], evidence_ids: [], branch_refs: [], created_at: at, updated_at: at, effective_at: at, content_hash: `sha256:${title}`, state_version: version, last_selection_reason: "manual structured capture" }; }
}
