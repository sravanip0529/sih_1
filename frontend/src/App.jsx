import { useEffect, useMemo, useState } from "react";

const DEFAULT_QUERY = "Find regions with strong vegetation-related spectral change";
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const DEFAULT_LIMITATIONS = [
  "Semantic retrieval is not ground-truth classification.",
  "Spectral change does not automatically prove a real-world event.",
  "Similarity scores are not probabilities.",
  "No external validation dataset has been used.",
];

function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: 4 });
}

function Metric({ label, value, suffix = "" }) {
  return <div className="metric"><span>{label}</span><strong>{value === undefined ? "—" : `${formatNumber(value)}${suffix}`}</strong></div>;
}

function GeometryView({ geojson, selectedId, resultIds }) {
  const features = geojson?.features || [];
  const polygons = features.flatMap((feature) => {
    const geometry = feature.geometry || {};
    const rings = geometry.type === "Polygon" ? geometry.coordinates : geometry.type === "MultiPolygon" ? geometry.coordinates.flat() : [];
    return rings.slice(0, 1).map((ring) => ({ ring, id: String(feature.properties?.region_id || "") }));
  });
  const points = polygons.flatMap(({ ring }) => ring);
  if (!points.length) return <div className="map-empty">Phase 9 region geometry is not available in the local artifact store.</div>;
  const xs = points.map(([x]) => x); const ys = points.map(([, y]) => y);
  const minX = Math.min(...xs); const maxX = Math.max(...xs); const minY = Math.min(...ys); const maxY = Math.max(...ys);
  const width = Math.max(maxX - minX, 1); const height = Math.max(maxY - minY, 1);
  const project = ([x, y]) => `${12 + ((x - minX) / width) * 376},${188 - ((y - minY) / height) * 176}`;
  return (
    <svg className="geometry" viewBox="0 0 400 200" role="img" aria-label="Offline view of Phase 9 region geometry">
      <rect x="0" y="0" width="400" height="200" rx="8" fill="#e8efe9" />
      {polygons.map(({ ring, id }) => <polygon key={id} points={ring.map(project).join(" ")} className={`${id === selectedId ? "geometry-selected" : ""} ${resultIds.includes(id) ? "geometry-result" : ""}`} />)}
    </svg>
  );
}

function EvidenceBlock({ title, children, className = "" }) {
  return <section className={`evidence-block ${className}`}><h4>{title}</h4>{children}</section>;
}

