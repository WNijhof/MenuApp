import { useEffect, useState } from "react";
import { api } from "../api.js";
import { taxonomyCategoryLabel } from "../taxonomyCategories.js";
import { useTranslation } from "../i18n.jsx";

export default function ExclusionManager() {
  const { t, language } = useTranslation();
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

  if (loading) return <p className="status-text">{t("exclusions.loading")}</p>;

  return (
    <div>
      <p className="help-text">
        {t("exclusions.helpPrefix")} <em>{t("exclusions.example1")}</em>, <em>{t("exclusions.example2")}</em>,{" "}
        <em>{t("exclusions.example3")}</em>
        {t("exclusions.helpMiddle")} <em>{t("exclusions.example4")}</em>
        {t("exclusions.helpSuffix")}
      </p>

      {error && <p className="error-text">{error}</p>}

      <form className="inline-form" onSubmit={handleAdd}>
        <input
          type="text"
          list="taxonomy-categories"
          placeholder={t("exclusions.placeholder")}
          value={term}
          onChange={(e) => setTerm(e.target.value)}
        />
        <datalist id="taxonomy-categories">
          {taxonomy.map((cat) => (
            <option key={cat} value={cat}>
              {taxonomyCategoryLabel(cat, language)}
            </option>
          ))}
        </datalist>
        <button type="submit">{t("exclusions.addButton")}</button>
      </form>

      <ul className="exclusion-list">
        {exclusions.map((exclusion) => (
          <li key={exclusion.id}>
            <div>
              <strong>{exclusion.term}</strong>
              {exclusion.expands_to.length > 1 && (
                <div className="help-text small">
                  {t("exclusions.alsoLabel")} {exclusion.expands_to.filter((tm) => tm !== exclusion.term).join(", ")}
                </div>
              )}
            </div>
            <button onClick={() => handleDelete(exclusion)} className="danger">
              {t("common.delete")}
            </button>
          </li>
        ))}
        {exclusions.length === 0 && <li className="status-text">{t("exclusions.empty")}</li>}
      </ul>
    </div>
  );
}
