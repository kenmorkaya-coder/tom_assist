import type {
  ChatMethod,
  DesktopBackend,
  MemorySettings,
  ProjectDocument,
} from "./backend";
import type { Conversation, ConversationView, Exchange } from "./Chat";
import type {
  AuditEvent,
  CanonicalState,
  InterventionRecord,
  Project,
  StateObject,
} from "./types";

export class FakeDesktopBackend implements DesktopBackend {
  private projects: Project[] = [];
  private states = new Map<string, CanonicalState>();
  private events = new Map<string, AuditEvent[]>();
  private settings = new Map<string, MemorySettings>();
  private sessions = new Map<string, ConversationView>();
  private projectDocuments = new Map<string, ProjectDocument[]>();
  connected = true; // Test-only transport, never an OAuth client.

  async oauthStatus() {
    return {
      connected: this.connected,
      code: this.connected ? "OAUTH_READY" : "OAUTH_NOT_CONNECTED",
      model: "fixture",
    };
  }
  async oauthLogin() {
    this.connected = true;
    return this.oauthStatus();
  }
  async oauthLogout() {
    this.connected = false;
    return this.oauthStatus();
  }

  async chat(
    projectId: string,
    method: ChatMethod,
    payload: Record<string, unknown>,
  ): Promise<unknown> {
    if (method === "provider.status")
      return {
        connected: this.connected,
        code: this.connected ? "FIXTURE_READY" : "OAUTH_DISCONNECTED",
        model: "fixture",
        capabilities: {
          hidden_context_visibility: false,
          model_internal_bias: "none",
        },
      };
    if (method === "conversation.list")
      return structuredClone(
        [...this.sessions.values()]
          .filter((v) => v.session.project_id === projectId)
          .map((v) => v.session),
      );
    if (method === "conversation.create") {
      const session: Conversation = {
        id: String(payload.session_id),
        project_id: projectId,
        title: String(payload.title),
        created_at: new Date().toISOString(),
      };
      this.sessions.set(session.id, {
        session,
        exchanges: [],
        interventions: [],
      });
      return structuredClone(session);
    }
    const view = [...this.sessions.values()].find(
      (v) =>
        v.session.project_id === projectId &&
        (v.session.id === payload.session_id ||
          v.exchanges.some((e) => e.exchange.id === payload.exchange_id)),
    );
    if (!view) throw new Error("Project conversation missing");
    if (method === "conversation.prepare") {
      const exchange: Exchange = {
        id: String(payload.exchange_id),
        session_id: view.session.id,
        project_id: projectId,
        user_draft: String(payload.user_draft),
        prompt: `[TOM_ASSIST_STATE v1] fixture\n${payload.user_draft}`,
        prompt_hash: "fixture-hash",
        packet_digest: "fixture-packet",
        status: "prepared",
        context_preview: {
          sections: [
            {
              type: "EVIDENCE_BOUNDARY",
              items: [
                {
                  state_id: "document-fixture:chunk:4",
                  text: "4.2 Release checks\n\nBefore release, the team must:\n\n(a) verify the package; and\n\n(b) record the receipt.",
                  authority: "user_supplied_document",
                  structural_score: 0,
                  semantic_score: 0.8,
                  reason_selected: "hard-gate-pass + ranked",
                },
              ],
            },
          ],
          excluded: [
            { id: "document-fixture:chunk:8", reason: "packet-budget" },
          ],
          document_research: {
            final_evidence_coverage: {
              discovered_units: [
                {
                  evidence_id: "document-fixture:chunk:4",
                  clause_identifier: "4.2",
                  conditionality: ["project_wide"],
                  packet_admitted: true,
                },
                {
                  evidence_id: "document-fixture:chunk:8",
                  clause_identifier: "8.1",
                  conditionality: ["activity_conditional"],
                  packet_admitted: false,
                  packet_exclusion_reason: "packet-budget",
                },
              ],
              missing_sources: [
                { named_identifier: "Schedule Z", reason_code: "MISSING_REFERENCED_SOURCE" },
              ],
              exhaustiveness: "limited_by_missing_referenced_sources",
            },
          },
        },
      };
      view.exchanges.push({ exchange });
      return structuredClone(exchange);
    }
    if (method === "conversation.send") {
      if (
        !this.connected ||
        payload.explicit_send !== true ||
        payload.confirmed_prompt_hash !== "fixture-hash"
      )
        throw new Error("Explicit connected send required");
      const row = view.exchanges.find(
        (e) => e.exchange.id === payload.exchange_id,
      )!;
      row.exchange.status = "completed";
      row.exchange.response_text =
        "Fixture response: retain the user-gated workflow.";
      row.evaluation = {
        result: "PASS",
        turn_id: `${row.exchange.id}:assistant`,
      };
      row.commit = { receipt: "fixture" };
    }
    return structuredClone(view);
  }
  async captureChatState(
    project: Project,
    sourceTurnId: string,
    text: string,
    oldId?: string,
    _reason?: string,
  ): Promise<void> {
    if (!sourceTurnId.endsWith(":assistant")) throw new Error("Invalid source");
    if (oldId) {
      const old = this.states
        .get(project.id)!
        .objects.find((o) => o.id === oldId)!;
      old.status = "superseded";
    }
    await this.capture(project, text);
  }

