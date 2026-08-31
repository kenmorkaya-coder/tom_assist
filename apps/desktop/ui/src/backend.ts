import { invoke } from "@tauri-apps/api/core";
import type { AuditEvent, CanonicalState, InterventionRecord, Project, StateObject } from "./types";

export interface MemorySettings { front_row_capacity: number; teach_on_conflict: boolean; }
export interface PreparedExchange { packet: { packet_digest: string; activated_branch_ids: string[]; retrieved_anchor_ids: string[] }; packet_text: string; }

export interface DesktopBackend {
  seedDemo(): Promise<Project>;
  listProjects(): Promise<Project[]>;
  createProject(name: string): Promise<Project>;
  rename(project: Project, name: string): Promise<Project>;
  state(projectId: string): Promise<CanonicalState>;
  capture(project: Project, title: string): Promise<void>;
  supersede(project: Project, object: StateObject): Promise<void>;
  audit(projectId: string): Promise<AuditEvent[]>;
  interventions(projectId: string): Promise<InterventionRecord[]>;
  resolveIntervention(projectId: string, interventionId: string, status: "accepted" | "false_positive" | "dismissed"): Promise<void>;
  archive(project: Project): Promise<Project>;
  diagnostics(projectId: string, afterEventId?: number): Promise<Record<string, unknown>>;
  memorySettings(projectId: string, settings?: Partial<MemorySettings>): Promise<MemorySettings>;
  exportProject(projectId: string, directory: string): Promise<string>;
  importProject(directory: string): Promise<Project>;
  backupProject(projectId: string, directory: string): Promise<string>;
  verifyArchive(directory: string): Promise<Record<string, unknown>>;
  exchange(projectId: string, method: "turn.prepare" | "turn.sent" | "response.evaluate", payload: Record<string, unknown>): Promise<unknown>;
}

function now(): string { return new Date().toISOString(); }
function id(): string { return crypto.randomUUID(); }

export const tauriBackend: DesktopBackend = {
  seedDemo: () => invoke("seed_demo"),
  listProjects: () => invoke("list_projects"),
  createProject: (name) => invoke("create_project", { request: { id: id(), name, retention_profile: "state-focused", created_at: now() } }),
  rename: (project, name) => invoke("rename_project", { projectId: project.id, name, updatedAt: now() }),
  state: (projectId) => invoke("project_state", { projectId }),
  async capture(project, title) {
    const timestamp = now();
    const object: StateObject = {
      id: id(), project_id: project.id, workstream_id: "desktop-main", type: "DECISION",
      title, canonical_text: title, status: "active", authority: "user", confidence: 1,
      binding_strength: "hard", source_turn_ids: [], evidence_ids: [], branch_refs: [],
      created_at: timestamp, updated_at: timestamp, effective_at: timestamp,
      content_hash: `desktop:${title}`, state_version: project.state_version + 1,
    };
    await invoke("capture_state", { request: { object, base_state_version: project.state_version, actor_id: "desktop-user", idempotency_key: id(), created_at: timestamp } });
  },
  async supersede(project, object) {
    const timestamp = now();
    const replacement = { ...object, id: id(), title: `${object.title} · revised`, canonical_text: `${object.canonical_text} (revised with explicit user approval)`, status: "active", supersedes_id: object.id, created_at: timestamp, updated_at: timestamp, effective_at: timestamp, state_version: project.state_version + 1 };
    await invoke("supersede_state", { request: { project_id: project.id, old_id: object.id, replacement, reason: "Explicit desktop smoke-test revision", base_state_version: project.state_version, actor_id: "desktop-user", idempotency_key: id(), created_at: timestamp } });
  },
  audit: (projectId) => invoke("audit_events", { projectId }),
  interventions: (projectId) => invoke("list_interventions", { projectId }),
  resolveIntervention: (projectId, interventionId, status) => invoke("resolve_intervention", { projectId, interventionId, status, resolvedAt: now() }),
  archive: (project) => invoke("archive_project", { projectId: project.id, updatedAt: now() }),
  diagnostics: (projectId, afterEventId = 0) => invoke("diagnostics", { projectId, afterEventId }),
  memorySettings: (projectId, settings = {}) => invoke("memory_settings", { projectId, settings }),
  exportProject: (projectId, directory) => invoke("export_project", { projectId, directory }),
  importProject: (directory) => invoke("import_project", { directory }),
  backupProject: (projectId, directory) => invoke("backup_project", { projectId, directory }),
  verifyArchive: (directory) => invoke("verify_archive", { directory }),
  exchange: (projectId, method, payload) => invoke("exchange_request", { envelope: {
    protocol: "tom-assist/1.0", request_id: id(), idempotency_key: id(), method,
    actor: { type: "desktop", instance_id: id() }, project_id: projectId,
    payload: { ...payload, project_id: projectId }, sent_at: now(),
  } }),
};
