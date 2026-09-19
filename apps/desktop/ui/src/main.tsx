import { render } from "preact";
import { App } from "./App";
import "./styles.css";

async function start() {
  const localPreview = ["127.0.0.1", "localhost"].includes(window.location.hostname) &&
    new URLSearchParams(window.location.search).has("design-preview");
  if (localPreview) {
    const { FakeDesktopBackend } = await import("./fakeBackend");
    const backend = new FakeDesktopBackend();
    backend.nativeAnswerPreview = true;
    render(<App backend={backend} />, document.getElementById("app")!);
    return;
  }
  render(<App />, document.getElementById("app")!);
}

void start();
