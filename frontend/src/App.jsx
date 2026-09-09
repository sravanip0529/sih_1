import { useMemo, useState } from "react";

const DEFAULT_QUERY = "Find regions with strong vegetation-related spectral change";
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: 4 });
}

function App() {
  const [query, setQuery] = useState(DEFAULT_QUERY);
  const [topK, setTopK] = useState(5);
  const [includeInterpretation, setIncludeInterpretation] = useState(true);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [statusText, setStatusText] = useState("Enter a query to search detected change regions.");

  const resultCountLabel = useMemo(() => `${results.length} result${results.length === 1 ? "" : "s"}`, [results.length]);

  const search = async () => {
    const trimmed = query.trim();
    if (!trimmed) {
      setError("Please enter a search query.");
      setStatusText("Validation error.");
      setResults([]);
      return;
    }

    const parsedTopK = Number(topK);
    if (!Number.isInteger(parsedTopK) || parsedTopK < 1 || parsedTopK > 20) {
      setError("Top-k must be an integer between 1 and 20.");
      setStatusText("Validation error.");
      setResults([]);
      return;
    }

    setLoading(true);
    setError("");
    setStatusText("Searching change regions...");

    try {
      const response = await fetch(`${API_BASE}/api/retrieval/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmed, top_k: parsedTopK, include_interpretation: includeInterpretation }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({ detail: "Unable to complete the retrieval request." }));
        throw new Error(payload.detail || "Unable to complete the retrieval request.");
      }

      const payload = await response.json();
      setResults(payload.results || []);
      setStatusText(payload.result_count === 0 ? "No matching regions were returned for this query." : `${payload.result_count} matching region${payload.result_count === 1 ? "" : "s"} returned.`);
    } catch (fetchError) {
      setResults([]);
      setStatusText("Backend request failed.");
      setError(fetchError.message || "Unable to complete the retrieval request.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="shell">
      <header className="page-header">
        <div>
          <p className="eyebrow">PS26227</p>
          <h1>Semantic retrieval and change-region analysis</h1>
        </div>
        <div className="status-pill">Scientific retrieval interface</div>
      </header>

      <section className="controls panel">
        <label className="field">
          <span>Query</span>
          <textarea
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            rows={4}
            placeholder="Find regions with strong vegetation-related spectral change"
          />
        </label>

        <div className="toolbar">
          <label className="field compact">
            <span>Top-k</span>
            <input
              type="number"
              min="1"
              max="20"
              value={topK}
              onChange={(event) => setTopK(event.target.value)}
            />
          </label>

          <label className="toggle">
            <input type="checkbox" checked={includeInterpretation} onChange={(event) => setIncludeInterpretation(event.target.checked)} />
            <span>Include interpretation</span>
          </label>

          <button type="button" onClick={search} disabled={loading}> {loading ? "Searching..." : "Search"}</button>
        </div>
      </section>

      <section className="search-status panel">
        <strong>{statusText}</strong>
        {resultCountLabel ? <span>{resultCountLabel}</span> : null}
      </section>

      {error ? <div className="error-banner">{error}</div> : null}

      <section className="layout">
        <div className="results-column">
          {results.length === 0 && !loading ? (
            <div className="empty-state panel">Enter a query to search the validated retrieval index.</div>
          ) : null}

          {results.map((result) => (
            <article key={`${result.region_id}-${result.rank}`} className="panel result-card">
              <div className="result-header">
                <div>
                  <span className="small-label">Result #{result.rank}</span>
                  <h3>{result.region_id}</h3>
                </div>
                <div className="score-box">
                  <span>Semantic retrieval similarity</span>
                  <strong>{Number(result.retrieval_score).toFixed(6)}</strong>
                </div>
              </div>

              <dl className="metadata-grid">
                <div><dt>Area</dt><dd>{formatNumber(result.area_m2)} m²</dd></div>
                <div><dt>Pixels</dt><dd>{formatNumber(result.pixel_count)}</dd></div>
                <div><dt>Reference</dt><dd>{result.reference_date || "—"}</dd></div>
                <div><dt>Moving</dt><dd>{result.moving_date || "—"}</dd></div>
              </dl>

              {result.semantic_description ? (
                <div className="info-block">
                  <h4>Region description</h4>
                  <p>{result.semantic_description}</p>
                </div>
              ) : null}

              {result.evidence_summary ? (
                <div className="info-block">
                  <h4>Evidence summary</h4>
                  <p>{result.evidence_summary}</p>
                </div>
              ) : null}

              {result.mean_change_magnitude !== null || result.median_change_magnitude !== null || result.max_change_magnitude !== null ? (
                <div className="info-block">
                  <h4>Change evidence</h4>
                  <ul className="metrics">
                    <li><span>Mean magnitude</span><strong>{formatNumber(result.mean_change_magnitude)}</strong></li>
                    <li><span>Median magnitude</span><strong>{formatNumber(result.median_change_magnitude)}</strong></li>
                    <li><span>Max magnitude</span><strong>{formatNumber(result.max_change_magnitude)}</strong></li>
                  </ul>
                </div>
              ) : null}

              {result.spectral_summary ? (
                <div className="info-block">
                  <h4>Spectral summary</h4>
                  {typeof result.spectral_summary === "string" ? <p>{result.spectral_summary}</p> : (
                    <pre>{JSON.stringify(result.spectral_summary, null, 2)}</pre>
                  )}
                </div>
              ) : null}

              {result.scientific_interpretation ? (
                <div className="info-block caution">
                  <h4>Cautious interpretation</h4>
                  <p>{result.scientific_interpretation}</p>
                </div>
              ) : null}

              {result.limitations && result.limitations.length > 0 ? (
                <div className="info-block warning">
                  <h4>Scientific limitations</h4>
                  <ul>
                    {result.limitations.map((item) => <li key={item}>{item}</li>)}
                  </ul>
                </div>
              ) : null}
            </article>
          ))}
        </div>

        <aside className="details-column panel">
          <h3>Scientific context</h3>
          <div className="context-box">
            <p>Semantic retrieval similarity is a ranked similarity measure. It is not a probability.</p>
            <p>Detected spectral patterns are evidence-based and must not be treated as confirmed land-cover classification.</p>
          </div>
          <div className="context-box">
            <h4>Provenance</h4>
            <ul>
              <li>Phase 9: region metadata</li>
              <li>Phase 10: embedding collection</li>
              <li>Phase 11: semantic retrieval</li>
              <li>Phase 12: evidence interpretation</li>
              <li>Phase 13: backend API exposure</li>
            </ul>
          </div>
        </aside>
      </section>
    </main>
  );
}

export default App;
