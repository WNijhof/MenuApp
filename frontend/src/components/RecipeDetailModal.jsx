import { dishTypeLabel } from "../dishTypes.js";
import { courseLabel } from "../courses.js";
import { useTranslation } from "../i18n.jsx";

// `overrides` (optional): this day's shopping-list tweaks, {original line:
// replacement, or null = left off}. Replaced lines are marked so it's clear
// while cooking that something else was bought.
export default function RecipeDetailModal({ recipe, overrides = {}, onClose }) {
  const { t, language } = useTranslation();

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-panel" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{recipe.title}</h3>
          <button className="icon-button" onClick={onClose} aria-label={t("common.close")}>
            ✕
          </button>
        </div>
        <div className="modal-badges">
          <span className="dish-type-badge">{dishTypeLabel(recipe.dish_type, language)}</span>
          <span className="dish-type-badge">{courseLabel(recipe.course, language)}</span>
          {recipe.servings && <span className="time-badge">{recipe.servings}</span>}
        </div>

        <h4>{t("recipes.ingredients")}</h4>
        {recipe.ingredients.length > 0 ? (
          <ul className="modal-list">
            {recipe.ingredients.map((line, i) => {
              const replacement = overrides?.[line];
              return replacement ? (
                <li key={i} className="ingredient-replaced" title={t("day.replacedTitle")}>
                  ✎ <s>{line}</s> → <strong>{replacement}</strong>
                </li>
              ) : (
                <li key={i}>{line}</li>
              );
            })}
          </ul>
        ) : (
          <p className="status-text">{t("recipes.noIngredients")}</p>
        )}

        <h4>{t("recipes.instructions")}</h4>
        {recipe.instructions.length > 0 ? (
          <ol className="modal-list">
            {recipe.instructions.map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ol>
        ) : (
          <p className="status-text">{t("recipes.noInstructions")}</p>
        )}
      </div>
    </div>
  );
}
