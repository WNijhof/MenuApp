import { useState } from "react";
import WeekView from "./components/WeekView.jsx";
import SourceManager from "./components/SourceManager.jsx";
import ExclusionManager from "./components/ExclusionManager.jsx";
import RecipeManager from "./components/RecipeManager.jsx";
import PantryManager from "./components/PantryManager.jsx";
import NietLekkerView from "./components/NietLekkerView.jsx";
import HistoryView from "./components/HistoryView.jsx";
import ShoppingListView from "./components/ShoppingListView.jsx";
import OffersView from "./components/OffersView.jsx";
import SettingsView from "./components/SettingsView.jsx";

const TABS = [
  { key: "week", label: "Weekmenu" },
  { key: "shopping-list", label: "Boodschappenlijst" },
  { key: "offers", label: "Aanbiedingen" },
  { key: "history", label: "Geschiedenis" },
  { key: "sources", label: "Bronnen" },
  { key: "exclusions", label: "Uitsluitingen" },
  { key: "pantry", label: "Basisproducten" },
  { key: "recipes", label: "Recepten" },
  { key: "niet-lekker", label: "Niet lekker" },
  { key: "settings", label: "Instellingen" },
];

export default function App() {
  const [tab, setTab] = useState("week");
  // Shared between Weekmenu and Boodschappenlijst so picking a week in one
  // tab carries over to the other. null = "the actual current week".
  const [weekStartDate, setWeekStartDate] = useState(null);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Weekmenu</h1>
        <nav className="tabs">
          {TABS.map((t) => (
            <button
              key={t.key}
              className={tab === t.key ? "tab active" : "tab"}
              onClick={() => setTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      <main>
        {tab === "week" && <WeekView weekStartDate={weekStartDate} onWeekChange={setWeekStartDate} />}
        {tab === "shopping-list" && (
          <ShoppingListView weekStartDate={weekStartDate} onWeekChange={setWeekStartDate} />
        )}
        {tab === "offers" && <OffersView />}
        {tab === "history" && <HistoryView />}
        {tab === "sources" && <SourceManager />}
        {tab === "exclusions" && <ExclusionManager />}
        {tab === "pantry" && <PantryManager />}
        {tab === "recipes" && <RecipeManager />}
        {tab === "niet-lekker" && <NietLekkerView />}
        {tab === "settings" && <SettingsView />}
      </main>
    </div>
  );
}
