import { useEffect, useState } from "react";
import { api } from "../api.js";
import { courseLabel } from "../courses.js";

const DAY_NAMES = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"];

export default function HistoryView() {
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
    const label = new Date(week.week_start_date).toLocaleDateString("nl-NL");
    if (!confirm(`Weekmenu van ${label} verwijderen?`)) return;
    try {
      await api.deleteMenuWeek(week.week_start_date);
      setWeeks((prev) => prev.filter((w) => w.week_start_date !== week.week_start_date));
    } catch (e) {
      setError(e.message);
    }
  };

  if (loading) return <p className="status-text">Geschiedenis wordt geladen…</p>;

  return (
    <div>
      <p className="help-text">Eerdere weekmenu's, ter inspiratie voor hergebruik.</p>

      {error && <p className="error-text">{error}</p>}

      {weeks.length === 0 && <p className="status-text">Nog geen eerdere weken.</p>}

      <div className="history-list">
        {weeks.map((week) => (
          <div key={week.week_start_date} className="history-week">
            <div className="history-week-header">
              <h3>Week van {new Date(week.week_start_date).toLocaleDateString("nl-NL")}</h3>
              <button className="danger" onClick={() => handleDelete(week)}>
                Verwijder
              </button>
            </div>
            <ul className="history-days">
              {week.days.map((day) => (
                <li key={day.day_of_week}>
                  <span className="day-name">{DAY_NAMES[day.day_of_week]}</span>
                  {day.recipe ? (
                    <>
                      <a href={day.recipe.url} target="_blank" rel="noreferrer">
                        {day.recipe.title}
                      </a>
                      <span className="help-text small"> ({courseLabel(day.recipe.course)})</span>
                    </>
                  ) : (
                    <span className="status-text">geen recept</span>
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
