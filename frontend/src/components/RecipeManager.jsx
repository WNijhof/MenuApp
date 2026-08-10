import { useEffect, useState } from "react";
import { api } from "../api.js";
import { dishTypeLabel } from "../dishTypes.js";
import { courseLabels, courseLabel } from "../courses.js";
import { useTranslation } from "../i18n.jsx";

export default function RecipeManager() {
  const { t, language } = useTranslation();
  const [recipes, setRecipes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState(null);
  const [url, setUrl] = useState("");
  const [courseFilter, setCourseFilter] = useState("");

  const [mode, setMode] = useState("url");
  const [editingId, setEditingId] = useState(null);
  const [manualTitle, setManualTitle] = useState("");
  const [manualIngredients, setManualIngredients] = useState("");
  const [manualInstructions, setManualInstructions] = useState("");
  const [manualServings, setManualServings] = useState("");
  const [manualCourse, setManualCourse] = useState("");

  const load = async (course = courseFilter) => {
    setLoading(true);
    try {
      setRecipes(await api.getRecipes({ course }));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleCourseFilterChange = (e) => {
    const value = e.target.value;
    setCourseFilter(value);
    load(value);
  };

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!url.trim()) return;
    setAdding(true);
    setError(null);
    try {
      await api.addRecipeByUrl(url.trim());
      setUrl("");
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setAdding(false);
    }
  };

  const resetManualForm = () => {
    setEditingId(null);
    setManualTitle("");
    setManualIngredients("");
    setManualInstructions("");
    setManualServings("");
    setManualCourse("");
  };

  const handleManualSubmit = async (e) => {
    e.preventDefault();
    if (!manualTitle.trim() || !manualIngredients.trim()) return;
    setAdding(true);
    setError(null);
    const payload = {
      title: manualTitle.trim(),
      ingredients: manualIngredients.split("\n"),
      instructions: manualInstructions.split("\n"),
      servings: manualServings.trim() || null,
      course: manualCourse || null,
    };
    try {
      if (editingId) {
        await api.updateManualRecipe(editingId, payload);
      } else {
        await api.addManualRecipe(payload);
      }
      resetManualForm();
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setAdding(false);
    }
  };

  const handleEditManual = (recipe) => {
    setMode("manual");
    setEditingId(recipe.id);
    setManualTitle(recipe.title);
    setManualIngredients(recipe.ingredients.join("\n"));
    setManualInstructions(recipe.instructions.join("\n"));
    setManualServings(recipe.servings || "");
    setManualCourse(recipe.course || "");
  };

  const handleDelete = async (recipe) => {
    try {
      await api.deleteRecipe(recipe.id);
      if (editingId === recipe.id) resetManualForm();
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleRate = async (recipe, rating) => {
    try {
      await api.rateRecipe(recipe.id, recipe.rating === rating ? null : rating);
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  if (loading) return <p className="status-text">{t("recipes.loading")}</p>;

  return (
    <div>
      <div className="tabs recipe-add-tabs">
        <button
          className={mode === "url" ? "tab active" : "tab"}
          onClick={() => {
            setMode("url");
            resetManualForm();
          }}
        >
          {t("recipes.addByUrlTab")}
        </button>
        <button
          className={mode === "manual" ? "tab active" : "tab"}
          onClick={() => setMode("manual")}
        >
          {t("recipes.addManualTab")}
        </button>
      </div>

      {error && <p className="error-text">{error}</p>}

      {mode === "url" ? (
        <>
          <p className="help-text">{t("recipes.help")}</p>
          <form className="inline-form" onSubmit={handleAdd}>
            <input
              type="url"
              placeholder={t("recipes.urlPlaceholder")}
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
            <button type="submit" disabled={adding}>
              {adding ? t("common.busy") : t("common.add")}
            </button>
          </form>
        </>
      ) : (
        <>
          <p className="help-text">{t("recipes.manualHelp")}</p>
          <form className="manual-recipe-form" onSubmit={handleManualSubmit}>
            <input
              type="text"
              placeholder={t("recipes.manualTitlePlaceholder")}
              value={manualTitle}
              onChange={(e) => setManualTitle(e.target.value)}
            />
            <textarea
              className="shopping-list-textarea"
              rows={5}
              placeholder={t("recipes.manualIngredientsPlaceholder")}
              value={manualIngredients}
              onChange={(e) => setManualIngredients(e.target.value)}
            />
            <textarea
              className="shopping-list-textarea"
              rows={5}
              placeholder={t("recipes.manualInstructionsPlaceholder")}
              value={manualInstructions}
              onChange={(e) => setManualInstructions(e.target.value)}
            />
            <div className="manual-recipe-form-row">
              <input
                type="text"
                placeholder={t("recipes.manualServingsPlaceholder")}
                value={manualServings}
                onChange={(e) => setManualServings(e.target.value)}
              />
              <select value={manualCourse} onChange={(e) => setManualCourse(e.target.value)}>
                <option value="">{t("recipes.manualCourseAuto")}</option>
                {Object.entries(courseLabels(language)).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <div className="manual-recipe-form-row">
              <button type="submit" disabled={adding || !manualTitle.trim() || !manualIngredients.trim()}>
                {adding ? t("common.busy") : editingId ? t("common.save") : t("common.add")}
              </button>
              {editingId && (
                <button type="button" onClick={resetManualForm}>
                  {t("recipes.manualCancelEdit")}
                </button>
              )}
            </div>
          </form>
        </>
      )}

      <div className="toolbar">
        <label>
          {t("recipes.courseFilterLabel")}{" "}
          <select value={courseFilter} onChange={handleCourseFilterChange}>
            <option value="">{t("recipes.allCourses")}</option>
            {Object.entries(courseLabels(language)).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <p className="status-text">{t("recipes.count", { count: recipes.length })}</p>

      <table className="data-table">
        <thead>
          <tr>
            <th>{t("common.title")}</th>
            <th>{t("common.dishType")}</th>
            <th>{t("common.course")}</th>
            <th>{t("recipes.rating")}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {recipes.map((recipe) => (
            <tr key={recipe.id}>
              <td>
                {recipe.is_manual ? (
                  <span>{recipe.title}</span>
                ) : (
                  <a href={recipe.url} target="_blank" rel="noreferrer">
                    {recipe.title}
                  </a>
                )}
                {recipe.is_manual && <span className="manual-badge">{t("recipes.manualBadge")}</span>}
                {recipe.has_offer && (
                  <span className="offer-badge" title={t("offer.badgeTitle")}>
                    {t("offer.badgeText")}
                  </span>
                )}
              </td>
              <td>{dishTypeLabel(recipe.dish_type, language)}</td>
              <td>{courseLabel(recipe.course, language)}</td>
              <td className="rating-buttons">
                <button
                  className={recipe.rating === "like" ? "icon-button active" : "icon-button"}
                  onClick={() => handleRate(recipe, "like")}
                  title={t("day.favorite")}
                  aria-label={t("day.favorite")}
                >
                  👍
                </button>
                <button
                  className={recipe.rating === "dislike" ? "icon-button active" : "icon-button"}
                  onClick={() => handleRate(recipe, "dislike")}
                  title={t("day.dislike")}
                  aria-label={t("day.dislike")}
                >
                  👎
                </button>
              </td>
              <td className="row-actions">
                {recipe.is_manual && (
                  <button onClick={() => handleEditManual(recipe)}>{t("common.edit")}</button>
                )}
                <button onClick={() => handleDelete(recipe)} className="danger">
                  {t("common.delete")}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
