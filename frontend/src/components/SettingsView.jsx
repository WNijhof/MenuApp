import { useEffect, useState } from "react";
import { api } from "../api.js";

const DAYS_PER_WEEK = 7;

export default function SettingsView() {
  const [counts, setCounts] = useState({ hoofdgerecht: 7, voorgerecht: 0, nagerecht: 0 });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const settings = await api.getSettings();
        setCounts({
          hoofdgerecht: settings.default_hoofdgerecht,
          voorgerecht: settings.default_voorgerecht,
          nagerecht: settings.default_nagerecht,
        });
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const total = counts.hoofdgerecht + counts.voorgerecht + counts.nagerecht;
  const valid = total <= DAYS_PER_WEEK;

  const handleChange = (course, value) => {
    const n = Math.max(0, parseInt(value, 10) || 0);
    setCounts((prev) => ({ ...prev, [course]: n }));
    setSaved(false);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!valid) return;
    setSaving(true);
    setError(null);
    try {
      await api.updateSettings({
        default_hoofdgerecht: counts.hoofdgerecht,
        default_voorgerecht: counts.voorgerecht,
        default_nagerecht: counts.nagerecht,
      });
      setSaved(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <p className="status-text">Instellingen worden geladen…</p>;

  return (
    <div>
      <p className="help-text">
        Standaard aantal gerechten per gang wanneer je een nieuwe week genereert. Dit is
        het startpunt — je kan het altijd per week nog aanpassen op het Weekmenu-tabblad.
      </p>

      {error && <p className="error-text">{error}</p>}

      <form className="toolbar course-count-toolbar" onSubmit={handleSave}>
        <label>
          Hoofdgerechten:{" "}
          <input
            type="number"
            min="0"
            max={DAYS_PER_WEEK}
            value={counts.hoofdgerecht}
            onChange={(e) => handleChange("hoofdgerecht", e.target.value)}
          />
        </label>
        <label>
          Voorgerechten:{" "}
          <input
            type="number"
            min="0"
            max={DAYS_PER_WEEK}
            value={counts.voorgerecht}
            onChange={(e) => handleChange("voorgerecht", e.target.value)}
          />
        </label>
        <label>
          Nagerechten:{" "}
          <input
            type="number"
            min="0"
            max={DAYS_PER_WEEK}
            value={counts.nagerecht}
            onChange={(e) => handleChange("nagerecht", e.target.value)}
          />
        </label>
        <button type="submit" disabled={saving || !valid}>
          {saving ? "Bezig…" : saved ? "Opgeslagen!" : "Opslaan"}
        </button>
      </form>
      {!valid && (
        <p className="error-text">Aantal gerechten kan niet meer dan {DAYS_PER_WEEK} zijn (nu {total}).</p>
      )}
    </div>
  );
}
