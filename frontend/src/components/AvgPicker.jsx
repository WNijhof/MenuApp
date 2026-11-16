import { useRef, useState } from "react";
import { useTranslation } from "../i18n.jsx";

const SWIPE_MIN_PX = 40;

// One swipeable row: shows the current option, ‹ › (or a swipe left/right)
// moves to the previous/next one, wrapping around at the ends.
function AvgRow({ label, options, value, onChange, disabled }) {
  const { language } = useTranslation();
  const [direction, setDirection] = useState(1);
  const touchStart = useRef(null);

  const index = Math.max(0, options.findIndex((o) => o.id === value));
  const current = options[index];

  const step = (delta) => {
    if (disabled || options.length < 2) return;
    setDirection(delta);
    onChange(options[(index + delta + options.length) % options.length].id);
  };

  const onTouchStart = (e) => {
    const touch = e.touches[0];
    touchStart.current = { x: touch.clientX, y: touch.clientY };
  };

  const onTouchEnd = (e) => {
    const start = touchStart.current;
    touchStart.current = null;
    if (!start) return;
    const touch = e.changedTouches[0];
    const dx = touch.clientX - start.x;
    const dy = touch.clientY - start.y;
    // Mostly-horizontal drags only, so scrolling the page never swaps a dish.
    if (Math.abs(dx) >= SWIPE_MIN_PX && Math.abs(dx) > Math.abs(dy) * 1.5) step(dx < 0 ? 1 : -1);
  };

  return (
    <div className="avg-row">
      <span className="avg-row-label">{label}</span>
      <div className="avg-row-picker">
        <button
          type="button"
          className="icon-button avg-arrow"
          onClick={() => step(-1)}
          disabled={disabled}
          aria-label="‹"
        >
          ‹
        </button>
        <div className="avg-row-swipe" onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}>
          <div
            key={current.id}
            className={direction > 0 ? "avg-option avg-slide-next" : "avg-option avg-slide-prev"}
          >
            <span className="avg-emoji" aria-hidden="true">
              {current.emoji}
            </span>
            <span className="avg-option-label">{current.label[language] || current.label.en}</span>
          </div>
        </div>
        <button
          type="button"
          className="icon-button avg-arrow"
          onClick={() => step(1)}
          disabled={disabled}
          aria-label="›"
        >
          ›
        </button>
      </div>
    </div>
  );
}

export default function AvgPicker({ avg, options, onChange, disabled = false }) {
  const { t } = useTranslation();
  if (!options) return <div className="day-card-empty">{t("common.busy")}</div>;

  return (
    <div className="avg-picker">
      <AvgRow
        label={t("avg.starch")}
        options={options.starch}
        value={avg.starch}
        disabled={disabled}
        onChange={(id) => onChange({ starch: id })}
      />
      <AvgRow
        label={t("avg.veg")}
        options={options.veg}
        value={avg.veg}
        disabled={disabled}
        onChange={(id) => onChange({ veg: id })}
      />
      <AvgRow
        label={t("avg.meat")}
        options={options.meat}
        value={avg.meat}
        disabled={disabled}
        onChange={(id) => onChange({ meat: id })}
      />
      <div className="avg-portions">
        <span>{t("avg.portions")}</span>
        <button
          type="button"
          className="icon-button"
          onClick={() => onChange({ portions: Math.max(1, avg.portions - 1) })}
          disabled={disabled || avg.portions <= 1}
          aria-label={t("avg.fewer")}
        >
          −
        </button>
        <strong>{avg.portions}</strong>
        <button
          type="button"
          className="icon-button"
          onClick={() => onChange({ portions: Math.min(12, avg.portions + 1) })}
          disabled={disabled || avg.portions >= 12}
          aria-label={t("avg.more")}
        >
          +
        </button>
      </div>
    </div>
  );
}
