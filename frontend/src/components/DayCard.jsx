import { dishTypeLabel } from "../dishTypes.js";
import { courseLabel } from "../courses.js";

const DAY_NAMES = [
  "Maandag",
  "Dinsdag",
  "Woensdag",
  "Donderdag",
  "Vrijdag",
  "Zaterdag",
  "Zondag",
];

export default function DayCard({
  dayOfWeek,
  recipe,
  onRefresh,
  refreshing,
  onRate,
  showDayName = true,
  frozen = false,
}) {
  return (
    <div className="day-card">
      <div className="day-card-header">
        <span className="day-name">{showDayName ? DAY_NAMES[dayOfWeek] : ""}</span>
        <button
          className="icon-button"
          onClick={onRefresh}
          disabled={refreshing || frozen}
          title={frozen ? "Ontdooi de week om te wisselen" : "Wissel voor een ander recept"}
          aria-label="Wissel voor een ander recept"
        >
          {refreshing ? "…" : "↻"}
        </button>
      </div>

      {recipe ? (
        <>
          <a className="day-card-body" href={recipe.url} target="_blank" rel="noreferrer">
            {recipe.image_url ? (
              <img src={recipe.image_url} alt="" loading="lazy" />
            ) : (
              <div className="day-card-image-placeholder" />
            )}
            <div className="day-card-info">
              <span className="dish-type-badge">{dishTypeLabel(recipe.dish_type)}</span>
              <span className="dish-type-badge">{courseLabel(recipe.course)}</span>
              {recipe.has_offer && (
                <span
                  className="offer-badge"
                  title="Bevat een product dat nu in de aanbieding is"
                >
                  🏷️ aanbieding
                </span>
              )}
              <h3>{recipe.title}</h3>
              {recipe.total_time_minutes ? (
                <span className="time-badge">{recipe.total_time_minutes} min</span>
              ) : null}
            </div>
          </a>
          {onRate && (
            <div className="rating-buttons day-card-rating">
              <button
                className={recipe.rating === "like" ? "icon-button active" : "icon-button"}
                onClick={() => onRate("like")}
                title="Favoriet"
                aria-label="Favoriet"
              >
                👍
              </button>
              <button
                className={recipe.rating === "dislike" ? "icon-button active" : "icon-button"}
                onClick={() => onRate("dislike")}
                title="Niet lekker"
                aria-label="Niet lekker"
              >
                👎
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="day-card-empty">Geen recept beschikbaar</div>
      )}
    </div>
  );
}
