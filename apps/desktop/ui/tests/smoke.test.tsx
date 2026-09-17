import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/preact";
import { webcrypto } from "node:crypto";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { App } from "../src/App";
import { FakeDesktopBackend } from "../src/fakeBackend";
import { GemmaInspection, NativeMemoryAnswer } from "../src/Chat";

beforeAll(() => {
  Object.defineProperty(globalThis, "crypto", {
    configurable: true,
    value: webcrypto,
  });
});
afterEach(cleanup);

describe("learned document answers", () => {
  it("answers only on an explicit action and retains citations and partial refusals", async () => {
    const backend = new FakeDesktopBackend();
    const project = await backend.seedDemo();
    const chat = vi.spyOn(backend, "chat").mockImplementation(async (_project, _method, payload) =>
      payload.action === "status" ? { ready: true, scope: "Six learned insurance facts." } : {
        status: "partial", answer: "SM must pay premiums. [Clause 24.2, page 57]\nThat information is not present in the available evidence.",
        sources: [{ source_id: "source-1", text: "SM must pay premiums.", provenance: { clause: "24.2", pdf_page: 57 } }],
      });
    render(<NativeMemoryAnswer project={project} draft="Who pays? What is the policy number?" backend={backend} />);
    const button = await screen.findByRole("button", { name: "Answer from learned documents" });
    expect(chat).toHaveBeenCalledTimes(1);
    expect(chat.mock.calls[0]![2]).toEqual({ action: "status" });
    fireEvent.click(button);
    await screen.findByRole("heading", { name: "Partly supported answer" });
    expect(chat.mock.calls[1]![2]).toMatchObject({ action: "answer", explicit_answer: true, project_state_version: project.state_version });
    expect(screen.getByText(/Clause 24.2, page 57/)).toBeTruthy();
    expect(screen.getByText(/That information is not present/)).toBeTruthy();
    expect(screen.getByText("Source: clause 24.2, page 57")).toBeTruthy();
  });

  it("discards an answer after the question or project changes", async () => {
    const backend = new FakeDesktopBackend();
    const project = await backend.seedDemo();
    let finish!: (value: unknown) => void;
    vi.spyOn(backend, "chat").mockImplementation((_project, _method, payload) => payload.action === "status"
      ? Promise.resolve({ ready: true }) : new Promise((resolve) => { finish = resolve; }));
    const view = render(<NativeMemoryAnswer project={project} draft="Old question" backend={backend} />);
    fireEvent.click(await screen.findByRole("button", { name: "Answer from learned documents" }));
    view.rerender(<NativeMemoryAnswer project={{ ...project, id: "another-project" }} draft="New question" backend={backend} />);
    finish({ status: "supported", answer: "Stale source answer", sources: [] });
    await waitFor(() => expect(screen.queryByText("Stale source answer")).toBeNull());
  });
});

