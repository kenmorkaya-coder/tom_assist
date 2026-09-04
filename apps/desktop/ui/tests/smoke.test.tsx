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

beforeAll(() => {
  Object.defineProperty(globalThis, "crypto", {
    configurable: true,
    value: webcrypto,
  });
});
afterEach(cleanup);

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
    expect(screen.getByText("2 requirements in this selected clause")).toBeTruthy();
    expect(
      screen.getByText(
        "This is a retrieved evidence subset, not a complete requirements inventory.",
      ),
    ).toBeTruthy();
    expect(
      screen.getByText(/1 contract excerpt is shown; 1 other contract candidate was excluded/),
    ).toBeTruthy();
    expect(screen.getByText("Retained contract source · chunk 4")).toBeTruthy();
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
    await screen.findByText("Five-dynamics experience committed");
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
