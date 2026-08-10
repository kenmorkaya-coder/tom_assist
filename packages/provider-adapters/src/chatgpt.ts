import type {
  ConversationIdentity,
  PanelMount,
  ProviderAdapter,
  ProviderDetection,
  ProviderRole,
  ProviderTurn,
  ProviderTurnEvent,
  StreamingState,
  SubmitInterceptor,
  Unsubscribe,
} from "./types";

export const CHATGPT_ADAPTER_VERSION = "chatgpt-visible-dom/1.0";

const COMPOSER_SELECTORS = [
  'textarea[data-testid="prompt-textarea"]',
  '[contenteditable="true"][data-testid="prompt-textarea"]',
  "#prompt-textarea",
  '[contenteditable="true"][role="textbox"]',
];
const TURN_SELECTORS = [
  "[data-message-author-role]",
  'article[data-testid^="conversation-turn-"]',
];
const STREAMING_SELECTORS = [
  '[data-testid="stop-button"]',
  '[aria-label*="Stop generating"]',
  '[data-is-streaming="true"]',
];

function first(root: ParentNode, selectors: string[]): HTMLElement | undefined {
  for (const selector of selectors) {
    const element = root.querySelector<HTMLElement>(selector);
    if (element) return element;
  }
  return undefined;
}

function normalize(text: string): string {
  return text.replace(/\u00a0/g, " ").replace(/[ \t]+/g, " ").replace(/\n{3,}/g, "\n\n").trim();
}

async function sha256(text: string): Promise<string> {
  const bytes = new TextEncoder().encode(text);
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return `sha256:${Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
}

function roleFor(element: HTMLElement): ProviderRole | undefined {
  const direct = element.dataset.messageAuthorRole;
  if (direct === "user" || direct === "assistant") return direct;
  const nested = element.querySelector<HTMLElement>("[data-message-author-role]")?.dataset
    .messageAuthorRole;
  return nested === "user" || nested === "assistant" ? nested : undefined;
}

function contentFor(element: HTMLElement): string {
  const content =
    element.querySelector<HTMLElement>("[data-message-content], .markdown, .whitespace-pre-wrap") ??
    element;
  return normalize(content.innerText || content.textContent || "");
}

export class CaptureDeduplicator {
  private readonly seen = new Set<string>();

  accept(turn: ProviderTurn): boolean {
    const key = `${turn.conversationKey}\0${turn.ordinal}\0${turn.contentHash}`;
    if (this.seen.has(key)) return false;
    this.seen.add(key);
    return true;
  }
}

export class ChatGptAdapter implements ProviderAdapter {
  constructor(
    private readonly document: Document,
    private readonly location: Location,
    private readonly detach: (reason: string) => void = () => undefined,
  ) {}

  async detect(): Promise<ProviderDetection> {
    const composer = first(this.document, COMPOSER_SELECTORS);
    const supportedHost = this.location.hostname === "chatgpt.com";
    const reasons = [
      ...(supportedHost ? [] : ["unsupported-host"]),
      ...(composer ? [] : ["composer-selector-missing"]),
    ];
    return {
      provider: "chatgpt",
      supported: reasons.length === 0,
      confidence: reasons.length === 0 ? 1 : 0,
      adapterVersion: CHATGPT_ADAPTER_VERSION,
      reasons,
    };
  }

  async healthCheck(): Promise<ProviderDetection> {
    const detection = await this.detect();
    if (!detection.supported) this.detach(detection.reasons.join(","));
    return detection;
  }

  async getConversationIdentity(): Promise<ConversationIdentity> {
    const declared = this.document.querySelector<HTMLElement>("[data-conversation-id]")?.dataset
      .conversationId;
    return {
      provider: "chatgpt",
      conversationKey: declared || this.location.pathname || "/",
      visibleTitle: normalize(this.document.title || "Untitled ChatGPT conversation"),
    };
  }

  async enumerateVisibleTurns(): Promise<ProviderTurn[]> {
    const identity = await this.getConversationIdentity();
    const nodes = Array.from(
      this.document.querySelectorAll<HTMLElement>(TURN_SELECTORS.join(",")),
    ).filter((node, index, all) => !all.some((other, otherIndex) => otherIndex < index && other.contains(node)));
    const streaming = await this.getStreamingState();
    const turns: ProviderTurn[] = [];
    for (const element of nodes) {
      const role = roleFor(element);
      const normalizedText = contentFor(element);
      if (!role || !normalizedText) continue;
      const ordinal = turns.length;
      const isLastAssistant = role === "assistant" && ordinal === nodes.length - 1;
      turns.push({
        provider: "chatgpt",
        conversationKey: identity.conversationKey,
        role,
        ordinal,
        normalizedText,
        contentHash: await sha256(normalizedText),
        providerTimestamp: element.querySelector("time")?.getAttribute("datetime") ?? undefined,
        complete: !(streaming.streaming && isLastAssistant),
      });
    }
    return turns;
  }

  observeTurnEvents(callback: (event: ProviderTurnEvent) => void): Unsubscribe {
    const deduplicator = new CaptureDeduplicator();
    let stopped = false;
    const emit = async () => {
      if (stopped) return;
      for (const turn of await this.enumerateVisibleTurns()) {
        if (!deduplicator.accept(turn)) continue;
        callback({
          kind: turn.complete ? "turn.complete" : "turn.incomplete",
          turn,
        });
      }
    };
    const observer = new MutationObserver(() => void emit());
    observer.observe(this.document.body, { childList: true, subtree: true, characterData: true });
    void emit();
    return () => {
      stopped = true;
      observer.disconnect();
    };
  }

  async readDraft(): Promise<string> {
    const composer = first(this.document, COMPOSER_SELECTORS);
    if (!composer) throw new Error("ADAPTER_UNSUPPORTED: composer missing");
    return normalize(composer instanceof HTMLTextAreaElement ? composer.value : composer.innerText || composer.textContent || "");
  }

  async writeDraft(text: string): Promise<void> {
    const composer = first(this.document, COMPOSER_SELECTORS);
    if (!composer) throw new Error("ADAPTER_UNSUPPORTED: composer missing");
    if (composer instanceof HTMLTextAreaElement) composer.value = text;
    else composer.textContent = text;
    composer.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: text }));
  }

  interceptSubmit(callback: SubmitInterceptor): Unsubscribe {
    const composer = first(this.document, COMPOSER_SELECTORS);
    const form = composer?.closest("form");
    if (!composer || !form) {
      this.detach("submit-surface-missing");
      return () => undefined;
    }
    let approvedReplay = false;
    const listener = (event: SubmitEvent) => {
      if (approvedReplay) {
        approvedReplay = false;
        return;
      }
      if (!event.isTrusted) return;
      event.preventDefault();
      void this.readDraft()
        .then((draft) => callback(draft, event))
        .then((decision) => {
          if (decision !== "continue") return;
          approvedReplay = true;
          form.requestSubmit(event.submitter instanceof HTMLElement ? event.submitter : undefined);
        });
    };
    form.addEventListener("submit", listener, { capture: true });
    return () => form.removeEventListener("submit", listener, { capture: true });
  }

  async getStreamingState(): Promise<StreamingState> {
    const streaming = Boolean(first(this.document, STREAMING_SELECTORS));
    return { streaming, stable: !streaming };
  }

  mountPanel(host: HTMLElement): PanelMount {
    const element = this.document.createElement("section");
    element.dataset.tomAssistPanel = "true";
    element.setAttribute("aria-label", "Tom Assist");
    host.append(element);
    return { element, destroy: () => element.remove() };
  }
}
