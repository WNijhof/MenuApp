import { useState } from "react";
import { thumbUrl } from "../api.js";
import { dishTypeLabel } from "../dishTypes.js";
import { courseLabel } from "../courses.js";
import { useTranslation } from "../i18n.jsx";
import RecipeAutocomplete from "./RecipeAutocomplete.jsx";
import RecipeDetailModal from "./RecipeDetailModal.jsx";

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
  pinned = false,
  cooked = false,
  skipShopping = false,
  onRefresh,
  onRefreshQuery,
  onPickRecipe,
  onTogglePinned,
  onToggleCooked,
  onToggleSkipShopping,
  refreshing,
  onRate,
  showDayName = true,
  frozen = false,
}) {
  const { t, language } = useTranslation();
  const [showSwapSearch, setShowSwapSearch] = useState(false);
  const [showDetail, setShowDetail] = useState(false);

  // A pinned or cooked dish is deliberately "done": swapping it needs an
  // explicit unpin first. (Freezing the week locks swaps for every day.)
  const swapLocked = frozen || pinned || cooked;
  const swapLockedTitle = frozen
    ? t("day.rerollFrozen")
    : cooked
      ? t("day.swapLockedCooked")
      : t("day.swapLockedPinned");

  const closeSearchAnd = (fn) => (...args) => {
    setShowSwapSearch(false);
    fn(...args);
  };

  const image = recipe?.image_url ? (
    <img
      src={thumbUrl(recipe)}
      alt=""
      loading="lazy"
      decoding="async"
      onError={(e) => {
        // Thumbnail unavailable - fall back to the original image once.
        if (e.currentTarget.src !== recipe.image_url) e.currentTarget.src = recipe.image_url;
      }}
    />
  ) : (
    <div className="day-card-image-placeholder" />
  );

  return (
    <div className={cooked ? "day-card day-card-cooked" : "day-card"}>
      <div className="day-card-header">
        <span className="day-card-header-left">
          {recipe && onToggleCooked && (
            <input
              type="checkbox"
              className="day-card-cooked-check"
              checked={cooked}
              onChange={onToggleCooked}
              title={cooked ? t("day.uncook") : t("day.cooked")}
              aria-label={cooked ? t("day.uncook") : t("day.cooked")}
            />
          )}
          <span className="day-name">{showDayName ? t(DAY_NAME_KEYS[dayOfWeek]) : ""}</span>
        </span>
        <div className="day-card-header-actions">
          {recipe && onToggleSkipShopping && (
            <button
              className={skipShopping ? "icon-button active" : "icon-button"}
              onClick={onToggleSkipShopping}
              title={skipShopping ? t("day.unskipShopping") : t("day.skipShopping")}
              aria-label={skipShopping ? t("day.unskipShopping") : t("day.skipShopping")}
            >
              🛒
            </button>
          )}
          {recipe && onTogglePinned && (
            <button
              className={pinned ? "icon-button active" : "icon-button"}
              onClick={onTogglePinned}
              title={pinned ? t("day.unpin") : t("day.pin")}
              aria-label={pinned ? t("day.unpin") : t("day.pin")}
            >
              📌
            </button>
          )}
          {onPickRecipe && (
            <button
              className={showSwapSearch ? "icon-button active" : "icon-button"}
              onClick={() => setShowSwapSearch((v) => !v)}
              disabled={swapLocked}
              title={swapLocked ? swapLockedTitle : t("day.swapToType")}
              aria-label={t("day.swapToType")}
            >
              🔍
            </button>
          )}
          <button
            className="icon-button"
            onClick={onRefresh}
            disabled={refreshing || swapLocked}
            title={swapLocked ? swapLockedTitle : t("day.reroll")}
            aria-label={t("day.reroll")}
          >
            {refreshing ? "…" : "↻"}
          </button>
        </div>
      </div>

      {showSwapSearch && !swapLocked && (
        <div className="day-card-swap-search">
          <RecipeAutocomplete
            course={recipe?.course}
            disabled={refreshing}
            onPick={closeSearchAnd((suggestion) => onPickRecipe(suggestion.id))}
            onSubmitText={closeSearchAnd((text) => onRefreshQuery(text))}
          />
        </div>
      )}

      {(cooked || skipShopping) && recipe && (
        <div className="day-card-status">
          {cooked && <span className="status-badge">✓ {t("day.cookedBadge")}</span>}
          {skipShopping && <span className="status-badge">🛒✕ {t("day.skippedBadge")}</span>}
        </div>
      )}

      {recipe ? (
        <>
          {recipe.is_manual ? (
            <button
              type="button"
              className="day-card-body day-card-body-button"
              onClick={() => setShowDetail(true)}
            >
              {image}
              <div className="day-card-info">
                <span className="dish-type-badge">{dishTypeLabel(recipe.dish_type, language)}</span>
                <span className="dish-type-badge">{courseLabel(recipe.course, language)}</span>
                <h3>{recipe.title}</h3>
              </div>
            </button>
          ) : (
            <a className="day-card-body" href={recipe.url} target="_blank" rel="noreferrer">
              {image}
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
          )}
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

      {showDetail && recipe && <RecipeDetailModal recipe={recipe} onClose={() => setShowDetail(false)} />}
    </div>
  );
}
