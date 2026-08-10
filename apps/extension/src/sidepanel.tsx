import { render } from "preact";
import "./styles.css";

function App() {
  return (
    <section class="shell">
      <p class="eyebrow">TOM ASSIST</p>
      <h1>Local service boundary ready</h1>
      <p>Attach a project to begin a snapshot-bound turn.</p>
      <span class="status">Awaiting project</span>
    </section>
  );
}

render(<App />, document.getElementById("app")!);
