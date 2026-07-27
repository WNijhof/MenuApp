import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function PantryManager() {
  const [staples, setStaples] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [term, setTerm] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      setStaples(await api.getPantryStaples());
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
      await api.createPantryStaple(value);
      setTerm("");
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleDelete = async (staple) => {
    try {
      await api.deletePantryStaple(staple.id);
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  if (loading) return <p className="status-text">Basisproducten worden geladen…</p>;

  return (
    <div>
      <p className="help-text">
        Producten die je altijd in huis hebt (bv. <em>zout</em>, <em>olie</em>,{" "}
        <em>oregano</em>) verschijnen straks niet op de boodschappenlijst.
      </p>

      {error && <p className="error-text">{error}</p>}

      <form className="inline-form" onSubmit={handleAdd}>
        <input
          type="text"
          placeholder="bv. zout, olijfolie, peper"
          value={term}
          onChange={(e) => setTerm(e.target.value)}
        />
        <button type="submit">Toevoegen</button>
      </form>

      <ul className="exclusion-list">
        {staples.map((staple) => (
          <li key={staple.id}>
            <strong>{staple.term}</strong>
            <button onClick={() => handleDelete(staple)} className="danger">
              Verwijder
            </button>
          </li>
        ))}
        {staples.length === 0 && <li className="status-text">Nog geen basisproducten.</li>}
      </ul>
    </div>
  );
}
