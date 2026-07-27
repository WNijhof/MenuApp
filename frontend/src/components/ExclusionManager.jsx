import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function ExclusionManager() {
  const [exclusions, setExclusions] = useState([]);
  const [taxonomy, setTaxonomy] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [term, setTerm] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const [ex, tax] = await Promise.all([
        api.getExclusions(),
        api.getTaxonomyCategories(),
      ]);
      setExclusions(ex);
      setTaxonomy(tax);
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
    const value = term.trim();
    if (!value) return;
    setError(null);
    try {
      await api.createExclusion(value);
      setTerm("");
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleDelete = async (exclusion) => {
    try {
      await api.deleteExclusion(exclusion.id);
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  if (loading) return <p className="status-text">Uitsluitingen worden geladen…</p>;

  return (
    <div>
      <p className="help-text">
        Vul een categorie in (bv. <em>vis</em>, <em>noten</em>, <em>varken</em>) om alle
        verwante ingrediënten (kabeljauw, zalm, ...) uit te sluiten, of typ een los
        ingrediënt (bv. <em>koriander</em>).
      </p>

      {error && <p className="error-text">{error}</p>}

      <form className="inline-form" onSubmit={handleAdd}>
        <input
          type="text"
          list="taxonomy-categories"
          placeholder="bv. vis, noten, koriander"
          value={term}
          onChange={(e) => setTerm(e.target.value)}
        />
        <datalist id="taxonomy-categories">
          {taxonomy.map((cat) => (
            <option key={cat} value={cat} />
          ))}
        </datalist>
        <button type="submit">Uitsluiten</button>
      </form>

      <ul className="exclusion-list">
        {exclusions.map((exclusion) => (
          <li key={exclusion.id}>
            <div>
              <strong>{exclusion.term}</strong>
              {exclusion.expands_to.length > 1 && (
                <div className="help-text small">
                  Ook: {exclusion.expands_to.filter((t) => t !== exclusion.term).join(", ")}
                </div>
              )}
            </div>
            <button onClick={() => handleDelete(exclusion)} className="danger">
              Verwijder
            </button>
          </li>
        ))}
        {exclusions.length === 0 && <li className="status-text">Nog geen uitsluitingen.</li>}
      </ul>
    </div>
  );
}
