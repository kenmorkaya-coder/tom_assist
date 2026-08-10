import type { ProviderAdapter, ProviderTurn, SubmitDecision, Unsubscribe } from "@tom-assist/provider-adapters";

export type GatePhase = "detached" | "idle" | "preparing" | "preview" | "unavailable";

export interface PacketPreview {
  packetText: string;
  packetDigest: string;
  includedCategories: string[];
  warnings: string[];
  excludedItems: string[];
}

export interface EvaluationBadge {
  result: "PASS" | "REVIEW" | "CONFLICT" | "INCOMPLETE";
  count: number;
  severity: string;
}

export interface ExtensionService {
  prepare(projectId: string, draft: string): Promise<PacketPreview>;
  markSent(projectId: string, draft: string, packetDigest: string): Promise<void>;
  evaluate(projectId: string, turn: ProviderTurn, packetDigest: string): Promise<EvaluationBadge>;
  capture(projectId: string, kind: string, text: string): Promise<void>;
}

export interface GateSnapshot {
  phase: GatePhase;
  projectId?: string;
  projectName?: string;
  draft: string;
  preview?: PacketPreview;
  editablePacket: string;
  warning?: string;
  badge?: EvaluationBadge;
  capturedTurns: number;
}

type Listener = (snapshot: GateSnapshot) => void;

/** User-event-bound state machine for EXT-020..025. */
export class PromptGateController {
  private snapshotValue: GateSnapshot = { phase: "detached", draft: "", editablePacket: "", capturedTurns: 0 };
  private listeners = new Set<Listener>();
  private resolveSubmission?: (decision: SubmitDecision) => void;
  private stopSubmit?: Unsubscribe;
  private stopTurns?: Unsubscribe;

  constructor(private readonly adapter: ProviderAdapter, private readonly service: ExtensionService) {}

  snapshot(): GateSnapshot { return structuredClone(this.snapshotValue); }
  subscribe(listener: Listener): Unsubscribe { this.listeners.add(listener); listener(this.snapshot()); return () => this.listeners.delete(listener); }
  private update(next: Partial<GateSnapshot>) { this.snapshotValue = { ...this.snapshotValue, ...next }; for (const listener of this.listeners) listener(this.snapshot()); }

  async start(): Promise<void> {
    const detection = await this.adapter.detect();
    if (!detection.supported) { this.update({ phase: "detached", warning: detection.reasons.join(", ") }); return; }
    this.stopSubmit = this.adapter.interceptSubmit((draft) => this.beginUserSubmission(draft));
    this.stopTurns = this.adapter.observeTurnEvents((event) => {
      if (event.turn.role === "assistant" && event.turn.complete && event.kind === "turn.complete") void this.captureResponse(event.turn);
    });
    this.update({ phase: this.snapshotValue.projectId ? "idle" : "detached" });
  }

  attachProject(projectId: string, projectName: string): void { this.update({ projectId, projectName, phase: "idle", warning: undefined }); }

  beginUserSubmission(draft: string): Promise<SubmitDecision> {
    if (!this.snapshotValue.projectId) return Promise.resolve("continue");
    if (this.resolveSubmission) return Promise.resolve("cancel");
    this.update({ phase: "preparing", draft, preview: undefined, editablePacket: "", warning: undefined });
    const held = new Promise<SubmitDecision>((resolve) => { this.resolveSubmission = resolve; });
    void this.service.prepare(this.snapshotValue.projectId, draft).then((preview) => {
      this.update({ phase: "preview", preview, editablePacket: preview.packetText });
    }).catch((error) => {
      this.update({ phase: "unavailable", warning: `Local service unavailable: ${String(error)}. Choose an explicit action to continue.` });
    });
    return held;
  }

  editPacket(text: string): void { if (this.snapshotValue.phase === "preview") this.update({ editablePacket: text }); }

  async sendWithTom(): Promise<void> {
    const { projectId, draft, preview, editablePacket } = this.snapshotValue;
    if (!projectId || !preview || !this.resolveSubmission || this.snapshotValue.phase !== "preview") return;
    const visible = `${editablePacket}\n\n[CURRENT_USER_REQUEST]\n${draft}`;
    await this.adapter.writeDraft(visible);
    await this.service.markSent(projectId, draft, preview.packetDigest);
    this.finish("continue", { phase: "idle" });
  }

  sendOnceWithoutTom(): void {
    if (!this.resolveSubmission || !["preview", "unavailable"].includes(this.snapshotValue.phase)) return;
    this.finish("continue", { phase: "idle", warning: this.snapshotValue.phase === "unavailable" ? "Sent once without Tom after explicit user confirmation." : undefined });
  }

  cancel(): void { if (this.resolveSubmission) this.finish("cancel", { phase: "idle" }); }

  detachProject(): void {
    if (this.resolveSubmission) this.finish("cancel", {});
    this.update({ phase: "detached", projectId: undefined, projectName: undefined, preview: undefined, warning: "Project detached." });
  }

  async quickCapture(kind: string, text = this.snapshotValue.draft): Promise<void> {
    if (!this.snapshotValue.projectId) throw new Error("No attached project");
    await this.service.capture(this.snapshotValue.projectId, kind, text);
  }

  async captureResponse(turn: ProviderTurn): Promise<void> {
    const { projectId, preview } = this.snapshotValue;
    if (!projectId || !preview) return;
    const badge = await this.service.evaluate(projectId, turn, preview.packetDigest);
    this.update({ badge, capturedTurns: this.snapshotValue.capturedTurns + 1 });
  }

  destroy(): void { this.stopSubmit?.(); this.stopTurns?.(); this.listeners.clear(); }

  private finish(decision: SubmitDecision, next: Partial<GateSnapshot>) {
    const resolve = this.resolveSubmission;
    this.resolveSubmission = undefined;
    this.update(next);
    resolve?.(decision);
  }
}
