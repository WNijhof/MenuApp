import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useTranslation } from "../i18n.jsx";
import DayCard from "./DayCard.jsx";
import LeftoverManager from "./LeftoverManager.jsx";
import WeekPicker from "./WeekPicker.jsx";

const DAYS_PER_WEEK = 7;

export default function WeekView({ weekStartDate, onWeekChange }) {
  const { t } = useTranslation();
  const [menu, setMenu] = useState(null);
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);
  const [refreshingDay, setRefreshingDay] = useState(null);
  const [freezing, setFreezing] = useState(false);
  const [error, setError] = useState(null);
  const [dayWarning, setDayWarning] = useState(null);
  const [counts, setCounts] = useState({ hoofdgerecht: 7, voorgerecht: 0, nagerecht: 0 });

  const load = async () => {
    setLoading(true);
    setError(null);
    setDayWarning(null);
    try {
      const current = await api.getCurrentMenu(weekStartDate);
      setMenu(current);
      onWeekChange(current.week_start_date);
      if (current.course_counts && Object.keys(current.course_counts).length > 0) {
        setCounts({
          hoofdgerecht: current.course_counts.hoofdgerecht || 0,
          voorgerecht: current.course_counts.voorgerecht || 0,
          nagerecht: current.course_counts.nagerecht || 0,
        });
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
  const visibleDays = (menu?.days || []).filter((d) => isFullWeek || d.recipe);

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
    } catch (e) {
      setError(e.message);
    } finally {
      setRegenerating(false);
    }
  };

  const handleRefreshDay = async (dayOfWeek, query) => {
    setRefreshingDay(dayOfWeek);
    setError(null);
    setDayWarning(null);
    try {
      const updatedDay = await api.refreshDay(dayOfWeek, menu?.week_start_date, query);
      setMenu((prev) => ({
        ...prev,
        days: prev.days.map((d) =>
          d.day_of_week === dayOfWeek ? updatedDay : d
        ),
      }));
      if (updatedDay.warning) setDayWarning(updatedDay.warning);
    } catch (e) {
      setError(e.message);
    } finally {
      setRefreshingDay(null);
    }
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

  const handleRateDay = async (dayOfWeek, recipe, rating) => {
    const newRating = recipe.rating === rating ? null : rating;
    try {
      const updated = await api.rateRecipe(recipe.id, newRating);
      setMenu((prev) => ({
        ...prev,
        days: prev.days.map((d) =>
          d.day_of_week === dayOfWeek ? { ...d, recipe: updated } : d
        ),
      }));
      // A newly-disliked recipe is now excluded from selection entirely -
      // swap it out of this week right away instead of leaving it showing.
      if (newRating === "dislike") {
        await handleRefreshDay(dayOfWeek);
      }
    } catch (e) {
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
            refreshing={refreshingDay === day.day_of_week}
            onRefresh={() => handleRefreshDay(day.day_of_week)}
            onRefreshQuery={(query) => handleRefreshDay(day.day_of_week, query)}
            onRate={(rating) => handleRateDay(day.day_of_week, day.recipe, rating)}
            showDayName={isFullWeek}
            frozen={isFrozen}
          />
        ))}
      </div>
    </div>
  );
}
