import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { webcrypto } from "node:crypto";
import { JSDOM } from "jsdom";
import { beforeAll, describe, expect, it } from "vitest";
import { ChatGptAdapter, type ProviderTurn } from "@tom-assist/provider-adapters";
import { PromptGateController, type ExtensionService, type PacketPreview } from "../src/gate";

class FixtureService implements ExtensionService {
  prepared = 0; sent = 0; evaluated = 0; captured = 0; unavailable = false;
  async prepare(): Promise<PacketPreview> { this.prepared += 1; if (this.unavailable) throw new Error("offline"); return { packetText: "[TOM_ASSIST_STATE v1]\nHELD_DECISIONS\n- Ship fixture flow\n[/TOM_ASSIST_STATE]", packetDigest: "sha256:packet", includedCategories: ["HELD_DECISIONS"], warnings: ["fixture warning"], excludedItems: ["superseded-path"] }; }
  async markSent(): Promise<void> { this.sent += 1; }
  async evaluate(): Promise<any> { this.evaluated += 1; return { result: "REVIEW", count: 1, severity: "warning" }; }
  async capture(): Promise<void> { this.captured += 1; }
}

beforeAll(() => { Object.defineProperty(globalThis, "crypto", { configurable: true, value: webcrypto }); });

function fixture() {
  const html = readFileSync(resolve(process.cwd(), "../../tests/fixtures/provider-dom/chatgpt-standard.html"), "utf8");
  const dom = new JSDOM(html, { url: "https://chatgpt.com/c/fixture" });
  Object.assign(globalThis, { HTMLTextAreaElement: dom.window.HTMLTextAreaElement, InputEvent: dom.window.InputEvent, MutationObserver: dom.window.MutationObserver });
  return dom;
}

describe("fixture prompt-gate e2e", () => {
  it("pauses, previews, approves, visibly inserts, and captures a response", async () => {
    const dom = fixture(); const service = new FixtureService(); const adapter = new ChatGptAdapter(dom.window.document, dom.window.location); const gate = new PromptGateController(adapter, service);
    gate.attachProject("demo-project", "Demo project");
    const decision = gate.beginUserSubmission("Please continue");
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(gate.snapshot()).toMatchObject({ phase: "preview", preview: { includedCategories: ["HELD_DECISIONS"], excludedItems: ["superseded-path"] } });
    await gate.sendWithTom();
    expect(await decision).toBe("continue");
    expect((dom.window.document.querySelector('[data-testid="prompt-textarea"]') as HTMLTextAreaElement).value).toContain("[TOM_ASSIST_STATE v1]");
    const response: ProviderTurn = { provider: "chatgpt", conversationKey: "/c/fixture", role: "assistant", ordinal: 3, normalizedText: "Fixture response", contentHash: "sha256:response", complete: true };
    await gate.captureResponse(response);
    expect({ prepared: service.prepared, sent: service.sent, evaluated: service.evaluated, badge: gate.snapshot().badge }).toEqual({ prepared: 1, sent: 1, evaluated: 1, badge: { result: "REVIEW", count: 1, severity: "warning" } });
  });

  it("requires an explicit user action before fail-open", async () => {
    const dom = fixture(); const service = new FixtureService(); service.unavailable = true; const gate = new PromptGateController(new ChatGptAdapter(dom.window.document, dom.window.location), service); gate.attachProject("demo-project", "Demo");
    let settled = false; const decision = gate.beginUserSubmission("draft").then((value) => { settled = true; return value; });
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(gate.snapshot().phase).toBe("unavailable"); expect(settled).toBe(false);
    gate.sendOnceWithoutTom(); expect(await decision).toBe("continue"); expect(gate.snapshot().warning).toContain("explicit user confirmation");
  });
});
