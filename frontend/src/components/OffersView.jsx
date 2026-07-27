import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useTranslation } from "../i18n.jsx";

const STORE_LABELS = { aldi: "Aldi", jumbo: "Jumbo", lidl: "Lidl" };

export default function OffersView() {
  const { t } = useTranslation();
  const [offers, setOffers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState(null);
  const [storeFilter, setStoreFilter] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      setOffers(await api.getOffers());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    setError(null);
    try {
      await api.syncOffers();
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setSyncing(false);
    }
  };

  if (loading) return <p className="status-text">{t("offers.loading")}</p>;

  const visibleOffers = storeFilter ? offers.filter((o) => o.store === storeFilter) : offers;

  return (
    <div>
      <p className="help-text">{t("offers.help")}</p>

      {error && <p className="error-text">{error}</p>}

      <div className="toolbar">
        <button onClick={handleSync} disabled={syncing}>
          {syncing ? t("common.busy") : t("offers.sync")}
        </button>
        <label>
          {" "}{t("offers.storeLabel")}{" "}
          <select value={storeFilter} onChange={(e) => setStoreFilter(e.target.value)}>
            <option value="">{t("offers.allStores")}</option>
            {Object.entries(STORE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <p className="status-text">{t("offers.count", { count: visibleOffers.length })}</p>

      <table className="data-table">
        <thead>
          <tr>
            <th>{t("offers.colProduct")}</th>
            <th>{t("offers.colStore")}</th>
            <th>{t("offers.colPrice")}</th>
            <th>{t("offers.colDiscount")}</th>
          </tr>
        </thead>
        <tbody>
          {visibleOffers.map((offer) => (
            <tr key={offer.id}>
              <td>{offer.name}</td>
              <td>{STORE_LABELS[offer.store] || offer.store}</td>
              <td>
                {offer.original_price ? (
                  <>
                    <span className="offer-strike">€{offer.original_price.toFixed(2)}</span>{" "}
                    €{offer.price.toFixed(2)}
                  </>
                ) : (
                  offer.price != null && `€${offer.price.toFixed(2)}`
                )}
              </td>
              <td>{offer.discount_label}</td>
            </tr>
          ))}
          {visibleOffers.length === 0 && (
            <tr>
              <td colSpan={4} className="status-text">
                {t("offers.empty")}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
