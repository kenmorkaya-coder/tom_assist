import type { Envelope } from "./protocol";

export interface PendingTransaction {
  correlationId: string;
  phase: "PREPARE_TURN" | "PENDING_SEND";
  envelope: Envelope;
  heldAt: string;
}

export interface SessionStorage {
  get(key: string): Promise<unknown>;
  set(values: Record<string, unknown>): Promise<void>;
  remove(key: string): Promise<void>;
}

const PREFIX = "held:";

export async function holdTransaction(
  storage: SessionStorage,
  transaction: PendingTransaction,
): Promise<void> {
  await storage.set({ [`${PREFIX}${transaction.correlationId}`]: transaction });
}

export async function releaseTransaction(
  storage: SessionStorage,
  correlationId: string,
): Promise<void> {
  await storage.remove(`${PREFIX}${correlationId}`);
}

export async function restoreTransaction(
  storage: SessionStorage,
  correlationId: string,
): Promise<PendingTransaction | undefined> {
  const value = await storage.get(`${PREFIX}${correlationId}`);
  return value as PendingTransaction | undefined;
}

export const chromeSessionStorage: SessionStorage = {
  async get(key) {
    const result = await chrome.storage.session.get(key);
    return result[key];
  },
  async set(values) {
    await chrome.storage.session.set(values);
  },
  async remove(key) {
    await chrome.storage.session.remove(key);
  },
};
