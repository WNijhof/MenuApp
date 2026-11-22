import { useState } from "react";
import { thumbUrl } from "../api.js";
import { dishTypeLabel } from "../dishTypes.js";
import { courseLabel } from "../courses.js";
import { useTranslation } from "../i18n.jsx";
import AvgPicker from "./AvgPicker.jsx";
import IngredientEditModal from "./IngredientEditModal.jsx";
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
  avg = null,
  avgOptions = null,
  pinned = false,
  cooked = false,
  skipShopping = false,
  ingredientOverrides = {},
  onSaveIngredients,
  onRefresh,
  onRefreshQuery,
  onPickRecipe,
  onMakeAvg,
  onChangeAvg,
  onShuffleAvg,
  onBackToRecipe,
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
  const [showIngredients, setShowIngredients] = useState(false);
  const changedIngredients = Object.keys(ingredientOverrides || {}).length;
  // Hand-replaced lines matter while cooking (you bought something else than
  // the recipe says), so they're listed on the card itself. Lines that were
  // only left off the list (already at home) don't change the cooking.
  const replacedIngredients = recipe && !avg
    ? Object.entries(ingredientOverrides || {}).filter(([, replacement]) => replacement)
    : [];

  // A pinned or cooked dish is deliberately "done": swapping it needs an
  // explicit unpin first. (Freezing the week locks swaps for every day.)
  const swapLocked = frozen || pinned || cooked;
  // A day is either a recipe or a simple AVG (potato/vegetable/meat) meal.
  const hasMeal = !!(recipe || avg);
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
          {hasMeal && onToggleCooked && (
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
          {hasMeal && onToggleSkipShopping && (
            <button
              className={skipShopping ? "icon-button active" : "icon-button"}
              onClick={onToggleSkipShopping}
              title={skipShopping ? t("day.unskipShopping") : t("day.skipShopping")}
              aria-label={skipShopping ? t("day.unskipShopping") : t("day.skipShopping")}
            >
              🛒
            </button>
          )}
          {recipe && !avg && onSaveIngredients && (
            <button
              className={changedIngredients ? "icon-button active" : "icon-button"}
              onClick={() => setShowIngredients(true)}
              disabled={skipShopping}
              title={skipShopping ? t("day.skippedBadge") : t("day.editIngredients")}
              aria-label={t("day.editIngredients")}
            >
              📝
            </button>
          )}
          {hasMeal && onTogglePinned && (
            <button
              className={pinned ? "icon-button active" : "icon-button"}
              onClick={onTogglePinned}
              title={pinned ? t("day.unpin") : t("day.pin")}
              aria-label={pinned ? t("day.unpin") : t("day.pin")}
            >
              📌
            </button>
          )}
          {onMakeAvg && (
            <button
              className={avg ? "icon-button active" : "icon-button"}
              onClick={avg ? onBackToRecipe : onMakeAvg}
              disabled={refreshing || swapLocked}
              title={swapLocked ? swapLockedTitle : avg ? t("avg.backToRecipe") : t("avg.make")}
              aria-label={avg ? t("avg.backToRecipe") : t("avg.make")}
            >
              🥔
            </button>
          )}
          {onPickRecipe && !avg && (
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
            onClick={avg ? onShuffleAvg : onRefresh}
            disabled={refreshing || swapLocked}
            title={swapLocked ? swapLockedTitle : avg ? t("avg.shuffle") : t("day.reroll")}
            aria-label={avg ? t("avg.shuffle") : t("day.reroll")}
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

      {(cooked || skipShopping || (recipe && !avg && changedIngredients > 0)) && hasMeal && (
        <div className="day-card-status">
          {cooked && <span className="status-badge">✓ {t("day.cookedBadge")}</span>}
          {skipShopping && <span className="status-badge">🛒✕ {t("day.skippedBadge")}</span>}
          {!skipShopping && recipe && !avg && changedIngredients > 0 && (
            <button
              type="button"
              className="status-badge status-badge-button"
              onClick={() => setShowIngredients(true)}
            >
              📝 {t("day.ingredientsChangedBadge", { count: changedIngredients })}
            </button>
          )}
        </div>
      )}

      {avg ? (
        <div className="avg-card-body">
          <span className="dish-type-badge">{t("avg.badge")}</span>
          <AvgPicker
            avg={avg}
            options={avgOptions}
            disabled={frozen || cooked}
            onChange={onChangeAvg}
          />
        </div>
      ) : recipe ? (
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
                <h3>{recipe.title}</h3>
                {recipe.total_time_minutes ? (
                  <span className="time-badge">{recipe.total_time_minutes} min</span>
                ) : null}
              </div>
            </a>
          )}
          {replacedIngredients.length > 0 && (
            <div className="day-card-replacements">
              <span className="day-card-replacements-title">✎ {t("day.replacedTitle")}</span>
              <ul>
                {replacedIngredients.map(([original, replacement]) => (
                  <li key={original}>
                    <s>{original}</s> → <strong>{replacement}</strong>
                  </li>
                ))}
              </ul>
            </div>
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

      {showDetail && recipe && <RecipeDetailModal
          recipe={recipe}
          overrides={avg ? {} : ingredientOverrides}
          onClose={() => setShowDetail(false)}
        />}
      {showIngredients && recipe && (
        <IngredientEditModal
          recipe={recipe}
          overrides={ingredientOverrides}
          onSave={onSaveIngredients}
          onClose={() => setShowIngredients(false)}
        />
      )}
    </div>
  );
}
