import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useTranslation } from "../i18n.jsx";
import WeekPicker from "./WeekPicker.jsx";

export default function ShoppingListView({ weekStartDate, onWeekChange }) {
  const { t } = useTranslation();
  const [items, setItems] = useState([]);
  const [resolvedWeek, setResolvedWeek] = useState(weekStartDate);
  const [frequent, setFrequent] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [newItem, setNewItem] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const [list, freq] = await Promise.all([
        api.getShoppingList(weekStartDate),
        api.getFrequentItems(),
      ]);
      setItems(list.items);
      setResolvedWeek(list.week_start_date);
      onWeekChange(list.week_start_date);
      setFrequent(freq);
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

  const text = items.map((i) => i.text).join("\n");

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      setError(t("shopping.copyFailed", { error: e.message }));
    }
  };

  const handleAdd = async (e) => {
    e.preventDefault();
    const value = newItem.trim();
    if (!value) return;
    setError(null);
    try {
      await api.addShoppingListItem(value);
      setNewItem("");
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleQuickAdd = async (term) => {
    setError(null);
    try {
      await api.addShoppingListItem(term);
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleRemoveExtra = async (extraId) => {
    try {
      await api.deleteShoppingListExtra(extraId);
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleForgetFavorite = async (id) => {
    try {
      await api.deleteFrequentItem(id);
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  if (loading) return <p className="status-text">{t("shopping.loading")}</p>;

  return (
    <div>
      <WeekPicker weekStartDate={resolvedWeek} onChange={onWeekChange} />

      <p className="help-text">{t("shopping.help")}</p>

      {error && <p className="error-text">{error}</p>}

      <form className="inline-form" onSubmit={handleAdd}>
        <input
          type="text"
          placeholder={t("shopping.placeholder")}
          value={newItem}
          onChange={(e) => setNewItem(e.target.value)}
        />
        <button type="submit">{t("common.add")}</button>
      </form>

      {frequent.length > 0 && (
        <div className="frequent-items">
          <span className="help-text small">{t("shopping.frequentLabel")}</span>
          {frequent.map((f) => (
            <span key={f.id} className="frequent-chip">
              <button type="button" onClick={() => handleQuickAdd(f.term)}>
                {f.term}
              </button>
              <button
                type="button"
                className="frequent-chip-remove"
                onClick={() => handleForgetFavorite(f.id)}
                title={t("shopping.forgetTitle")}
                aria-label={t("shopping.forgetTitle")}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      <div className="toolbar">
        <button onClick={handleCopy} disabled={items.length === 0}>
          {copied ? t("shopping.copied") : t("shopping.copyButton")}
        </button>
      </div>

      {items.length === 0 ? (
        <p className="status-text">{t("shopping.empty")}</p>
      ) : (
        <>
          <ul className="shopping-list-items">
            {items.map((item, i) => (
              <li key={item.extra_id ?? `recipe-${i}`}>
                <span>{item.text}</span>
                {item.extra_id != null && (
                  <button
                    className="danger"
                    onClick={() => handleRemoveExtra(item.extra_id)}
                    title={t("common.removeTitle")}
                    aria-label={t("common.removeTitle")}
                  >
                    ×
                  </button>
                )}
              </li>
            ))}
          </ul>
          <textarea className="shopping-list-textarea" readOnly rows={Math.min(items.length + 1, 25)} value={text} />
        </>
      )}
    </div>
  );
}
