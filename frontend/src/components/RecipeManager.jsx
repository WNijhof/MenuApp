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

  const handleDelete = async (recipe) => {
    try {
      await api.deleteRecipe(recipe.id);
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
      <p className="help-text">{t("recipes.help")}</p>

      {error && <p className="error-text">{error}</p>}

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
                <a href={recipe.url} target="_blank" rel="noreferrer">
                  {recipe.title}
                </a>
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