describe("explicit Gemma inspection", () => {
  it("shows distinct roles, clickable evidence and uninterpreted matrix details", async () => {
    const backend = new FakeDesktopBackend();
    const project = await backend.seedDemo();
    const text = "Notify the superintendent.";
    const evidence = [{ start: 11, end: 25, quote: "superintendent" }];
    vi.spyOn(backend, "chat").mockResolvedValue({
      stages: [{ stage: "validation", status: "passed", reason: "Semantic review required" }],
      source: { id: "saved", kind: "saved_example", text, full_text: text, start: 0, end: text.length },
      graph: {
        entities: [{ id: "person", name: "superintendent", mentions: evidence }],
        events: [{ id: "e1", action: "notify", modality: "obligation", negated: false,
          roles: { actor: null, object: null, source: null, target: null, recipient: "person", authority: null },
          condition: null, exception: null, evidence }],
        predicates: [], conditions: [], links: [], unresolved: [],
      },
      compiled: { loads: [{ id: "e1", kind: "event", matrix_sha256: "fixture", matrix: Array.from({ length: 32 }, () => Array(32).fill(0)) }] },
      runtime: { interpretation: "Interpretation unavailable", responses: [], state_unchanged: true },
      purity: { live_runtime: { unchanged: true }, ledger: { unchanged: true } },
    });
    const view = render(<GemmaInspection project={project} objects={[]} draft="" backend={backend} />);
    fireEvent.click(screen.getByLabelText("Enable inspection for this project view"));
    fireEvent.change(screen.getByLabelText("Selected adapter"), { target: { value: "v14-4380" } });
    fireEvent.click(screen.getByRole("button", { name: "Inspect saved example" }));
    await screen.findByRole("heading", { name: "Inspection outcomes" });
    expect(screen.getByText("authority").nextElementSibling?.textContent).toBe("not specified");
    fireEvent.click(screen.getByRole("button", { name: "superintendent" }));
    expect(view.container.querySelector("mark")?.textContent).toBe("superintendent");
    expect(screen.getByText("Interpretation unavailable", { selector: "p" })).toBeTruthy();
    expect(screen.getByText("Ordered matrix loads (1)")).toBeTruthy();
  });

  it("makes no request on typing or opt-in, and shows a precise blocked stage", async () => {
    const backend = new FakeDesktopBackend();
    const project = await backend.seedDemo();
    const chat = vi.spyOn(backend, "chat").mockResolvedValue({
      stages: [{ stage: "extraction", status: "blocked", reason: "insufficient memory headroom" }],
      purity: {},
    });
    const view = render(<GemmaInspection project={project} objects={[]} draft="Stop excavation." backend={backend} />);
    expect(chat).not.toHaveBeenCalled();
    fireEvent.click(screen.getByLabelText("Enable inspection for this project view"));
    expect(chat).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Selected adapter"), { target: { value: "v14-4380" } });
    fireEvent.change(screen.getByLabelText("Extraction source"), { target: { value: "gemma" } });
    view.rerender(<GemmaInspection project={project} objects={[]} draft="😀 Stop excavation." backend={backend} />);
    expect(chat).not.toHaveBeenCalled();
    const passage = screen.getByLabelText("Inspection passage") as HTMLTextAreaElement;
    passage.setSelectionRange(3, passage.value.length);
    fireEvent.click(screen.getByRole("button", { name: "Inspect selected passage" }));
    await screen.findByText(/insufficient memory headroom/, { selector: "li" });
    expect(chat).toHaveBeenCalledTimes(1);
    expect(chat.mock.calls[0]![1]).toBe("inspection.gemma");
    expect(chat.mock.calls[0]![2]).toMatchObject({ opt_in: true, explicit_inspect: true, query_stream1: false, source: { start: 2, text: "😀 Stop excavation." } });
  });

  it("discards a late result when the active project changes", async () => {
    const backend = new FakeDesktopBackend();
    const project = await backend.seedDemo();
    let finish!: (value: unknown) => void;
    vi.spyOn(backend, "chat").mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
    const view = render(<GemmaInspection project={project} objects={[]} draft="" backend={backend} />);
    fireEvent.click(screen.getByLabelText("Enable inspection for this project view"));
    fireEvent.change(screen.getByLabelText("Selected adapter"), { target: { value: "v14-4380" } });
    fireEvent.click(screen.getByRole("button", { name: "Inspect saved example" }));
    const next = { ...project, id: "other-project" };
    view.rerender(<GemmaInspection project={next} objects={[]} draft="" backend={backend} />);
    finish({ stages: [{ stage: "runtime", status: "passed", reason: "old project result" }], purity: {} });
    await waitFor(() => expect(screen.queryByText(/old project result/)).toBeNull());
  });
});

