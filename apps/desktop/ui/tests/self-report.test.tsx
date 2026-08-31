import { cleanup, fireEvent, render, screen } from "@testing-library/preact";
import { afterEach, expect, it, vi } from "vitest";
import { SelfReport, type SelfReportRecord } from "../src/SelfReport";
afterEach(cleanup);

it("has no action when disabled and never sends during render or preview", () => {
  const act = vi.fn();
  const props = { exchangeId: "e", busy: false, act };
  const view = render(<SelfReport {...props} enabled={false} />);
  expect(screen.queryByRole("button")).toBeNull();
  view.rerender(<SelfReport {...props} enabled={true} />);
  expect(act).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText("Preview self-report request"));
  expect(act).toHaveBeenCalledExactlyOnceWith("conversation.self_report.prepare", { exchange_id: "e" });
  const report: SelfReportRecord = { status: "prepared", prompt: "exact visible request", prompt_hash: "h", candidates: [], labels: {}, metrics: {}, precision: { value: null, accurate: 0, false_positive: 0, reviewed: 0, emitted: 0, unreviewed: 0 } };
  view.rerender(<SelfReport {...props} enabled={true} report={report} />);
  expect(screen.getByText("exact visible request")).toBeTruthy();
  expect(act).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByText("Send one self-report request"));
  expect(act).toHaveBeenLastCalledWith("conversation.self_report.send", { exchange_id: "e", confirmed_prompt_hash: "h", explicit_send: true });
  view.rerender(<SelfReport {...props} enabled={true} report={{ ...report, status: "sending" }} />);
  expect(screen.queryByText("Send one self-report request")).toBeNull();
});

it("labels measure proposals and never claim an authoritative capture", () => {
  const act = vi.fn();
  const report: SelfReportRecord = { status: "complete", prompt: "request", prompt_hash: "h", candidates: [{ candidate_id: "c", operation: "CREATE", object: { type: "CONSTRAINT", canonical_text: "Keep data local" } }], labels: {}, metrics: { emitted: 1 }, precision: { value: null, accurate: 0, false_positive: 0, reviewed: 0, emitted: 1, unreviewed: 1 } };
  render(<SelfReport enabled={false} report={report} exchangeId="e" busy={false} act={act} />);
  expect(screen.getByText(/not measured/)).toBeTruthy();
  fireEvent.click(screen.getByText("Mark accurate proposal"));
  expect(act).toHaveBeenCalledExactlyOnceWith("conversation.self_report.label", { exchange_id: "e", candidate_id: "c", label: "accurate", confirmed: true });
});