  async seedDemo(): Promise<Project> {
    if (this.projects.length) return this.projects[0]!;
    const project = await this.createProject("Local Release Console");
    this.projectDocuments.set(project.id, [
      {
        document_id: "document-fixture",
        display_name: "Project deed.txt",
        content_sha256: "fixture-document-sha256",
        byte_length: 12345,
        media_type: "text/plain",
        chunking_version: "fixture-chunks/1",
        embedding_version: "fixture-embedding/1",
        ingested_tick: 0,
        tombstoned_at: null,
        chunk_count: 24,
      },
    ]);
    return project;
  }
  async listProjects(): Promise<Project[]> {
    return structuredClone(this.projects);
  }
  async createProject(name: string): Promise<Project> {
    const project: Project = {
      id: crypto.randomUUID(),
      name,
      status: "active",
      state_version: 0,
      state_digest: "sha256:empty",
      retention_profile: "state-focused",
      policy_profile: "context-policy/1.3",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    this.projects.unshift(project);
    this.states.set(project.id, {
      project_id: project.id,
      state_version: 0,
      objects: [],
      edges: [],
    });
    this.events.set(project.id, [this.event("PROJECT_CREATED", 0)]);
    this.projectDocuments.set(project.id, []);
    return structuredClone(project);
  }
  async rename(project: Project, name: string): Promise<Project> {
    project.name = name;
    return structuredClone(project);
  }
  async state(projectId: string): Promise<CanonicalState> {
    return structuredClone(this.states.get(projectId)!);
  }
  async capture(project: Project, title: string): Promise<void> {
    const state = this.states.get(project.id)!;
    state.state_version += 1;
    state.objects.push(this.object(project.id, title, state.state_version));
    this.update(project.id, state.state_version);
    this.events
      .get(project.id)!
      .push(this.event("STATE_COMMITTED", state.state_version - 1));
  }
  async supersede(project: Project, object: StateObject): Promise<void> {
    const state = this.states.get(project.id)!;
    state.state_version += 1;
    const stored = state.objects.find((row) => row.id === object.id)!;
    stored.status = "superseded";
    stored.state_version = state.state_version;
    state.objects.push({
      ...this.object(
        project.id,
        `${object.title} · revised`,
        state.state_version,
      ),
      supersedes_id: object.id,
    });
    this.update(project.id, state.state_version);
    this.events
      .get(project.id)!
      .push(this.event("STATE_SUPERSEDED", state.state_version - 1));
  }
  async audit(projectId: string): Promise<AuditEvent[]> {
    return structuredClone(this.events.get(projectId) ?? []);
  }
  async interventions(_projectId: string): Promise<InterventionRecord[]> {
    return [];
  }
  async resolveIntervention(
    _projectId: string,
    _interventionId: string,
    _status: "accepted" | "false_positive" | "dismissed",
  ): Promise<void> {}
  async archive(project: Project): Promise<Project> {
    project.status = "archived";
    return structuredClone(project);
  }
  async diagnostics(projectId: string): Promise<Record<string, unknown>> {
    const documents = this.projectDocuments.get(projectId) ?? [];
    return {
      database_replay_ok: true,
      network_services: false,
      memory: {
        front_row_capacity: 4096,
        front_row_count: 3,
        library_count: 7,
        demotion_count: 4,
        document_count: documents.filter((row) => !row.tombstoned_at).length,
        document_count_all: documents.length,
        document_bytes: documents.reduce((total, row) => total + row.byte_length, 0),
        document_chunk_count: documents.reduce((total, row) => total + row.chunk_count, 0),
      },
    };
  }
  async exportDocumentResearchDiagnostics(projectId: string): Promise<string> {
    return `/fixture/diagnostics/document-research-${projectId}.json`;
  }
  async documents(projectId: string): Promise<ProjectDocument[]> {
    return structuredClone(this.projectDocuments.get(projectId) ?? []);
  }
  async memorySettings(
    projectId: string,
    settings: Partial<MemorySettings> = {},
  ): Promise<MemorySettings> {
    const result = {
      ...(this.settings.get(projectId) ?? {
        front_row_capacity: 4096,
        teach_on_conflict: true,
      }),
      ...settings,
    };
    this.settings.set(projectId, result);
    return structuredClone(result);
  }
  async exportProject(_projectId: string, directory: string): Promise<string> {
    return directory;
  }
  async importProject(_directory: string): Promise<Project> {
    return this.createProject("Imported project");
  }
  async backupProject(projectId: string, directory: string): Promise<string> {
    return this.exportProject(projectId, directory);
  }
  async verifyArchive(_directory: string): Promise<Record<string, unknown>> {
    return { verified: true };
  }
  async exchange(_projectId: string, method: string): Promise<unknown> {
    if (method === "turn.prepare")
      return {
        packet: {
          packet_digest: "fixture-packet",
          activated_branch_ids: ["fixture-branch"],
          retrieved_anchor_ids: [],
        },
        packet_text: "[TOM_ASSIST_STATE v1] fixture",
      };
    return { result: "PASS", diagnostics: [] };
  }
  private update(id: string, version: number) {
    const project = this.projects.find((row) => row.id === id)!;
    project.state_version = version;
    project.state_digest = `sha256:v${version}`;
  }
  private event(type: string, base: number): AuditEvent {
    return {
      id: crypto.randomUUID(),
      event_type: type,
      actor_type: "user",
      actor_id: "desktop",
      base_state_version: base,
      prior_digest: `sha256:v${base}`,
      resulting_digest: `sha256:v${base + 1}`,
      created_at: new Date().toISOString(),
    };
  }
  private object(
    projectId: string,
    title: string,
    version: number,
  ): StateObject {
    const at = new Date().toISOString();
    return {
      id: crypto.randomUUID(),
      project_id: projectId,
      type: "DECISION",
      title,
      canonical_text: title,
      status: "active",
      authority: "user",
      confidence: 1,
      binding_strength: "hard",
      source_turn_ids: ["desktop-capture"],
      evidence_ids: [],
      branch_refs: [],
      created_at: at,
      updated_at: at,
      effective_at: at,
      content_hash: `sha256:${title}`,
      state_version: version,
      last_selection_reason: "manual structured capture",
    };
  }
}
