import Ajv2020 from "ajv/dist/2020";
import coreMethodsSchema from "../../../crates/protocol/schemas/core-methods.schema.json";
import envelopeSchema from "../../../crates/protocol/schemas/envelope.schema.json";

export const PROTOCOL_VERSION = "tom-assist/1.0";
export const NATIVE_HOST_NAME = "tom.assist.native";

export interface Envelope {
  protocol: string;
  request_id: string;
  idempotency_key: string;
  method: string;
  actor: { type: string; instance_id: string };
  project_id?: string;
  base_state_version?: number;
  payload: unknown;
  sent_at: string;
}

const ajv = new Ajv2020({ allErrors: true, strict: false });
ajv.addFormat("uuid", /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
ajv.addFormat("date-time", (value: string) => !Number.isNaN(Date.parse(value)));
ajv.addSchema(coreMethodsSchema);
const validate = ajv.compile(envelopeSchema);

export function validateEnvelope(value: unknown): Envelope {
  if (
    value &&
    typeof value === "object" &&
    "protocol" in value &&
    (value as { protocol?: unknown }).protocol !== PROTOCOL_VERSION
  ) {
    throw new Error(`PROTOCOL_MISMATCH: ${(value as { protocol?: unknown }).protocol}`);
  }
  if (!validate(value)) {
    throw new Error(`VALIDATION_FAILED: ${ajv.errorsText(validate.errors)}`);
  }
  const envelope = value as unknown as Envelope;
  return envelope;
}

export function isTrustedSender(senderId: string | undefined, runtimeId: string): boolean {
  return Boolean(senderId) && senderId === runtimeId;
}
