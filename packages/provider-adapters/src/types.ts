export interface ProviderDetection {
  provider: string;
  supported: boolean;
  confidence: number;
  adapterVersion: string;
  reasons: string[];
}

export interface ConversationIdentity {
  provider: string;
  conversationKey: string;
  visibleTitle: string;
}

export type ProviderRole = "user" | "assistant";

export interface ProviderTurn {
  provider: string;
  conversationKey: string;
  role: ProviderRole;
  ordinal: number;
  normalizedText: string;
  contentHash: string;
  providerTimestamp?: string;
  complete: boolean;
}

export interface ProviderTurnEvent {
  kind: "turn.visible" | "turn.complete" | "turn.incomplete";
  turn: ProviderTurn;
}

export type Unsubscribe = () => void;
export type SubmitDecision = "continue" | "pause" | "cancel";
export type SubmitInterceptor = (draft: string, event: Event) => Promise<SubmitDecision>;

export interface StreamingState {
  streaming: boolean;
  stable: boolean;
}

export interface PanelMount {
  element: HTMLElement;
  destroy(): void;
}

// EXT-001 contract, kept verbatim in method shape from specification §8.1.
export interface ProviderAdapter {
  detect(): Promise<ProviderDetection>;
  getConversationIdentity(): Promise<ConversationIdentity>;
  enumerateVisibleTurns(): Promise<ProviderTurn[]>;
  observeTurnEvents(cb: (event: ProviderTurnEvent) => void): Unsubscribe;
  readDraft(): Promise<string>;
  writeDraft(text: string): Promise<void>;
  interceptSubmit(cb: SubmitInterceptor): Unsubscribe;
  getStreamingState(): Promise<StreamingState>;
  mountPanel(host: HTMLElement): PanelMount;
}
