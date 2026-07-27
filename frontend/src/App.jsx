import { useEffect, useState } from "react";
import { api } from "./api.js";
import { applyTheme } from "./theme.js";
import { DEFAULT_LANGUAGE, LanguageProvider, useTranslation } from "./i18n.jsx";
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

function AppShell() {
  const { t } = useTranslation();
  const [tab, setTab] = useState("week");
  // Shared between Weekmenu and Boodschappenlijst so picking a week in one
  // tab carries over to the other. null = "the actual current week".
  const [weekStartDate, setWeekStartDate] = useState(null);

  const TABS = [
    { key: "week", label: t("tabs.week") },
    { key: "shopping-list", label: t("tabs.shoppingList") },
    { key: "offers", label: t("tabs.offers") },
    { key: "history", label: t("tabs.history") },
    { key: "sources", label: t("tabs.sources") },
    { key: "exclusions", label: t("tabs.exclusions") },
    { key: "pantry", label: t("tabs.pantry") },
    { key: "recipes", label: t("tabs.recipes") },
    { key: "niet-lekker", label: t("tabs.disliked") },
    { key: "settings", label: t("tabs.settings") },
  ];

  return (
    <div className="app">
      <header className="app-header">
        <h1>{t("app.title")}</h1>
        <nav className="tabs">
          {TABS.map((tabDef) => (
            <button
              key={tabDef.key}
              className={tab === tabDef.key ? "tab active" : "tab"}
              onClick={() => setTab(tabDef.key)}
            >
              {tabDef.label}
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

export default function App() {
  const [language, setLanguage] = useState(DEFAULT_LANGUAGE);

  useEffect(() => {
    api.getSettings().then((settings) => {
      applyTheme(settings);
      if (settings.language) setLanguage(settings.language);
    }).catch(() => {});
  }, []);

  return (
    <LanguageProvider initialLanguage={language}>
      <AppShell />
    </LanguageProvider>
  );
}
