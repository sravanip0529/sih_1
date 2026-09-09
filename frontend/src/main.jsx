import React from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

function Dashboard() {
  return (
    <main className="shell">
      <header>
        <p className="eyebrow">PS26227</p>
        <h1>Satellite analysis workspace</h1>
        <p className="status">Foundation ready. Retrieval and temporal analysis arrive in later phases.</p>
      </header>
      <section className="workspace" aria-label="Analysis workspace">
        <aside>
          <label htmlFor="query">Search imagery</label>
          <input id="query" placeholder="Find urban expansion near a river" />
          <button type="button">Search</button>
        </aside>
        <div className="map-placeholder" role="img" aria-label="Map view placeholder">
          Map view
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <Dashboard />
  </React.StrictMode>,
);
