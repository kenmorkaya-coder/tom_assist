import { describe, expect, it } from "vitest";
import { ChunkAssembler } from "../src/chunks";
import { isTrustedSender, validateEnvelope } from "../src/protocol";
import {
  holdTransaction,
  restoreTransaction,
  type SessionStorage,
} from "../src/session";

const envelope = {
  protocol: "tom-assist/1.0",
  request_id: "00000000-0000-4000-8000-000000000001",
  idempotency_key: "00000000-0000-4000-8000-000000000002",
  method: "turn.prepare",
  actor: { type: "extension", instance_id: "00000000-0000-4000-8000-000000000003" },
  project_id: "00000000-0000-4000-8000-000000000004",
  base_state_version: 0,
  payload: {},
  sent_at: "2026-08-10T00:00:00Z",
};

describe("native boundary", () => {
  it("validates the protocol schema and handshake version", () => {
    expect(validateEnvelope(envelope).request_id).toBe("00000000-0000-4000-8000-000000000001");
    expect(() => validateEnvelope({ ...envelope, protocol: "tom-assist/999" })).toThrow(
      "PROTOCOL_MISMATCH",
    );
    expect(() => validateEnvelope({ ...envelope, request_id: undefined })).toThrow(
      "VALIDATION_FAILED",
    );
  });

  it("rejects forged runtime senders", () => {
    expect(isTrustedSender("pinned-extension", "pinned-extension")).toBe(true);
    expect(isTrustedSender("page-controlled", "pinned-extension")).toBe(false);
    expect(isTrustedSender(undefined, "pinned-extension")).toBe(false);
  });

  it("reassembles out-of-order chunk frames byte-exactly", () => {
    const value = { payload: "λ".repeat(500_000), nested: { ok: true } };
    const bytes = new TextEncoder().encode(JSON.stringify(value));
    const midpoint = Math.floor(bytes.length / 2);
    const encode = (part: Uint8Array) => {
      let binary = "";
      for (const byte of part) binary += String.fromCharCode(byte);
      return btoa(binary);
    };
    const assembler = new ChunkAssembler();
    expect(
      assembler.accept({
        correlation_id: "large",
        seq: 1,
        total: 2,
        chunk_b64: encode(bytes.slice(midpoint)),
      }),
    ).toBeUndefined();
    expect(
      assembler.accept({
        correlation_id: "large",
        seq: 0,
        total: 2,
        chunk_b64: encode(bytes.slice(0, midpoint)),
      }),
    ).toEqual(value);
  });

  it("restores held PREPARE_TURN state after a worker wake", async () => {
    const values = new Map<string, unknown>();
    const storage: SessionStorage = {
      async get(key) { return values.get(key); },
      async set(rows) { for (const [key, value] of Object.entries(rows)) values.set(key, value); },
      async remove(key) { values.delete(key); },
    };
    await holdTransaction(storage, {
      correlationId: "00000000-0000-4000-8000-000000000001",
      phase: "PREPARE_TURN",
      envelope,
      heldAt: "2026-08-10T00:00:00Z",
    });
    expect((await restoreTransaction(storage, "00000000-0000-4000-8000-000000000001"))?.envelope).toEqual(envelope);
  });
});
