import { useEffect, useRef, useState } from "react";
import { api, thumbUrl } from "../api.js";
import { useTranslation } from "../i18n.jsx";
import DayCard from "./DayCard.jsx";
import LeftoverManager from "./LeftoverManager.jsx";
import WeekPicker from "./WeekPicker.jsx";

const DAYS_PER_WEEK = 7;
const DEFAULT_COUNTS = { hoofdgerecht: 5, voorgerecht: 0, nagerecht: 0 };

export default function WeekView({ weekStartDate, onWeekChange }) {
  const { t } = useTranslation();
  const [menu, setMenu] = useState(null);
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);
  const [refreshingDay, setRefreshingDay] = useState(null);
  const [freezing, setFreezing] = useState(false);
  const [error, setError] = useState(null);
  const [dayWarning, setDayWarning] = useState(null);
  const [counts, setCounts] = useState(DEFAULT_COUNTS);
  const [avgOptions, setAvgOptions] = useState(null); // potato/vegetable/meat choices for AVG days
  const [epoch, setEpoch] = useState(0); // bumped whenever a menu is (re)loaded or regenerated

  // Swipe-style swapping: one spare replacement is kept ready per day
  // (fetched in the background, its photo already preloaded), so ↻ / 👎
  // can show the new dish immediately and save it in the background,
  // instead of waiting on a round trip per click.
  const candidates = useRef({}); // dayOfWeek -> { recipe, warning }
  const prefetchRun = useRef(0); // bumped to abandon prefetching for a stale week/menu
  const menuRef = useRef(null);
  const persistChain = useRef(Promise.resolve()); // saves run in click order

  const load = async () => {
    setLoading(true);
    setError(null);
    setDayWarning(null);
    try {
      const current = await api.getCurrentMenu(weekStartDate);
      setMenu(current);
      setEpoch((n) => n + 1);
      onWeekChange(current.week_start_date);
      if (current.course_counts && Object.keys(current.course_counts).length > 0) {
        setCounts({
          hoofdgerecht: current.course_counts.hoofdgerecht || 0,
          voorgerecht: current.course_counts.voorgerecht || 0,
          nagerecht: current.course_counts.nagerecht || 0,
        });
      } else {
        // No menu generated for this week yet: fall back to the configured defaults.
        api
          .getSettings()
          .then((s) =>
            setCounts({
              hoofdgerecht: s.default_hoofdgerecht,
              voorgerecht: s.default_voorgerecht,
              nagerecht: s.default_nagerecht,
            })
          )
          .catch(() => {});
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [weekStartDate]);

  useEffect(() => {
    api.getAvgOptions().then(setAvgOptions).catch(() => {});
  }, []);

  menuRef.current = menu;

  const countsTotal = counts.hoofdgerecht + counts.voorgerecht + counts.nagerecht;
  const countsValid = countsTotal <= DAYS_PER_WEEK;

  const menuTotal = Object.values(menu?.course_counts || {}).reduce((a, b) => a + b, 0);
  const isFullWeek = menuTotal === DAYS_PER_WEEK;
  const isFrozen = !!menu?.frozen;
  // course_counts is only non-empty once a menu has actually been generated
  // and persisted - freezing an ephemeral, not-yet-generated week makes no
  // sense (there's nothing in the database yet to protect).
  const hasMenu = menuTotal > 0;
  // With fewer than 7 dishes requested, the open days aren't tied to real
  // weekdays (they're randomly interleaved server-side) - showing them as
  // e.g. "Thursday: no recipe" would be misleading, so just don't render
  // placeholder cards or day names in that case.
  const visibleDays = (menu?.days || []).filter((d) => isFullWeek || d.recipe || d.avg);

  // --- spare candidates ---------------------------------------------------

  const preload = (recipe) => {
    if (recipe?.image_url) new Image().src = thumbUrl(recipe);
  };

  const fillCandidate = async (dayOfWeek, run) => {
    const current = menuRef.current;
    if (!current || !hasMenuOf(current)) return;
    const held = Object.values(candidates.current).map((c) => c.recipe?.id).filter(Boolean);
    try {
      const result = await api.getDayCandidate(dayOfWeek, current.week_start_date, held);
      if (run !== prefetchRun.current || !result.recipe) return;
      candidates.current[dayOfWeek] = { recipe: result.recipe, warning: result.warning };
      preload(result.recipe);
    } catch {
      // Best effort - without a spare the swap just asks the server.
    }
  };

  const hasMenuOf = (m) => Object.values(m.course_counts || {}).reduce((a, b) => a + b, 0) > 0;

  const prefetchAll = async (run) => {
    const current = menuRef.current;
    if (!current || !hasMenuOf(current) || current.frozen) return;
    for (const day of current.days) {
      if (run !== prefetchRun.current) return;
      if (day.recipe && !day.pinned && !day.cooked && !candidates.current[day.day_of_week]) {
        // eslint-disable-next-line no-await-in-loop
        await fillCandidate(day.day_of_week, run);
      }
    }
  };

  // (Re)start prefetching whenever a different week/menu was loaded or generated.
  const weekKey = menu ? `${menu.week_start_date}|${epoch}|${menu.frozen}` : null;
  useEffect(() => {
    candidates.current = {};
    const run = ++prefetchRun.current;
    if (weekKey) prefetchAll(run);
    return () => {
      prefetchRun.current += 1;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [weekKey]);

  // --- actions ------------------------------------------------------------

  const handleCountChange = (course, value) => {
    const n = Math.max(0, parseInt(value, 10) || 0);
    setCounts((prev) => ({ ...prev, [course]: n }));
  };

  const handleRegenerate = async () => {
    if (!countsValid) return;
    setRegenerating(true);
    setError(null);
    setDayWarning(null);
    try {
      const updated = await api.generateMenu(counts, menu?.week_start_date || weekStartDate);
      setMenu(updated);
      setEpoch((n) => n + 1);
      // Pinned/cooked dishes are kept server-side, so the effective counts can be higher.
      if (updated.course_counts) {
        setCounts({
          hoofdgerecht: updated.course_counts.hoofdgerecht || 0,
          voorgerecht: updated.course_counts.voorgerecht || 0,
          nagerecht: updated.course_counts.nagerecht || 0,
        });
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setRegenerating(false);
    }
  };

  const replaceDay = (dayOfWeek, patch) =>
    setMenu((prev) => ({
      ...prev,
      days: prev.days.map((d) => (d.day_of_week === dayOfWeek ? { ...d, ...patch } : d)),
    }));

  // Server-side swap (used when no spare is ready, and for keyword search).
  const handleRefreshDay = async (dayOfWeek, query) => {
    setRefreshingDay(dayOfWeek);
    setError(null);
    setDayWarning(null);
    try {
      const updatedDay = await api.refreshDay(dayOfWeek, menu?.week_start_date, query);
      replaceDay(dayOfWeek, updatedDay);
      delete candidates.current[dayOfWeek];
      if (updatedDay.warning) setDayWarning(updatedDay.warning);
      fillCandidate(dayOfWeek, prefetchRun.current);
    } catch (e) {
      setError(e.message);
    } finally {
      setRefreshingDay(null);
    }
  };

  // Show `recipe` on the day right away, save it in the background.
  const applyRecipeToDay = (dayOfWeek, recipe, { dislikeOld = null, warning = null } = {}) => {
    const weekStart = menuRef.current.week_start_date;
    replaceDay(dayOfWeek, { recipe, avg: null, pinned: false, cooked: false, skip_shopping: false });
    setDayWarning(warning);
    delete candidates.current[dayOfWeek];
    // A held spare that equals the dish just put on a day would now duplicate it.
    for (const [day, spare] of Object.entries(candidates.current)) {
      if (spare.recipe?.id === recipe.id) delete candidates.current[day];
    }

    persistChain.current = persistChain.current
      .then(async () => {
        if (dislikeOld) await api.rateRecipe(dislikeOld.id, "dislike");
        await api.setDayRecipe(dayOfWeek, weekStart, recipe.id);
      })
      .catch((e) => {
        setError(e.message);
        load(); // the screen got ahead of the database - resync
      })
      .then(() => {
        const run = prefetchRun.current;
        for (const day of [dayOfWeek, ...Object.keys(candidates.current).map(Number)]) {
          if (!candidates.current[day]) fillCandidate(day, run);
        }
      });
  };

  const swapWithSpare = (dayOfWeek, options = {}) => {
    const spare = candidates.current[dayOfWeek];
    const used = new Set((menuRef.current?.days || []).map((d) => d.recipe?.id));
    if (spare?.recipe && !used.has(spare.recipe.id)) {
      applyRecipeToDay(dayOfWeek, spare.recipe, { ...options, warning: spare.warning });
      return true;
    }
    return false;
  };

  const handleReroll = (dayOfWeek) => {
    if (!swapWithSpare(dayOfWeek)) handleRefreshDay(dayOfWeek);
  };

  const handlePickRecipe = async (dayOfWeek, recipeId) => {
    setRefreshingDay(dayOfWeek);
    setError(null);
    setDayWarning(null);
    try {
      const updatedDay = await api.setDayRecipe(dayOfWeek, menu?.week_start_date, recipeId);
      replaceDay(dayOfWeek, updatedDay);
      delete candidates.current[dayOfWeek];
      fillCandidate(dayOfWeek, prefetchRun.current);
    } catch (e) {
      setError(e.message);
    } finally {
      setRefreshingDay(null);
    }
  };

  // --- AVG days (Aardappel / Groente / Vlees) -------------------------------

  const pickRandom = (list) => list[Math.floor(Math.random() * list.length)].id;

  // Show the new choice right away, save it in the background (in click order,
  // like recipe swaps) so swiping through options never waits on the server.
  const saveAvg = (dayOfWeek, avg) => {
    const weekStart = menuRef.current.week_start_date;
    persistChain.current = persistChain.current
      .then(() => api.setDayAvg(dayOfWeek, weekStart, avg))
      .catch((e) => {
        setError(e.message);
        load(); // the screen got ahead of the database - resync
      });
  };

  const handleMakeAvg = (day) => {
    if (!avgOptions) return;
    const avg = {
      starch: pickRandom(avgOptions.starch),
      veg: pickRandom(avgOptions.veg),
      meat: pickRandom(avgOptions.meat),
      portions: 2,
    };
    setDayWarning(null);
    delete candidates.current[day.day_of_week];
    replaceDay(day.day_of_week, { recipe: null, avg, pinned: false, cooked: false, skip_shopping: false });
    saveAvg(day.day_of_week, avg);
  };

  const handleChangeAvg = (dayOfWeek, patch) => {
    const current = menuRef.current.days.find((d) => d.day_of_week === dayOfWeek)?.avg;
    if (!current) return;
    const avg = { ...current, ...patch };
    replaceDay(dayOfWeek, { avg });
    saveAvg(dayOfWeek, avg);
  };

  const handleShuffleAvg = (dayOfWeek) => {
    if (!avgOptions) return;
    handleChangeAvg(dayOfWeek, {
      starch: pickRandom(avgOptions.starch),
      veg: pickRandom(avgOptions.veg),
      meat: pickRandom(avgOptions.meat),
    });
  };

  const handleToggleFrozen = async () => {
    setFreezing(true);
    setError(null);
    try {
      const updated = await api.setWeekFrozen(menu.week_start_date, !menu.frozen);
      setMenu(updated);
    } catch (e) {
      setError(e.message);
    } finally {
      setFreezing(false);
    }
  };

  const handleToggleFlag = async (day, flag) => {
    const next = !day[flag];
    replaceDay(day.day_of_week, { [flag]: next }); // optimistic
    try {
      const updated = await api.updateDayFlags(day.day_of_week, menu.week_start_date, { [flag]: next });
      replaceDay(day.day_of_week, {
        pinned: updated.pinned,
        cooked: updated.cooked,
        skip_shopping: updated.skip_shopping,
      });
      // Pinned/cooked dishes don't get swapped, so they don't need a spare.
      if (next && (flag === "pinned" || flag === "cooked")) delete candidates.current[day.day_of_week];
      if (!next && (flag === "pinned" || flag === "cooked")) fillCandidate(day.day_of_week, prefetchRun.current);
    } catch (e) {
      replaceDay(day.day_of_week, { [flag]: !next });
      setError(e.message);
    }
  };

  const handleRateDay = async (day, rating) => {
    const recipe = day.recipe;
    const newRating = recipe.rating === rating ? null : rating;
    const dayOfWeek = day.day_of_week;

    // A newly-disliked recipe is excluded from selection entirely - swap it
    // out of this week right away (instantly, if a spare is ready) instead
    // of leaving it showing. Cooked dishes stay: they were already eaten.
    if (newRating === "dislike" && !day.cooked && !isFrozen) {
      if (swapWithSpare(dayOfWeek, { dislikeOld: recipe })) return;
    }

    replaceDay(dayOfWeek, { recipe: { ...recipe, rating: newRating } });
    try {
      const updated = await api.rateRecipe(recipe.id, newRating);
      replaceDay(dayOfWeek, { recipe: updated });
      if (newRating === "dislike" && !day.cooked && !isFrozen) {
        await handleRefreshDay(dayOfWeek);
      }
    } catch (e) {
      replaceDay(dayOfWeek, { recipe });
      setError(e.message);
    }
  };

  if (loading) return <p className="status-text">{t("week.loading")}</p>;

  return (
    <div>
      <WeekPicker weekStartDate={menu?.week_start_date || weekStartDate} onChange={onWeekChange} />

      <LeftoverManager />

      <div className="toolbar course-count-toolbar">
        <label>
          {t("course.mains")}:{" "}
          <input
            type="number"
            min="0"
            max={DAYS_PER_WEEK}
            value={counts.hoofdgerecht}
            disabled={isFrozen}
            onChange={(e) => handleCountChange("hoofdgerecht", e.target.value)}
          />
        </label>
        <label>
          {t("course.starters")}:{" "}
          <input
            type="number"
            min="0"
            max={DAYS_PER_WEEK}
            value={counts.voorgerecht}
            disabled={isFrozen}
            onChange={(e) => handleCountChange("voorgerecht", e.target.value)}
          />
        </label>
        <label>
          {t("course.desserts")}:{" "}
          <input
            type="number"
            min="0"
            max={DAYS_PER_WEEK}
            value={counts.nagerecht}
            disabled={isFrozen}
            onChange={(e) => handleCountChange("nagerecht", e.target.value)}
          />
        </label>
        <button onClick={handleRegenerate} disabled={regenerating || !countsValid || isFrozen}>
          {regenerating ? t("common.busy") : t("week.generate")}
        </button>
        {hasMenu && (
          <button
            className={isFrozen ? "active" : ""}
            onClick={handleToggleFrozen}
            disabled={freezing}
            title={isFrozen ? t("week.unfreezeTitle") : t("week.freezeTitle")}
          >
            {freezing ? t("common.busy") : isFrozen ? t("week.unfreeze") : t("week.freeze")}
          </button>
        )}
      </div>
      {!countsValid && (
        <p className="error-text">{t("course.countTooHigh", { max: DAYS_PER_WEEK, count: countsTotal })}</p>
      )}
      {hasMenu && !isFrozen && <p className="help-text small">{t("week.pinHelp")}</p>}
      {hasMenu && !isFrozen && <p className="help-text small">{t("avg.help")}</p>}
      {isFrozen && <p className="status-text">{t("week.frozenNotice")}</p>}

      {error && <p className="error-text">{error}</p>}
      {menu?.warnings?.map((w, i) => (
        <p key={i} className="warning-text">
          {w}
        </p>
      ))}
      {dayWarning && <p className="warning-text">{dayWarning}</p>}

      <div className="week-grid">
        {visibleDays.map((day) => (
          <DayCard
            key={day.day_of_week}
            dayOfWeek={day.day_of_week}
            recipe={day.recipe}
            avg={day.avg}
            avgOptions={avgOptions}
            pinned={!!day.pinned}
            cooked={!!day.cooked}
            skipShopping={!!day.skip_shopping}
            refreshing={refreshingDay === day.day_of_week}
            onRefresh={() => handleReroll(day.day_of_week)}
            onRefreshQuery={(query) => handleRefreshDay(day.day_of_week, query)}
            onPickRecipe={(recipeId) => handlePickRecipe(day.day_of_week, recipeId)}
            onMakeAvg={hasMenu && avgOptions ? () => handleMakeAvg(day) : undefined}
            onChangeAvg={(patch) => handleChangeAvg(day.day_of_week, patch)}
            onShuffleAvg={() => handleShuffleAvg(day.day_of_week)}
            onBackToRecipe={() => handleRefreshDay(day.day_of_week)}
            onTogglePinned={() => handleToggleFlag(day, "pinned")}
            onToggleCooked={() => handleToggleFlag(day, "cooked")}
            onToggleSkipShopping={() => handleToggleFlag(day, "skip_shopping")}
            onRate={(rating) => handleRateDay(day, rating)}
            showDayName={isFullWeek}
            frozen={isFrozen}
          />
        ))}
      </div>
    </div>
  );
}
