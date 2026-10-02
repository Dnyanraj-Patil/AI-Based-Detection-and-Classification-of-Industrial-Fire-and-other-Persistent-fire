import React from "react";
import { searchLocation } from "../services/api";

const RADII = [5, 10, 25, 50, 100, 250];

export default function LocationFilter({ value, onApply, compact = false }) {
  const [query, setQuery] = React.useState(value?.label || "");
  const [radius, setRadius] = React.useState(value?.radius_km || 25);
  const [busy, setBusy] = React.useState(false);
  const [message, setMessage] = React.useState("");

  React.useEffect(() => {
    setQuery(value?.label || "");
    if (value?.radius_km) setRadius(value.radius_km);
  }, [value?.label, value?.radius_km]);

  async function apply() {
    const q = query.trim();
    if (!q) {
      onApply?.(null);
      setMessage("");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const result = await searchLocation(q);
      if (!result?.found) {
        setMessage("Location not found. Try a city or area name in India.");
        return;
      }
      onApply?.({
        label: result.label,
        latitude: Number(result.latitude),
        longitude: Number(result.longitude),
        radius_km: Number(radius),
      });
      setQuery(result.label);
    } catch (err) {
      setMessage(err?.response?.data?.detail || "Location search failed.");
    } finally {
      setBusy(false);
    }
  }

  function clear() {
    setQuery("");
    setMessage("");
    onApply?.(null);
  }

  return (
    <div className={`location-filter ${compact ? "compact" : ""}`}>
      <div className="location-filter-title">LOCATION INTELLIGENCE</div>
      <div className="location-filter-row">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") apply(); }}
          placeholder="Search city / area (e.g. Pune)"
          aria-label="Search city or area"
        />
        <select value={radius} onChange={(e) => setRadius(Number(e.target.value))} aria-label="Search radius">
          {RADII.map((r) => <option key={r} value={r}>{r} km</option>)}
        </select>
        <button type="button" onClick={apply} disabled={busy}>{busy ? "Searching…" : "Apply"}</button>
        <button type="button" onClick={clear} className="location-clear">Clear</button>
      </div>
      {value?.label && <div className="location-filter-active">Monitoring {value.label} within {value.radius_km} km</div>}
      {message && <div className="location-filter-message">{message}</div>}
    </div>
  );
}
