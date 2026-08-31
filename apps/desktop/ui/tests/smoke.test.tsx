import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/preact";
import { webcrypto } from "node:crypto";
import { afterEach, beforeAll, describe, expect, it } from "vitest";
import { App } from "../src/App";
import { FakeDesktopBackend } from "../src/fakeBackend";

beforeAll(() => {
  Object.defineProperty(globalThis, "crypto", { configurable: true, value: webcrypto });
});
afterEach(cleanup);

describe("desktop project → capture → supersede → audit smoke", () => {
  it("keeps every transition visible and auditable", async () => {
    render(<App backend={new FakeDesktopBackend()}/>);
    await screen.findByRole("heading", { name: "Local Release Console" });
    fireEvent.click(screen.getByRole("button", { name: /new project/i }));
    await screen.findByRole("heading", { name: "New Project" });
    fireEvent.click(screen.getByRole("button", { name: /quick capture decision/i }));
    fireEvent.click(screen.getByRole("button", { name: "Ledger" }));
    await screen.findByRole("heading", { name: "Document user-gated workflow" });
    fireEvent.click(screen.getByRole("button", { name: /supersede with reason/i }));
    await screen.findByRole("heading", { name: "Document user-gated workflow · revised" });
    expect(screen.getAllByText("superseded").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Audit" }));
    await waitFor(() => expect(screen.getByText("STATE_SUPERSEDED")).toBeTruthy());
  });
  it("saves front-row and conflict teaching settings per project", async () => {
    const backend = new FakeDesktopBackend();
    render(<App backend={backend}/>);
    await screen.findByRole("heading", { name: "Local Release Console" });
    const first = (await backend.listProjects())[0]!;
    fireEvent.click(screen.getByRole("button", { name: "Settings" }));
    const capacity = await screen.findByLabelText("Front-row capacity") as HTMLInputElement;
    expect(capacity.value).toBe("4096");
    fireEvent.input(capacity, { target: { value: "8192" } });
    fireEvent.click(screen.getByLabelText("Teach on dismissed conflict"));
    fireEvent.click(screen.getByRole("button", { name: "Save memory settings" }));
    await screen.findByText("Memory settings saved for this project.");
    expect(await backend.memorySettings(first.id)).toEqual({ front_row_capacity: 8192, teach_on_conflict: false });
    fireEvent.click(screen.getByRole("button", { name: /new project/i }));
    await screen.findByRole("heading", { name: "New Project" });
    await waitFor(() => expect((screen.getByLabelText("Front-row capacity") as HTMLInputElement).value).toBe("4096"));
  });
});
