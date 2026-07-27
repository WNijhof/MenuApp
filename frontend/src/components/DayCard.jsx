import { dishTypeLabel } from "../dishTypes.js";
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

export default function DayCard({
  dayOfWeek,
  recipe,
  onRefresh,
  refreshing,
  onRate,
  showDayName = true,
  frozen = false,
}) {
  const { t, language } = useTranslation();

  return (
    <div className="day-card">
      <div className="day-card-header">
        <span className="day-name">{showDayName ? t(DAY_NAME_KEYS[dayOfWeek]) : ""}</span>
        <button
          className="icon-button"
          onClick={onRefresh}
          disabled={refreshing || frozen}
          title={frozen ? t("day.rerollFrozen") : t("day.reroll")}
          aria-label={t("day.reroll")}
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
              <span className="dish-type-badge">{dishTypeLabel(recipe.dish_type, language)}</span>
              <span className="dish-type-badge">{courseLabel(recipe.course, language)}</span>
              {recipe.has_offer && (
                <span className="offer-badge" title={t("offer.badgeTitle")}>
                  {t("offer.badgeText")}
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
                title={t("day.favorite")}
                aria-label={t("day.favorite")}
              >
                👍
              </button>
              <button
                className={recipe.rating === "dislike" ? "icon-button active" : "icon-button"}
                onClick={() => onRate("dislike")}
                title={t("day.dislike")}
                aria-label={t("day.dislike")}
              >
                👎
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="day-card-empty">{t("day.noRecipe")}</div>
      )}
    </div>
  );
}
