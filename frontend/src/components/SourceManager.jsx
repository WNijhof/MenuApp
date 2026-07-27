import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function SourceManager() {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [syncingId, setSyncingId] = useState(null);
  const [syncingAll, setSyncingAll] = useState(false);
  const [syncResults, setSyncResults] = useState([]);
  const [newSource, setNewSource] = useState({ name: "", base_url: "" });

  const load = async () => {
    setLoading(true);
    try {
      setSources(await api.getSources());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!newSource.name.trim() || !newSource.base_url.trim()) return;
    setError(null);
    try {
      await api.createSource(newSource);
      setNewSource({ name: "", base_url: "" });
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleToggle = async (source) => {
    try {
      await api.updateSource(source.id, { enabled: !source.enabled });
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleDelete = async (source) => {
    if (!confirm(`Bron "${source.name}" en bijbehorende recepten verwijderen?`)) return;
    try {
      await api.deleteSource(source.id);
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleSync = async (source) => {
    setSyncingId(source.id);
    setError(null);
    try {
      const result = await api.syncSource(source.id);
      setSyncResults((prev) => [result, ...prev].slice(0, 10));
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setSyncingId(null);
    }
  };

  const handleSyncAll = async () => {
    setSyncingAll(true);
    setError(null);
    try {
      const results = await api.syncAllSources();
      setSyncResults(results);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setSyncingAll(false);
    }
  };

  if (loading) return <p className="status-text">Bronnen worden geladen…</p>;

  return (
    <div>
      <div className="toolbar">
        <button onClick={handleSyncAll} disabled={syncingAll}>
          {syncingAll ? "Bezig…" : "Synchroniseer alle bronnen"}
        </button>
      </div>

      {error && <p className="error-text">{error}</p>}

      <form className="inline-form" onSubmit={handleAdd}>
        <input
          type="text"
          placeholder="Naam (bv. Mijn favoriete site)"
          value={newSource.name}
          onChange={(e) => setNewSource({ ...newSource, name: e.target.value })}
        />
        <input
          type="url"
          placeholder="https://voorbeeld.nl/recepten"
          value={newSource.base_url}
          onChange={(e) => setNewSource({ ...newSource, base_url: e.target.value })}
        />
        <button type="submit">Bron toevoegen</button>
      </form>

      <table className="data-table">
        <thead>
          <tr>
            <th>Naam</th>
            <th>URL</th>
            <th>Aan</th>
            <th>Laatst gesynchroniseerd</th>
            <th>Recepten</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {sources.map((source) => (
            <tr key={source.id}>
              <td>{source.name}</td>
              <td className="truncate">
                <a href={source.base_url} target="_blank" rel="noreferrer">
                  {source.base_url}
                </a>
              </td>
              <td>
                <input
                  type="checkbox"
                  checked={source.enabled}
                  onChange={() => handleToggle(source)}
                />
              </td>
              <td>
                {source.last_synced_at
                  ? new Date(source.last_synced_at).toLocaleString("nl-NL")
                  : "nooit"}
                {source.last_sync_error && (
                  <div className="error-text small">{source.last_sync_error}</div>
                )}
              </td>
              <td>{source.recipe_count}</td>
              <td className="row-actions">
                <button onClick={() => handleSync(source)} disabled={syncingId === source.id}>
                  {syncingId === source.id ? "…" : "Sync"}
                </button>
                <button onClick={() => handleDelete(source)} className="danger">
                  Verwijder
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {syncResults.length > 0 && (
        <div className="sync-results">
          <h4>Laatste synchronisatie</h4>
          <ul>
            {syncResults.map((r, i) => (
              <li key={i}>
                {r.source_name}: {r.recipes_found} nieuwe recepten
                {r.recipes_updated > 0 && `, ${r.recipes_updated} ververst`} (
                {r.pages_checked} pagina's gecontroleerd)
                {r.error && <span className="error-text"> — {r.error}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
