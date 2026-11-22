import { useState } from "react";
import { useTranslation } from "../i18n.jsx";

// Per-day tweaks to a recipe's ingredients for the shopping list only: untick
// a line to leave it off, or edit its text (e.g. a smaller amount, or a
// substitute). The recipe itself is never changed. `overrides` is
// {original line: replacement, or null = left off}.
export default function IngredientEditModal({ recipe, overrides = {}, onSave, onClose }) {
  const { t } = useTranslation();
  const [rows, setRows] = useState(() =>
    recipe.ingredients.map((original) => {
      const has = Object.prototype.hasOwnProperty.call(overrides, original);
      const replacement = has ? overrides[original] : undefined;
      return {
        original,
        included: !has || replacement !== null,
        text: has && replacement ? replacement : original,
      };
    })
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const update = (i, patch) =>
    setRows((prev) => prev.map((row, j) => (j === i ? { ...row, ...patch } : row)));

  const handleSave = async () => {
    const next = {};
    for (const row of rows) {
      const text = row.text.trim();
      if (!row.included || !text) next[row.original] = null;
      else if (text !== row.original.trim()) next[row.original] = text;
    }
    setSaving(true);
    setError(null);
    try {
      await onSave(next);
      onClose();
    } catch (e) {
      setError(e.message);
      setSaving(false);
    }
  };

  const handleResetAll = () =>
    setRows((prev) => prev.map((row) => ({ ...row, included: true, text: row.original })));

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-panel" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{recipe.title}</h3>
          <button className="icon-button" onClick={onClose} aria-label={t("common.close")}>
            ✕
          </button>
        </div>
        <p className="status-text ingredient-edit-help">{t("day.ingredientsHelp")}</p>

        {rows.length === 0 ? (
          <p className="status-text">{t("recipes.noIngredients")}</p>
        ) : (
          <ul className="ingredient-edit-list">
            {rows.map((row, i) => {
              const changed = row.included && row.text.trim() !== row.original.trim();
              return (
                <li
                  key={i}
                  className={row.included ? "ingredient-edit-row" : "ingredient-edit-row ingredient-edit-removed"}
                >
                  <input
                    type="checkbox"
                    checked={row.included}
                    onChange={(e) => update(i, { included: e.target.checked })}
                    title={row.included ? t("day.ingredientRemove") : t("day.ingredientRestore")}
                    aria-label={row.included ? t("day.ingredientRemove") : t("day.ingredientRestore")}
                  />
                  <input
                    type="text"
                    value={row.text}
                    disabled={!row.included}
                    onChange={(e) => update(i, { text: e.target.value })}
                  />
                  {changed && (
                    <button
                      className="icon-button"
                      onClick={() => update(i, { text: row.original })}
                      title={t("day.ingredientUndo", { original: row.original })}
                      aria-label={t("day.ingredientUndo", { original: row.original })}
                    >
                      ↺
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        )}

        {error && <p className="error-text">{error}</p>}
        <div className="ingredient-edit-actions">
          <button onClick={handleResetAll} disabled={saving}>
            {t("day.ingredientsReset")}
          </button>
          <button className="primary-button" onClick={handleSave} disabled={saving}>
            {saving ? t("common.busy") : t("common.save")}
          </button>
        </div>
      </div>
    </div>
  );
}
