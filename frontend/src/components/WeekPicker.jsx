import { useTranslation } from "../i18n.jsx";

function toMonday(dateStr) {
  const d = new Date(`${dateStr}T00:00:00`);
  const day = d.getDay(); // 0=Sunday .. 6=Saturday
  const diff = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + diff);
  // Build the ISO string from local date parts, not toISOString() (which
  // converts to UTC first): in UTC+ timezones, local midnight is still
  // "yesterday" in UTC, so toISOString() silently rolled every date back
  // by one day - a Monday picked here became Sunday, which resolves to
  // the *previous* week's Monday server-side.
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

const LOCALE_BY_LANG = { en: "en-GB", nl: "nl-NL" };

export default function WeekPicker({ weekStartDate, onChange }) {
  const { t, language } = useTranslation();
  const label = weekStartDate
    ? new Date(`${weekStartDate}T00:00:00`).toLocaleDateString(LOCALE_BY_LANG[language] || "en-GB", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : "";

  return (
    <div className="week-picker">
      <label>
        {t("weekPicker.label")}{" "}
        <input
          type="date"
          value={weekStartDate || ""}
          onChange={(e) => e.target.value && onChange(toMonday(e.target.value))}
        />
      </label>
      <button type="button" onClick={() => onChange(null)}>
        {t("weekPicker.thisWeek")}
      </button>
      {label && <span className="help-text">{t("weekPicker.mondayOf", { date: label })}</span>}
    </div>
  );
}
