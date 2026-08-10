import { fireEvent, render, screen, waitFor } from "@testing-library/preact";
import { webcrypto } from "node:crypto";
import { beforeAll, describe, expect, it } from "vitest";
import { App } from "../src/App";
import { FakeDesktopBackend } from "../src/fakeBackend";

beforeAll(() => {
  Object.defineProperty(globalThis, "crypto", { configurable: true, value: webcrypto });
});

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
});
