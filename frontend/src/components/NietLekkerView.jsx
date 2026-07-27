import { useEffect, useState } from "react";
import { api } from "../api.js";
import { dishTypeLabel } from "../dishTypes.js";
import { courseLabel } from "../courses.js";
import { useTranslation } from "../i18n.jsx";

export default function NietLekkerView() {
  const { t, language } = useTranslation();
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

  if (loading) return <p className="status-text">{t("disliked.loading")}</p>;

  return (
    <div>
      <p className="help-text">{t("disliked.help")}</p>

      {error && <p className="error-text">{error}</p>}

      <table className="data-table">
        <thead>
          <tr>
            <th>{t("common.title")}</th>
            <th>{t("common.dishType")}</th>
            <th>{t("common.course")}</th>
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
              <td>{dishTypeLabel(recipe.dish_type, language)}</td>
              <td>{courseLabel(recipe.course, language)}</td>
              <td className="row-actions">
                <button onClick={() => handleRestore(recipe)}>{t("disliked.restore")}</button>
              </td>
            </tr>
          ))}
          {recipes.length === 0 && (
            <tr>
              <td colSpan={4} className="status-text">
                {t("disliked.empty")}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