function App() {
  const [query, setQuery] = useState(DEFAULT_QUERY);
  const [topK, setTopK] = useState(5);
  const [includeInterpretation, setIncludeInterpretation] = useState(true);
  const [results, setResults] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [geojson, setGeojson] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [geometryError, setGeometryError] = useState("");
  const [statusText, setStatusText] = useState("Ready for a local retrieval query.");

  useEffect(() => {
    fetch(`${API_BASE}/api/retrieval/regions`)
      .then((response) => response.ok ? response.json() : Promise.reject(new Error("Phase 9 region geometry is unavailable.")))
      .then(setGeojson)
      .catch((fetchError) => setGeometryError(fetchError.message));
  }, []);

  const selected = useMemo(() => results.find((result) => result.region_id === selectedId) || results[0] || null, [results, selectedId]);
  const resultIds = useMemo(() => results.map((result) => result.region_id), [results]);

  const search = async () => {
    const trimmed = query.trim(); const parsedTopK = Number(topK);
    if (!trimmed) { setError("Please enter a search query."); setStatusText("Validation error."); return; }
    if (!Number.isInteger(parsedTopK) || parsedTopK < 1 || parsedTopK > 20) { setError("Top-k must be an integer between 1 and 20."); setStatusText("Validation error."); return; }
    setLoading(true); setError(""); setSelectedId(""); setStatusText("Searching satellite change regions...");
    try {
      const response = await fetch(`${API_BASE}/api/retrieval/search`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmed, top_k: parsedTopK, include_interpretation: includeInterpretation }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || !Array.isArray(payload.results)) throw new Error(payload.detail || "The retrieval service returned an invalid response.");
      setResults(payload.results); setStatusText(payload.results.length ? `${payload.results.length} matching region${payload.results.length === 1 ? "" : "s"} returned.` : "No matching regions were returned for this query.");
    } catch (fetchError) {
      setResults([]); setStatusText("Retrieval service unavailable."); setError(fetchError.message || "Unable to connect to the local retrieval service.");
    } finally { setLoading(false); }
  };

  return (
    <main className="shell">
      <header className="page-header">
        <div><p className="eyebrow">PS26227 / PHASE 14</p><h1>Semantic retrieval and multi-temporal change analysis</h1><p className="lede">Search detected satellite-image change regions using natural-language queries and inspect the underlying spectral evidence.</p></div>
        <div className="status-pill">Local scientific interface</div>
      </header>

      <section className="controls panel">
        <label className="field"><span>Natural-language query</span><textarea value={query} onChange={(event) => setQuery(event.target.value)} rows={3} placeholder="Describe the type of spectral change you want to explore..." /></label>
        <div className="toolbar">
          <label className="field compact"><span>Top-k results</span><input type="number" min="1" max="20" value={topK} onChange={(event) => setTopK(event.target.value)} /></label>
          <label className="toggle"><input type="checkbox" checked={includeInterpretation} onChange={(event) => setIncludeInterpretation(event.target.checked)} /><span>Include scientific interpretation</span></label>
          <button type="button" onClick={search} disabled={loading}>{loading ? "Searching..." : "Search change regions"}</button>
        </div>
      </section>

      <section className="search-status panel"><strong>{statusText}</strong><span>{results.length ? `${results.length} result${results.length === 1 ? "" : "s"}` : "No results loaded"}</span></section>
      {error ? <div className="error-banner">{error}</div> : null}

      <section className="layout">
        <div className="results-column">
          <div className="section-heading"><div><span className="eyebrow">Ranked retrieval</span><h2>Regions returned by Phase 13</h2></div><span className="muted">Select a result to inspect evidence</span></div>
          {!results.length && !loading ? <div className="empty-state panel">Enter a query to search the validated local retrieval index.</div> : null}
          {results.map((result) => (
            <button type="button" key={`${result.region_id}-${result.rank}`} className={`result-card panel ${selected?.region_id === result.region_id ? "result-selected" : ""}`} onClick={() => setSelectedId(result.region_id)}>
              <div className="result-header"><div><span className="small-label">Rank #{result.rank}</span><h3>{result.region_id}</h3></div><div className="score-box"><span>Semantic similarity score</span><strong>{formatNumber(result.retrieval_score)}</strong></div></div>
              <dl className="metadata-grid"><div><dt>Area</dt><dd>{formatNumber(result.area_m2)} m²</dd></div><div><dt>Pixels</dt><dd>{formatNumber(result.pixel_count)}</dd></div><div><dt>Reference</dt><dd>{result.reference_date || "—"}</dd></div><div><dt>Moving</dt><dd>{result.moving_date || "—"}</dd></div></dl>
              {result.semantic_description ? <p className="description">{result.semantic_description}</p> : null}
            </button>
          ))}
        </div>

        <aside className="details-column panel">
          <div className="section-heading"><div><span className="eyebrow">Evidence dossier</span><h2>{selected ? selected.region_id : "Select a region"}</h2></div></div>
          {selected ? <>
            <div className="detail-grid"><Metric label="Rank" value={selected.rank} /><Metric label="Similarity" value={selected.retrieval_score} /><Metric label="Area" value={selected.area_m2} suffix=" m²" /><Metric label="Pixels" value={selected.pixel_count} /></div>
            <EvidenceBlock title="Dates"><p>{selected.reference_date || "—"} <span className="arrow">→</span> {selected.moving_date || "—"}</p></EvidenceBlock>
            <EvidenceBlock title="Change magnitude"><div className="metric-list"><Metric label="Mean" value={selected.mean_change_magnitude} /><Metric label="Median" value={selected.median_change_magnitude} /><Metric label="Maximum" value={selected.max_change_magnitude} /></div></EvidenceBlock>
            <EvidenceBlock title="Spectral evidence"><p>{typeof selected.spectral_summary === "string" ? selected.spectral_summary : selected.spectral_summary ? JSON.stringify(selected.spectral_summary, null, 2) : "No spectral summary available from the API response."}</p></EvidenceBlock>
            <EvidenceBlock title="Semantic description"><p>{selected.semantic_description || "No description available."}</p></EvidenceBlock>
            {includeInterpretation && selected.scientific_interpretation ? <EvidenceBlock title="Cautious spectral interpretation" className="caution"><p>{selected.scientific_interpretation}</p></EvidenceBlock> : null}
            <EvidenceBlock title="Scientific limitations" className="warning"><ul>{[...(selected.limitations || []), ...DEFAULT_LIMITATIONS.filter((item) => !(selected.limitations || []).includes(item))].map((item) => <li key={item}>{item}</li>)}</ul></EvidenceBlock>
            <EvidenceBlock title="Provenance"><ul><li>Phase 9 geometry: data/processed/regions/regions.geojson</li><li>Phase 11 retrieval: data/retrieval/retrieval_report.json</li><li>Phase 12 interpretation: data/retrieval_analysis/retrieval_analysis.json</li><li>Phase 13 service: POST /api/retrieval/search</li></ul></EvidenceBlock>
          </> : <p className="muted">Search first, then select a returned region to inspect its measured evidence.</p>}
        </aside>
      </section>

      <section className="visualization panel"><div className="section-heading"><div><span className="eyebrow">Spatial evidence</span><h2>Phase 9 region geometry</h2></div><span className="muted">Offline SVG / no map tiles</span></div><GeometryView geojson={geojson} selectedId={selected?.region_id} resultIds={resultIds} />{geometryError ? <p className="muted">{geometryError}</p> : <p className="caption">Geometry is read from the generated GeoJSON artifact and highlighted for the selected retrieval result.</p>}</section>
      <footer className="scientific-note"><strong>Measured:</strong> spectral differences, change magnitude, region area, pixel count, and semantic similarity. <strong>Not verified:</strong> ground-truth land-cover events or confirmed vegetation change.</footer>
    </main>
  );
}

export default App;
