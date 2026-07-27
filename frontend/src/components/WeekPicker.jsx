function toMonday(dateStr) {
  const d = new Date(`${dateStr}T00:00:00`);
  const day = d.getDay(); // 0=zondag .. 6=zaterdag
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

export default function WeekPicker({ weekStartDate, onChange }) {
  const label = weekStartDate
    ? new Date(`${weekStartDate}T00:00:00`).toLocaleDateString("nl-NL", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : "";

  return (
    <div className="week-picker">
      <label>
        Week van:{" "}
        <input
          type="date"
          value={weekStartDate || ""}
          onChange={(e) => e.target.value && onChange(toMonday(e.target.value))}
        />
      </label>
      <button type="button" onClick={() => onChange(null)}>
        Deze week
      </button>
      {label && <span className="help-text">(maandag {label})</span>}
    </div>
  );
}
