import { useEffect, useState } from "react";
import { api } from "../api.js";
import { dishTypeLabel } from "../dishTypes.js";
import { COURSE_LABELS, courseLabel } from "../courses.js";

export default function RecipeManager() {
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

  if (loading) return <p className="status-text">Recepten worden geladen…</p>;

  return (
    <div>
      <p className="help-text">
        Voeg een los recept toe via een directe link naar de receptpagina.
      </p>

      {error && <p className="error-text">{error}</p>}

      <form className="inline-form" onSubmit={handleAdd}>
        <input
          type="url"
          placeholder="https://voorbeeld.nl/recepten/mijn-recept"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
        <button type="submit" disabled={adding}>
          {adding ? "Bezig…" : "Toevoegen"}
        </button>
      </form>

      <div className="toolbar">
        <label>
          Gang:{" "}
          <select value={courseFilter} onChange={handleCourseFilterChange}>
            <option value="">Alle gangen</option>
            {Object.entries(COURSE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <p className="status-text">{recipes.length} recepten in de database</p>

      <table className="data-table">
        <thead>
          <tr>
            <th>Titel</th>
            <th>Type</th>
            <th>Gang</th>
            <th>Waardering</th>
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
                  <span className="offer-badge" title="Bevat een product dat nu in de aanbieding is">
                    🏷️ aanbieding
                  </span>
                )}
              </td>
              <td>{dishTypeLabel(recipe.dish_type)}</td>
              <td>{courseLabel(recipe.course)}</td>
              <td className="rating-buttons">
                <button
                  className={recipe.rating === "like" ? "icon-button active" : "icon-button"}
                  onClick={() => handleRate(recipe, "like")}
                  title="Favoriet"
                  aria-label="Favoriet"
                >
                  👍
                </button>
                <button
                  className={recipe.rating === "dislike" ? "icon-button active" : "icon-button"}
                  onClick={() => handleRate(recipe, "dislike")}
                  title="Niet lekker"
                  aria-label="Niet lekker"
                >
                  👎
                </button>
              </td>
              <td className="row-actions">
                <button onClick={() => handleDelete(recipe)} className="danger">
                  Verwijder
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
