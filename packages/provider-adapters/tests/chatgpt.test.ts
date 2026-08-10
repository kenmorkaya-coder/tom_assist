import { readFileSync } from "node:fs";
import { webcrypto } from "node:crypto";
import { resolve } from "node:path";
import { JSDOM } from "jsdom";
import { beforeEach, describe, expect, it } from "vitest";
import { CaptureDeduplicator, ChatGptAdapter } from "../src";

const fixtureRoot = resolve(import.meta.dirname, "../../../tests/fixtures/provider-dom");

function adapterFor(name: string, detach: (reason: string) => void = () => undefined) {
  const dom = new JSDOM(readFileSync(resolve(fixtureRoot, name), "utf8"), {
    url: "https://chatgpt.com/c/fixture",
  });
  Object.assign(globalThis, {
    HTMLTextAreaElement: dom.window.HTMLTextAreaElement,
    InputEvent: dom.window.InputEvent,
    MutationObserver: dom.window.MutationObserver,
  });
  return {
    dom,
    adapter: new ChatGptAdapter(dom.window.document, dom.window.location, detach),
  };
}

beforeEach(() => {
  Object.defineProperty(globalThis, "crypto", {
    configurable: true,
    value: globalThis.crypto ?? webcrypto,
  });
});

describe("ChatGPT visible-DOM adapter", () => {
  it("enumerates ordered visible turns and reads/writes the standard composer", async () => {
    const { adapter } = adapterFor("chatgpt-standard.html");
    expect((await adapter.detect()).supported).toBe(true);
    const turns = await adapter.enumerateVisibleTurns();
    expect(turns.map(({ role, ordinal }) => ({ role, ordinal }))).toEqual([
      { role: "user", ordinal: 0 },
      { role: "assistant", ordinal: 1 },
    ]);
    expect(turns[0]?.normalizedText).toBe("Use a local event store.");
    expect(turns[0]?.contentHash).toMatch(/^sha256:[0-9a-f]{64}$/);
    expect(await adapter.readDraft()).toBe("Next step");
    await adapter.writeDraft("Visible approved packet\n\nOriginal draft");
    expect(await adapter.readDraft()).toContain("Original draft");
  });

  it("uses semantic fallbacks and marks streaming assistant capture incomplete", async () => {
    const fallback = adapterFor("chatgpt-contenteditable.html").adapter;
    expect((await fallback.enumerateVisibleTurns()).length).toBe(2);
    expect(await fallback.readDraft()).toBe("Editable draft");
    const streaming = adapterFor("chatgpt-streaming.html").adapter;
    expect(await streaming.getStreamingState()).toEqual({ streaming: true, stable: false });
    expect((await streaming.enumerateVisibleTurns()).at(-1)?.complete).toBe(false);
  });

  it("deduplicates repeated DOM captures by conversation, ordinal, and hash", async () => {
    const turn = (await adapterFor("chatgpt-standard.html").adapter.enumerateVisibleTurns())[0]!;
    const dedup = new CaptureDeduplicator();
    expect(dedup.accept(turn)).toBe(true);
    expect(dedup.accept(turn)).toBe(false);
    expect(dedup.accept({ ...turn, ordinal: 99 })).toBe(true);
  });

  it("detaches cleanly when the authored unknown-DOM fixture loses selectors", async () => {
    const reasons: string[] = [];
    const { adapter } = adapterFor("chatgpt-unknown.html", (reason) => reasons.push(reason));
    const health = await adapter.healthCheck();
    expect(health.supported).toBe(false);
    expect(reasons).toEqual(["composer-selector-missing"]);
    await expect(adapter.readDraft()).rejects.toThrow("ADAPTER_UNSUPPORTED");
  });
});
