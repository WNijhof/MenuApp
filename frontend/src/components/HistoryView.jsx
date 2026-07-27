import { useEffect, useState } from "react";
import { api } from "../api.js";
import { courseLabel } from "../courses.js";
import { useTranslation } from "../i18n.jsx";

const DAY_NAME_KEYS = [
  "day.monday",
  "day.tuesday",
  "day.wednesday",
  "day.thursday",
  "day.friday",
  "day.saturday",
  "day.sunday",
];

const LOCALE_BY_LANG = { en: "en-GB", nl: "nl-NL" };

export default function HistoryView() {
  const { t, language } = useTranslation();
  const [weeks, setWeeks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        setWeeks(await api.getMenuHistory());
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const handleDelete = async (week) => {
    const label = new Date(week.week_start_date).toLocaleDateString(LOCALE_BY_LANG[language] || "en-GB");
    if (!confirm(t("history.confirmDelete", { date: label }))) return;
    try {
      await api.deleteMenuWeek(week.week_start_date);
      setWeeks((prev) => prev.filter((w) => w.week_start_date !== week.week_start_date));
    } catch (e) {
      setError(e.message);
    }
  };

  if (loading) return <p className="status-text">{t("history.loading")}</p>;

  return (
    <div>
      <p className="help-text">{t("history.help")}</p>

      {error && <p className="error-text">{error}</p>}

      {weeks.length === 0 && <p className="status-text">{t("history.empty")}</p>}

      <div className="history-list">
        {weeks.map((week) => (
          <div key={week.week_start_date} className="history-week">
            <div className="history-week-header">
              <h3>
                {t("history.weekOf", {
                  date: new Date(week.week_start_date).toLocaleDateString(LOCALE_BY_LANG[language] || "en-GB"),
                })}
                {week.frozen && <span title={t("week.frozenBadgeTitle")}> ❄️</span>}
              </h3>
              <button className="danger" onClick={() => handleDelete(week)} disabled={week.frozen}>
                {t("common.delete")}
              </button>
            </div>
            <ul className="history-days">
              {week.days.map((day) => (
                <li key={day.day_of_week}>
                  <span className="day-name">{t(DAY_NAME_KEYS[day.day_of_week])}</span>
                  {day.recipe ? (
                    <>
                      <a href={day.recipe.url} target="_blank" rel="noreferrer">
                        {day.recipe.title}
                      </a>
                      <span className="help-text small"> ({courseLabel(day.recipe.course, language)})</span>
                    </>
                  ) : (
                    <span className="status-text">{t("history.noRecipe")}</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
