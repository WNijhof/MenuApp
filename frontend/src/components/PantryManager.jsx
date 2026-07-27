import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useTranslation } from "../i18n.jsx";

export default function PantryManager() {
  const { t } = useTranslation();
  const [staples, setStaples] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [term, setTerm] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      setStaples(await api.getPantryStaples());
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
      await api.createPantryStaple(value);
      setTerm("");
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleDelete = async (staple) => {
    try {
      await api.deletePantryStaple(staple.id);
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  if (loading) return <p className="status-text">{t("pantry.loading")}</p>;

  return (
    <div>
      <p className="help-text">
        {t("pantry.helpPrefix")} <em>{t("pantry.example1")}</em>, <em>{t("pantry.example2")}</em>,{" "}
        <em>{t("pantry.example3")}</em>
        {t("pantry.helpSuffix")}
      </p>

      {error && <p className="error-text">{error}</p>}

      <form className="inline-form" onSubmit={handleAdd}>
        <input
          type="text"
          placeholder={t("pantry.placeholder")}
          value={term}
          onChange={(e) => setTerm(e.target.value)}
        />
        <button type="submit">{t("common.add")}</button>
      </form>

      <ul className="exclusion-list">
        {staples.map((staple) => (
          <li key={staple.id}>
            <strong>{staple.term}</strong>
            <button onClick={() => handleDelete(staple)} className="danger">
              {t("common.delete")}
            </button>
          </li>
        ))}
        {staples.length === 0 && <li className="status-text">{t("pantry.empty")}</li>}
      </ul>
    </div>
  );
}
