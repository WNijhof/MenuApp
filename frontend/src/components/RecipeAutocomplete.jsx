import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { dishTypeLabel } from "../dishTypes.js";
import { useTranslation } from "../i18n.jsx";

const DEBOUNCE_MS = 120;

// Type-ahead over the recipe database: suggestions appear (as an expanding
// list) while typing. Picking one calls onPick(suggestion); pressing Enter
// without a highlighted suggestion calls onSubmitText(text) so the old
// free-text "search by keyword" swap still works.
export default function RecipeAutocomplete({ course, onPick, onSubmitText, disabled }) {
  const { t, language } = useTranslation();
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState(null); // null = nothing searched yet
  const [highlight, setHighlight] = useState(-1);
  const requestSeq = useRef(0);

  useEffect(() => {
    const text = query.trim();
    if (!text) {
      setSuggestions(null);
      setHighlight(-1);
      return undefined;
    }
    const timer = setTimeout(async () => {
      const seq = ++requestSeq.current;
      try {
        const results = await api.searchRecipes(text, course);
        // Ignore answers to queries that have since been typed over.
        if (seq === requestSeq.current) {
          setSuggestions(results);
          setHighlight(-1);
        }
      } catch {
        if (seq === requestSeq.current) setSuggestions([]);
      }
    }, DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [query, course]);

  const pick = (suggestion) => {
    setQuery("");
    setSuggestions(null);
    onPick(suggestion);
  };

  const handleKeyDown = (e) => {
    const count = suggestions?.length || 0;
    if (e.key === "ArrowDown" && count) {
      e.preventDefault();
      setHighlight((h) => (h + 1) % count);
    } else if (e.key === "ArrowUp" && count) {
      e.preventDefault();
      setHighlight((h) => (h <= 0 ? count - 1 : h - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (highlight >= 0 && suggestions[highlight]) {
        pick(suggestions[highlight]);
      } else if (query.trim()) {
        const text = query.trim();
        setQuery("");
        setSuggestions(null);
        onSubmitText(text);
      }
    } else if (e.key === "Escape") {
      setSuggestions(null);
    }
  };

  return (
    <div className="recipe-autocomplete">
      <input
        type="text"
        autoFocus
        disabled={disabled}
        placeholder={t("day.searchPlaceholder")}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        role="combobox"
        aria-expanded={!!suggestions?.length}
        aria-autocomplete="list"
      />
      {suggestions && suggestions.length > 0 && (
        <ul className="recipe-autocomplete-list" role="listbox">
          {suggestions.map((s, i) => (
            <li
              key={s.id}
              role="option"
              aria-selected={i === highlight}
              className={i === highlight ? "highlighted" : ""}
              // mousedown, not click: fires before the input loses focus
              onMouseDown={(e) => {
                e.preventDefault();
                pick(s);
              }}
              onMouseEnter={() => setHighlight(i)}
            >
              <span className="recipe-autocomplete-title">{s.title}</span>
              <span className="recipe-autocomplete-type">{dishTypeLabel(s.dish_type, language)}</span>
            </li>
          ))}
        </ul>
      )}
      {suggestions && suggestions.length === 0 && (
        <p className="recipe-autocomplete-empty">{t("day.searchNoResults")}</p>
      )}
      {!suggestions && <p className="recipe-autocomplete-empty">{t("day.searchHint")}</p>}
    </div>
  );
}