describe("desktop project → capture → supersede → audit smoke", () => {
  it("keeps every transition visible and auditable", async () => {
    render(<App backend={new FakeDesktopBackend()} />);
    await screen.findByRole("heading", { name: "Local Release Console" });
    fireEvent.click(screen.getByRole("button", { name: /new project/i }));
    await screen.findByRole("heading", { name: "New Project" });
    fireEvent.click(
      screen.getByRole("button", { name: /quick capture decision/i }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Ledger" }));
    await screen.findByRole("heading", {
      name: "Document user-gated workflow",
    });
    fireEvent.click(
      screen.getByRole("button", { name: /supersede with reason/i }),
    );
    await screen.findByRole("heading", {
      name: "Document user-gated workflow · revised",
    });
    expect(screen.getAllByText("superseded").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Audit" }));
    await waitFor(() =>
      expect(screen.getByText("STATE_SUPERSEDED")).toBeTruthy(),
    );
  });
  it("saves front-row and conflict teaching settings per project", async () => {
    const backend = new FakeDesktopBackend();
    render(<App backend={backend} />);
    await screen.findByRole("heading", { name: "Local Release Console" });
    const first = (await backend.listProjects())[0]!;
    fireEvent.click(screen.getByRole("button", { name: "Settings" }));
    const capacity = (await screen.findByLabelText(
      "Front-row capacity",
    )) as HTMLInputElement;
    expect(capacity.value).toBe("4096");
    fireEvent.input(capacity, { target: { value: "8192" } });
    fireEvent.click(screen.getByLabelText("Teach on dismissed conflict"));
    fireEvent.click(
      screen.getByRole("button", { name: "Save memory settings" }),
    );
    await screen.findByText("Memory settings saved for this project.");
    expect(await backend.memorySettings(first.id)).toEqual({
      front_row_capacity: 8192,
      teach_on_conflict: false,
    });
    fireEvent.click(screen.getByRole("button", { name: /new project/i }));
    await screen.findByRole("heading", { name: "New Project" });
    await waitFor(() =>
      expect(
        (screen.getByLabelText("Front-row capacity") as HTMLInputElement).value,
      ).toBe("4096"),
    );
  });
  it("shows project-local front, long and document shelves without leaking documents", async () => {
    const backend = new FakeDesktopBackend();
    render(<App backend={backend} />);
    await screen.findByRole("heading", { name: "Local Release Console" });
    fireEvent.click(screen.getByRole("button", { name: "Memory" }));
    await screen.findByRole("heading", { name: "Project deed.txt" });
    expect(screen.getByText("3 / 4,096")).toBeTruthy();
    expect(screen.getByText("7 permanent records")).toBeTruthy();
    expect(screen.getByText("1 active documents")).toBeTruthy();
    expect(screen.getByText(/belongs only to the selected project/)).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /new project/i }));
    await screen.findByRole("heading", { name: "New Project" });
    await screen.findByText("No permanent documents in this project.");
    expect(screen.queryByRole("heading", { name: "Project deed.txt" })).toBeNull();
  });
  it("holds recovery import until verification and invalidates changed paths", async () => {
    const backend = new FakeDesktopBackend();
    const verify = vi.spyOn(backend, "verifyArchive");
    const backup = vi.spyOn(backend, "backupProject");
    const restore = vi.spyOn(backend, "importProject");
    render(<App backend={backend} />);
    await screen.findByRole("heading", { name: "Local Release Console" });
    fireEvent.click(screen.getByRole("button", { name: "Settings" }));
    const importButton = () =>
      screen.getByRole("button", {
        name: "Import verified recovery archive",
      }) as HTMLButtonElement;
    expect(importButton().disabled).toBe(true);
    expect(screen.getByText(/unencrypted—not redacted/)).toBeTruthy();
    fireEvent.click(
      screen.getByRole("button", { name: "Verify recovery archive" }),
    );
    await waitFor(() => expect(importButton().disabled).toBe(false));
    fireEvent.input(screen.getByLabelText("Recovery directory"), {
      target: { value: "/tmp/another-archive" },
    });
    expect(importButton().disabled).toBe(true);
    verify.mockRejectedValueOnce(new Error("checksum mismatch"));
    fireEvent.click(
      screen.getByRole("button", { name: "Verify recovery archive" }),
    );
    await screen.findByText(/checksum mismatch/);
    expect(importButton().disabled).toBe(true);
    expect(restore).not.toHaveBeenCalled();
    fireEvent.click(
      screen.getByRole("button", { name: "Create complete project backup" }),
    );
    await screen.findByText(/Verified backup saved:/);
    expect(backup.mock.calls[0]![1]).toMatch(
      /^\/tmp\/another-archive-backup-\d+$/,
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Verify recovery archive" }),
    );
    await waitFor(() => expect(importButton().disabled).toBe(false));
    fireEvent.click(importButton());
    await screen.findByRole("heading", { name: "Imported project" });
    expect(restore).toHaveBeenCalledWith("/tmp/another-archive");
  });
  it("requires a visible preview and an explicit send, then captures only after confirmation", async () => {
    const backend = new FakeDesktopBackend();
    backend.includeMissingSource = false;
    const chat = vi.spyOn(backend, "chat");
    const capture = vi.spyOn(backend, "captureChatState");
    render(<App backend={backend} />);
    await screen.findByRole("heading", { name: "Local Release Console" });
    fireEvent.click(screen.getByRole("button", { name: "Chat" }));
    fireEvent.click(
      await screen.findByRole("button", { name: "New conversation" }),
    );
    fireEvent.input(await screen.findByLabelText("Message"), {
      target: { value: "Check the project constraints." },
    });
    fireEvent.keyDown(screen.getByLabelText("Message"), { key: "Enter" });
    expect(
      chat.mock.calls.filter((c) => c[1] === "conversation.send"),
    ).toHaveLength(0);
    fireEvent.click(screen.getByRole("button", { name: "Preview packet" }));
    await screen.findByRole("heading", {
      name: "Evidence selected for your question",
    });
    expect(screen.getByText("4.2 Release checks")).toBeTruthy();
    expect(screen.getByText("(a) verify the package; and")).toBeTruthy();
    expect(screen.getByText("(b) record the receipt.")).toBeTruthy();
    expect(screen.getByText("2 top-level numbered paragraphs in this selected clause")).toBeTruthy();
    expect(
      screen.getByText(
        "Tom Assist examined the full retained project-document inventory for this question.",
      ),
    ).toBeTruthy();
    expect(
      screen.getByText(/1 contract excerpt is shown; 1 other contract candidate was excluded/),
    ).toBeTruthy();
    expect(screen.getByText("Retained contract source · chunk 4")).toBeTruthy();
    expect(
      screen.getByRole("heading", {
        name: "Prerequisite coverage found in the project documents",
      }),
    ).toBeTruthy();
    expect(screen.getByText(/found 2 authored evidence units/)).toBeTruthy();
    expect(
      screen.getByText(/Every retained passage was consumed in native Tree rank order/),
    ).toBeTruthy();
    expect(screen.getByText(/1466 Tree-ranked passages were examined/)).toBeTruthy();
    expect(screen.getByText(/2 distinct source-located pre-start trigger points/)).toBeTruthy();
    expect(screen.getByText(/Clause addresses:/).closest("p")?.textContent).toContain(
      "4.2, 8.1",
    );
    expect(screen.queryByText(/Not exhaustive:/)).toBeNull();
    expect(
      (screen.getByText("Technical send details").closest("details") as HTMLDetailsElement)
        .open,
    ).toBe(false);
    await screen.findByLabelText("Outgoing provider prompt");
    expect(
      chat.mock.calls.filter((c) => c[1] === "conversation.send"),
    ).toHaveLength(0);
    fireEvent.input(screen.getByLabelText("Message"), {
      target: { value: "Updated draft" },
    });
    expect(screen.queryByRole("button", { name: "Send with Tom" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Preview packet" }));
    fireEvent.click(
      await screen.findByRole("button", { name: "Send with Tom" }),
    );
    await screen.findByText("PASS");
    await screen.findByText("Evaluated response awaiting your acceptance");
    expect(screen.queryByText("Five-dynamics experience committed")).toBeNull();
    fireEvent.click(
      screen.getByRole("button", {
        name: "Accept response and commit experience",
      }),
    );
    await screen.findByText("Five-dynamics experience committed");
    expect(
      chat.mock.calls.filter(
        (c) =>
          c[1] === "conversation.evaluate" && c[2].accept_reviewed === true,
      ),
    ).toHaveLength(1);
    expect(
      chat.mock.calls.filter((c) => c[1] === "conversation.send"),
    ).toHaveLength(1);
    expect(
      chat.mock.calls.find((c) => c[1] === "conversation.send")![2],
    ).toMatchObject({
      explicit_send: true,
      confirmed_prompt_hash: "fixture-hash",
    });
    expect(capture).not.toHaveBeenCalled();
    fireEvent.click(
      screen.getByRole("button", { name: "Review capture / supersession" }),
    );
    expect(capture).not.toHaveBeenCalled();
    fireEvent.input(screen.getByLabelText("Decision text"), {
      target: { value: "User-approved decision" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Confirm decision" }));
    await waitFor(() => expect(capture).toHaveBeenCalledOnce());
    expect(capture.mock.calls[0]![2]).toBe("User-approved decision");
    fireEvent.click(screen.getByRole("button", { name: "Ledger" }));
    await screen.findByRole("heading", { name: "User-approved decision" });
    fireEvent.click(screen.getByRole("button", { name: "Chat" }));
    await screen.findByText("PASS");
    expect(
      chat.mock.calls.filter((c) => c[1] === "conversation.send"),
    ).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: /new project/i }));
    await screen.findByRole("heading", { name: "New Project" });
    expect(screen.queryByText("PASS")).toBeNull();
  });
  it("allows offline preview but disables send when OAuth is disconnected", async () => {
    const backend = new FakeDesktopBackend();
    backend.connected = false;
    const chat = vi.spyOn(backend, "chat");
    render(<App backend={backend} />);
    await screen.findByRole("heading", { name: "Local Release Console" });
    fireEvent.click(screen.getByRole("button", { name: "Chat" }));
    await screen.findByText(/OAuth not connected/);
    fireEvent.click(screen.getByRole("button", { name: "New conversation" }));
    fireEvent.input(await screen.findByLabelText("Message"), {
      target: { value: "Offline draft" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Preview packet" }));
    const send = (await screen.findByRole("button", {
      name: "Send with Tom",
    })) as HTMLButtonElement;
    expect(send.disabled).toBe(true);
    expect(
      chat.mock.calls.filter((c) => c[1] === "conversation.send"),
    ).toHaveLength(0);
    fireEvent.click(screen.getByRole("button", { name: "Connect OAuth" }));
    await screen.findByText(/Tom Assist OAuth connected/);
    expect(send.disabled).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Disconnect OAuth" }));
    await screen.findByText(/OAuth not connected/);
    expect(send.disabled).toBe(true);
  });
  it("keeps the selected project when an earlier project's send finishes", async () => {
    const backend = new FakeDesktopBackend();
    const original = backend.chat.bind(backend);
    let release!: () => void;
    const pending = new Promise<void>((resolve) => {
      release = resolve;
    });
    vi.spyOn(backend, "chat").mockImplementation(
      async (project, method, payload) => {
        if (method === "conversation.send") await pending;
        return original(project, method, payload);
      },
    );
    render(<App backend={backend} />);
    await screen.findByRole("heading", { name: "Local Release Console" });
    fireEvent.click(screen.getByRole("button", { name: "Chat" }));
    fireEvent.click(
      await screen.findByRole("button", { name: "New conversation" }),
    );
    fireEvent.input(await screen.findByLabelText("Message"), {
      target: { value: "Slow reply" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Preview packet" }));
    fireEvent.click(
      await screen.findByRole("button", { name: "Send with Tom" }),
    );
    await screen.findByText(/Working locally or waiting/);
    fireEvent.click(screen.getByRole("button", { name: /new project/i }));
    await screen.findByRole("heading", { name: "New Project" });
    release();
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "New Project" })).toBeTruthy(),
    );
    expect(screen.queryByText("PASS")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Ledger" }));
    expect(screen.queryByText(/Fixture response/)).toBeNull();
  });
  it("requires a reason for explicit chat supersession", async () => {
    const backend = new FakeDesktopBackend();
    const capture = vi.spyOn(backend, "captureChatState");
    render(<App backend={backend} />);
    await screen.findByRole("heading", { name: "Local Release Console" });
    fireEvent.click(
      screen.getByRole("button", { name: "Quick capture decision" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Chat" }));
    fireEvent.click(
      await screen.findByRole("button", { name: "New conversation" }),
    );
    fireEvent.input(await screen.findByLabelText("Message"), {
      target: { value: "Review this decision" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Preview packet" }));
    fireEvent.click(
      await screen.findByRole("button", { name: "Send with Tom" }),
    );
    fireEvent.click(
      await screen.findByRole("button", {
        name: "Review capture / supersession",
      }),
    );
    const select = screen.getByLabelText(
      "Supersede decision",
    ) as HTMLSelectElement;
    fireEvent.change(select, { target: { value: select.options[1]!.value } });
    expect(
      (
        screen.getByRole("button", {
          name: "Confirm decision",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
    fireEvent.input(screen.getByLabelText("Supersession reason"), {
      target: { value: "Owner changed the requirement" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Confirm decision" }));
    await waitFor(() => expect(capture).toHaveBeenCalledOnce());
    expect(capture.mock.calls[0]![4]).toBe("Owner changed the requirement");
  });
});

it("opens exact RGM citations and explicitly saves a reviewed ToM relationship", async () => {
  const backend = new FakeDesktopBackend();
  const project = await backend.seedDemo();
  const chat = vi.spyOn(backend, "chat").mockImplementation(async (_project, _method, payload) =>
    payload.action === "status" ? { ready: true, engine: "rgm", scope: "Experimental document answers." }
      : payload.action === "learn_situation" ? { duplicate: false, write_count: 381 } : {
      status: "supported", answer: "Orchid must notify Rowan.",
      sources: [{ source_id: "corpus/chunk_1", text: "🌳 Orchid must notify Rowan. Next clause.",
        provenance: { display_name: "Maintenance agreement", doc_id: "document-a", chunk_id: "chunk_1", start: 100, end: 138,
          answer_start: 102, answer_end: 127 } }],
    });
  const view = render(<NativeMemoryAnswer project={project} draft="Who must notify Rowan?" backend={backend} />);
  fireEvent.click(await screen.findByRole("button", { name: "Answer from project documents" }));
  await screen.findByRole("heading", { name: "Supported answer" });
  const citation = screen.getByText("Source: Maintenance agreement · chunk_1");
  fireEvent.click(citation);
  expect(citation.closest("details")?.open).toBe(true);
  expect(view.container.querySelector("mark")?.textContent).toBe("Orchid must notify Rowan.");
  expect(chat.mock.calls[1]![2]).toMatchObject({ explicit_answer: true, question: "Who must notify Rowan?" });
  expect(view.container.textContent).not.toContain("page undefined");
  fireEvent.click(screen.getByText("Save a reviewed relationship in ToM"));
  fireEvent.input(screen.getByLabelText("Party that failed to show compliance"), { target: { value: "Orchid" } });
  fireEvent.input(screen.getByLabelText("Party that may buy replacement cover"), { target: { value: "Rowan" } });
  fireEvent.click(screen.getByRole("button", { name: "Save reviewed relationship" }));
  await screen.findByText("Saved in ToM across 381 memory locations.");
  expect(chat.mock.calls[2]![2]).toMatchObject({ action: "learn_situation", explicit_user_action: true,
    project_state_version: project.state_version, document_id: "document-a", chunk_index: 1,
    roles: { failure_party: "Orchid", cover_payer: "Rowan" } });
});

it("records explicit source authority when current evidence conflicts", async () => {
  const backend = new FakeDesktopBackend();
  const project = await backend.seedDemo();
  const chat = vi.spyOn(backend, "chat").mockImplementation(async (_project, _method, payload) => {
    if (payload.action === "status") return { ready: true, engine: "rgm+tom", scope: "Project documents." };
    if (payload.action === "resolve_source_authority") return { status: "recorded", link_count: 1 };
    return {
      status: "not_supported", answer: "Conflicting evidence needs source-authority review.", sources: [],
      authority_review: { status: "unresolved", can_record: true, relation_kind: "reimbursement",
        conflict_sources: [{ source_id: "SRC-new", text: "Orchid must not reimburse Rowan.",
          reason: "source explicitly negates reimbursement", active: true,
          provenance: { display_name: "Amendment", doc_id: "document-new", chunk_index: 0, start: 0, end: 38 } }],
        current_sources: [{ source_id: "SRC-old", text: "Orchid must reimburse Rowan.", active: true,
          provenance: { display_name: "Original agreement", doc_id: "document-old", chunk_index: 2, start: 50, end: 80 } }],
      },
    };
  });
  render(<NativeMemoryAnswer project={project} draft="Does Orchid reimburse Rowan?" backend={backend} />);
  fireEvent.click(await screen.findByRole("button", { name: "Answer from project documents" }));
  await screen.findByRole("heading", { name: "Not supported" });
  fireEvent.click(screen.getByLabelText("Replace Original agreement passage 3"));
  fireEvent.input(screen.getByLabelText("Source authority effective time"), {
    target: { value: "2026-09-17T00:00:00+10:00" },
  });
  fireEvent.input(screen.getByLabelText("Source authority reason"), {
    target: { value: "Executed amendment replaces the original clause" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Record source supersession" }));
  await screen.findByText("Source authority recorded. Ask the question again to apply it.");
  expect(chat.mock.calls[2]![2]).toMatchObject({ action: "resolve_source_authority",
    explicit_user_action: true, relation_kind: "reimbursement", superseding_source_id: "SRC-new",
    superseded_source_ids: ["SRC-old"], effective_at: "2026-09-17T00:00:00+10:00",
    reason: "Executed amendment replaces the original clause" });
});

it("imports a local document only after an explicit action", async () => {
  const { Memory } = await import("../src/Memory");
  const backend = new FakeDesktopBackend();
  const project = await backend.seedDemo();
  vi.spyOn(backend, "diagnostics").mockResolvedValue({ memory: {} });
  vi.spyOn(backend, "documents").mockResolvedValue([]);
  const chat = vi.spyOn(backend, "chat").mockImplementation(async (_id, method) =>
    method === "document.ingest" ? { display_name: "Agreement.pdf", chunk_count: 12, duplicate: false }
      : { ready: false, engine: "rgm" });
  render(<Memory projectId={project.id} backend={backend} />);
  const path = await screen.findByLabelText("Document file path");
  expect(chat.mock.calls.every((c) => c[1] !== "document.ingest")).toBe(true);
  fireEvent.input(path, { target: { value: "/Volumes/Passport/Agreement.pdf" } });
  fireEvent.click(screen.getByRole("button", { name: "Import document" }));
  await screen.findByText("Imported: Agreement.pdf · 12 passages");
  expect(chat).toHaveBeenCalledWith(project.id, "document.ingest", {
    explicit_user_action: true, source_path: "/Volumes/Passport/Agreement.pdf",
  });
});
