import { useEffect, useState } from "react";
import { api } from "../api.js";
import { dishTypeLabel } from "../dishTypes.js";
import { courseLabel } from "../courses.js";

export default function NietLekkerView() {
  const [recipes, setRecipes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      setRecipes(await api.getRecipes({ rating: "dislike" }));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleRestore = async (recipe) => {
    try {
      await api.rateRecipe(recipe.id, null);
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  if (loading) return <p className="status-text">Wordt geladen…</p>;

  return (
    <div>
      <p className="help-text">
        Recepten die je 👎 hebt gegeven worden niet meer herhaald in het weekmenu. Zet de
        waardering terug om een recept weer mee te laten doen.
      </p>

      {error && <p className="error-text">{error}</p>}

      <table className="data-table">
        <thead>
          <tr>
            <th>Titel</th>
            <th>Type</th>
            <th>Gang</th>
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
              </td>
              <td>{dishTypeLabel(recipe.dish_type)}</td>
              <td>{courseLabel(recipe.course)}</td>
              <td className="row-actions">
                <button onClick={() => handleRestore(recipe)}>Terugzetten</button>
              </td>
            </tr>
          ))}
          {recipes.length === 0 && (
            <tr>
              <td colSpan={4} className="status-text">
                Nog geen recepten als "niet lekker" gemarkeerd.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
