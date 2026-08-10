export interface ChunkFrame {
  correlation_id: string;
  seq: number;
  total: number;
  chunk_b64: string;
}

function isChunkFrame(value: unknown): value is ChunkFrame {
  if (!value || typeof value !== "object") return false;
  const row = value as Partial<ChunkFrame>;
  return (
    typeof row.correlation_id === "string" &&
    Number.isInteger(row.seq) &&
    Number.isInteger(row.total) &&
    typeof row.chunk_b64 === "string"
  );
}

function decodeBase64(value: string): Uint8Array {
  const binary = globalThis.atob(value);
  return Uint8Array.from(binary, (character) => character.charCodeAt(0));
}

export class ChunkAssembler {
  private readonly pending = new Map<string, Map<number, Uint8Array>>();

  accept(value: unknown): unknown | undefined {
    if (!isChunkFrame(value)) return value;
    if (value.total < 1 || value.seq < 0 || value.seq >= value.total) {
      throw new Error("VALIDATION_FAILED: invalid chunk bounds");
    }
    const frames = this.pending.get(value.correlation_id) ?? new Map<number, Uint8Array>();
    frames.set(value.seq, decodeBase64(value.chunk_b64));
    this.pending.set(value.correlation_id, frames);
    if (frames.size !== value.total) return undefined;
    const ordered: Uint8Array[] = [];
    for (let index = 0; index < value.total; index += 1) {
      const frame = frames.get(index);
      if (!frame) return undefined;
      ordered.push(frame);
    }
    const length = ordered.reduce((total, bytes) => total + bytes.byteLength, 0);
    const joined = new Uint8Array(length);
    let offset = 0;
    for (const bytes of ordered) {
      joined.set(bytes, offset);
      offset += bytes.byteLength;
    }
    this.pending.delete(value.correlation_id);
    return JSON.parse(new TextDecoder().decode(joined));
  }
}
