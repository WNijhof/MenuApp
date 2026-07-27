import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function LeftoverManager() {
  const [leftovers, setLeftovers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [term, setTerm] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      setLeftovers(await api.getLeftovers());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleAdd = async (e) => {
    e.preventDefault();
    const value = term.trim();
    if (!value) return;
    setError(null);
    try {
      await api.createLeftover(value);
      setTerm("");
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleDelete = async (leftover) => {
    try {
      await api.deleteLeftover(leftover.id);
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="leftover-manager">
      <p className="help-text">
        Restjes in de koelkast? Recepten die deze bevatten krijgen voorrang bij het
        genereren. De lijst wordt na het genereren automatisch geleegd.
      </p>

      {error && <p className="error-text">{error}</p>}

      <form className="inline-form" onSubmit={handleAdd}>
        <input
          type="text"
          placeholder="bv. halve courgette, restje kip"
          value={term}
          onChange={(e) => setTerm(e.target.value)}
        />
        <button type="submit">Toevoegen</button>
      </form>

      {!loading && (
        <ul className="exclusion-list">
          {leftovers.map((leftover) => (
            <li key={leftover.id}>
              <strong>{leftover.term}</strong>
              <button onClick={() => handleDelete(leftover)} className="danger">
                Verwijder
              </button>
            </li>
          ))}
          {leftovers.length === 0 && <li className="status-text">Geen restjes opgegeven.</li>}
        </ul>
      )}
    </div>
  );
}
