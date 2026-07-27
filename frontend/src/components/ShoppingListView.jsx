import { useEffect, useState } from "react";
import { api } from "../api.js";
import WeekPicker from "./WeekPicker.jsx";

export default function ShoppingListView({ weekStartDate, onWeekChange }) {
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
      setError("Kopiëren naar klembord mislukt: " + e.message);
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

  if (loading) return <p className="status-text">Boodschappenlijst wordt geladen…</p>;

  return (
    <div>
      <WeekPicker weekStartDate={resolvedWeek} onChange={onWeekChange} />

      <p className="help-text">
        Alle ingrediënten van het weekmenu, min je basisproducten, plus wat je er zelf aan
        toevoegt. Plak het tekstblok in Todoist's snel-toevoegen venster — elke regel wordt
        een eigen taak.
      </p>

      {error && <p className="error-text">{error}</p>}

      <form className="inline-form" onSubmit={handleAdd}>
        <input
          type="text"
          placeholder="bv. wc-papier, eieren 6-pack"
          value={newItem}
          onChange={(e) => setNewItem(e.target.value)}
        />
        <button type="submit">Toevoegen</button>
      </form>

      {frequent.length > 0 && (
        <div className="frequent-items">
          <span className="help-text small">Veelgebruikt:</span>
          {frequent.map((f) => (
            <span key={f.id} className="frequent-chip">
              <button type="button" onClick={() => handleQuickAdd(f.term)}>
                {f.term}
              </button>
              <button
                type="button"
                className="frequent-chip-remove"
                onClick={() => handleForgetFavorite(f.id)}
                title="Niet meer onthouden"
                aria-label="Niet meer onthouden"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      <div className="toolbar">
        <button onClick={handleCopy} disabled={items.length === 0}>
          {copied ? "Gekopieerd!" : "Kopieer naar klembord"}
        </button>
      </div>

      {items.length === 0 ? (
        <p className="status-text">Nog geen boodschappen voor deze week.</p>
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
                    title="Verwijderen"
                    aria-label="Verwijderen"
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
