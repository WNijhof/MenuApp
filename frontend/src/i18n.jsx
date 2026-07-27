import { createContext, useContext, useEffect, useMemo, useState } from "react";

export const SUPPORTED_LANGUAGES = ["en", "nl"];
export const DEFAULT_LANGUAGE = "en";

const translations = {
  en: {
    "app.title": "Weekmenu",

    "tabs.week": "Weekly menu",
    "tabs.shoppingList": "Shopping list",
    "tabs.offers": "Offers",
    "tabs.history": "History",
    "tabs.sources": "Sources",
    "tabs.exclusions": "Exclusions",
    "tabs.pantry": "Pantry staples",
    "tabs.recipes": "Recipes",
    "tabs.disliked": "Disliked",
    "tabs.settings": "Settings",

    "common.add": "Add",
    "common.delete": "Delete",
    "common.save": "Save",
    "common.saved": "Saved!",
    "common.busy": "Working…",
    "common.title": "Title",
    "common.dishType": "Type",
    "common.course": "Course",
    "common.removeTitle": "Remove",

    "course.mains": "Mains",
    "course.starters": "Starters",
    "course.desserts": "Desserts",
    "course.countTooHigh": "Number of dishes cannot exceed {max} (currently {count}).",

    "week.loading": "Loading weekly menu…",
    "week.generate": "Generate new week",
    "week.freeze": "Freeze week",
    "week.unfreeze": "❄️ Unfreeze week",
    "week.freezeTitle": "Freeze this week so nothing changes by accident (e.g. after doing the groceries)",
    "week.unfreezeTitle": "Unfreeze this week to allow changes again",
    "week.frozenNotice": "This week is frozen — the menu will no longer change. Unfreeze the week to make adjustments.",
    "week.frozenCannotDelete": "This week is frozen. Unfreeze it first to delete it.",
    "week.frozenBadgeTitle": "Frozen",

    "weekPicker.label": "Week of:",
    "weekPicker.thisWeek": "This week",
    "weekPicker.mondayOf": "(Monday {date})",

    "day.reroll": "Swap for a different recipe",
    "day.rerollFrozen": "Unfreeze the week to swap",
    "day.favorite": "Favorite",
    "day.dislike": "Not tasty",
    "day.noRecipe": "No recipe available",
    "day.monday": "Monday",
    "day.tuesday": "Tuesday",
    "day.wednesday": "Wednesday",
    "day.thursday": "Thursday",
    "day.friday": "Friday",
    "day.saturday": "Saturday",
    "day.sunday": "Sunday",

    "offer.badgeTitle": "Contains a product that's currently on offer",
    "offer.badgeText": "🏷️ offer",

    "history.help": "Previous weekly menus, for reuse inspiration.",
    "history.loading": "Loading history…",
    "history.empty": "No previous weeks yet.",
    "history.weekOf": "Week of {date}",
    "history.noRecipe": "no recipe",
    "history.confirmDelete": "Delete the weekly menu for {date}?",

    "leftovers.help": "Leftovers in the fridge? Recipes that use them get priority when generating. The list is automatically cleared after generating.",
    "leftovers.placeholder": "e.g. half a courgette, leftover chicken",
    "leftovers.empty": "No leftovers listed.",

    "disliked.loading": "Loading…",
    "disliked.help": "Recipes you've given a 👎 are no longer repeated in the weekly menu. Reset the rating to let a recipe back in.",
    "disliked.restore": "Restore",
    "disliked.empty": "No recipes marked \"not tasty\" yet.",

    "offers.loading": "Loading offers…",
    "offers.help": "Current offers at Aldi, Jumbo and Lidl. Recipes using one of these products get priority when generating the weekly menu.",
    "offers.sync": "Refresh offers",
    "offers.storeLabel": "Store:",
    "offers.allStores": "All stores",
    "offers.count": "{count} offers",
    "offers.colProduct": "Product",
    "offers.colStore": "Store",
    "offers.colPrice": "Price",
    "offers.colDiscount": "Discount",
    "offers.empty": "No offers fetched yet — click \"Refresh offers\".",

    "pantry.loading": "Loading pantry staples…",
    "pantry.helpPrefix": "Products you always have on hand (e.g.",
    "pantry.helpSuffix": ") won't show up on the shopping list.",
    "pantry.example1": "salt",
    "pantry.example2": "oil",
    "pantry.example3": "oregano",
    "pantry.placeholder": "e.g. salt, olive oil, pepper",
    "pantry.empty": "No pantry staples yet.",

    "recipes.loading": "Loading recipes…",
    "recipes.help": "Add a single recipe via a direct link to the recipe page.",
    "recipes.urlPlaceholder": "https://example.com/recipes/my-recipe",
    "recipes.courseFilterLabel": "Course:",
    "recipes.allCourses": "All courses",
    "recipes.count": "{count} recipes in the database",
    "recipes.rating": "Rating",

    "shopping.loading": "Loading shopping list…",
    "shopping.help": "All ingredients from the weekly menu, minus your pantry staples, plus anything you add yourself. Paste the text block into Todoist's quick-add window — each line becomes its own task.",
    "shopping.placeholder": "e.g. toilet paper, 6-pack of eggs",
    "shopping.frequentLabel": "Frequently used:",
    "shopping.forgetTitle": "Stop remembering this",
    "shopping.copied": "Copied!",
    "shopping.copyButton": "Copy to clipboard",
    "shopping.copyFailed": "Failed to copy to clipboard: {error}",
    "shopping.empty": "No shopping items for this week yet.",

    "sources.loading": "Loading sources…",
    "sources.syncAll": "Sync all sources",
    "sources.namePlaceholder": "Name (e.g. My favorite site)",
    "sources.urlPlaceholder": "https://example.com/recipes",
    "sources.addButton": "Add source",
    "sources.colName": "Name",
    "sources.colUrl": "URL",
    "sources.colEnabled": "Enabled",
    "sources.colLastSync": "Last synced",
    "sources.colRecipeCount": "Recipes",
    "sources.never": "never",
    "sources.syncOne": "Sync",
    "sources.confirmDelete": "Delete source \"{name}\" and its recipes?",
    "sources.lastSyncHeading": "Last sync",
    "sources.syncResultNew": "{count} new recipes",
    "sources.syncResultUpdated": ", {count} updated",
    "sources.syncResultPagesChecked": "({count} pages checked)",

    "exclusions.loading": "Loading exclusions…",
    "exclusions.helpPrefix": "Enter a category (e.g.",
    "exclusions.helpMiddle": ") to exclude all related ingredients (cod, salmon, ...), or type a single ingredient (e.g.",
    "exclusions.helpSuffix": ").",
    "exclusions.example1": "fish",
    "exclusions.example2": "nuts",
    "exclusions.example3": "pork",
    "exclusions.example4": "coriander",
    "exclusions.placeholder": "e.g. fish, nuts, coriander",
    "exclusions.addButton": "Exclude",
    "exclusions.alsoLabel": "Also:",
    "exclusions.empty": "No exclusions yet.",

    "settings.loading": "Loading settings…",
    "settings.courseCountsHelp": "Default number of dishes per course when you generate a new week. This is just the starting point — you can always adjust it per week on the Weekly menu tab.",
    "settings.colorsHeading": "Colors",
    "settings.colorsHelp": "Customize the app's background and accent color (buttons, links, tab highlight). This choice applies to everyone using the app, regardless of their device's light/dark mode.",
    "settings.backgroundColorLabel": "Background color:",
    "settings.accentColorLabel": "Accent color:",
    "settings.resetColors": "Default colors",
    "settings.languageHeading": "Language",
    "settings.languageHelp": "Choose the app's display language.",
    "settings.languageLabel": "Language:",
    "settings.languageEnglish": "English",
    "settings.languageDutch": "Nederlands",
  },
  nl: {
    "app.title": "Weekmenu",

    "tabs.week": "Weekmenu",
    "tabs.shoppingList": "Boodschappenlijst",
    "tabs.offers": "Aanbiedingen",
    "tabs.history": "Geschiedenis",
    "tabs.sources": "Bronnen",
    "tabs.exclusions": "Uitsluitingen",
    "tabs.pantry": "Basisproducten",
    "tabs.recipes": "Recepten",
    "tabs.disliked": "Niet lekker",
    "tabs.settings": "Instellingen",

    "common.add": "Toevoegen",
    "common.delete": "Verwijder",
    "common.save": "Opslaan",
    "common.saved": "Opgeslagen!",
    "common.busy": "Bezig…",
    "common.title": "Titel",
    "common.dishType": "Type",
    "common.course": "Gang",
    "common.removeTitle": "Verwijderen",

    "course.mains": "Hoofdgerechten",
    "course.starters": "Voorgerechten",
    "course.desserts": "Nagerechten",
    "course.countTooHigh": "Aantal gerechten kan niet meer dan {max} zijn (nu {count}).",

    "week.loading": "Weekmenu wordt geladen…",
    "week.generate": "Genereer nieuwe week",
    "week.freeze": "Bevries week",
    "week.unfreeze": "❄️ Ontdooi week",
    "week.freezeTitle": "Bevries deze week zodat er niets meer per ongeluk verandert (bijv. na het doen van de boodschappen)",
    "week.unfreezeTitle": "Ontdooi deze week om weer wijzigingen toe te staan",
    "week.frozenNotice": "Deze week is bevroren — het menu wordt niet meer gewijzigd. Ontdooi de week om aanpassingen te doen.",
    "week.frozenCannotDelete": "Deze week is bevroren. Ontdooi de week eerst om te verwijderen.",
    "week.frozenBadgeTitle": "Bevroren",

    "weekPicker.label": "Week van:",
    "weekPicker.thisWeek": "Deze week",
    "weekPicker.mondayOf": "(maandag {date})",

    "day.reroll": "Wissel voor een ander recept",
    "day.rerollFrozen": "Ontdooi de week om te wisselen",
    "day.favorite": "Favoriet",
    "day.dislike": "Niet lekker",
    "day.noRecipe": "Geen recept beschikbaar",
    "day.monday": "Maandag",
    "day.tuesday": "Dinsdag",
    "day.wednesday": "Woensdag",
    "day.thursday": "Donderdag",
    "day.friday": "Vrijdag",
    "day.saturday": "Zaterdag",
    "day.sunday": "Zondag",

    "offer.badgeTitle": "Bevat een product dat nu in de aanbieding is",
    "offer.badgeText": "🏷️ aanbieding",

    "history.help": "Eerdere weekmenu's, ter inspiratie voor hergebruik.",
    "history.loading": "Geschiedenis wordt geladen…",
    "history.empty": "Nog geen eerdere weken.",
    "history.weekOf": "Week van {date}",
    "history.noRecipe": "geen recept",
    "history.confirmDelete": "Weekmenu van {date} verwijderen?",

    "leftovers.help": "Restjes in de koelkast? Recepten die deze bevatten krijgen voorrang bij het genereren. De lijst wordt na het genereren automatisch geleegd.",
    "leftovers.placeholder": "bv. halve courgette, restje kip",
    "leftovers.empty": "Geen restjes opgegeven.",

    "disliked.loading": "Wordt geladen…",
    "disliked.help": "Recepten die je 👎 hebt gegeven worden niet meer herhaald in het weekmenu. Zet de waardering terug om een recept weer mee te laten doen.",
    "disliked.restore": "Terugzetten",
    "disliked.empty": "Nog geen recepten als \"niet lekker\" gemarkeerd.",

    "offers.loading": "Aanbiedingen worden geladen…",
    "offers.help": "Huidige aanbiedingen bij Aldi, Jumbo en Lidl. Recepten die een van deze producten gebruiken krijgen voorrang bij het genereren van het weekmenu.",
    "offers.sync": "Ververs aanbiedingen",
    "offers.storeLabel": "Winkel:",
    "offers.allStores": "Alle winkels",
    "offers.count": "{count} aanbiedingen",
    "offers.colProduct": "Product",
    "offers.colStore": "Winkel",
    "offers.colPrice": "Prijs",
    "offers.colDiscount": "Korting",
    "offers.empty": "Nog geen aanbiedingen opgehaald — klik op \"Ververs aanbiedingen\".",

    "pantry.loading": "Basisproducten worden geladen…",
    "pantry.helpPrefix": "Producten die je altijd in huis hebt (bv.",
    "pantry.helpSuffix": ") verschijnen straks niet op de boodschappenlijst.",
    "pantry.example1": "zout",
    "pantry.example2": "olie",
    "pantry.example3": "oregano",
    "pantry.placeholder": "bv. zout, olijfolie, peper",
    "pantry.empty": "Nog geen basisproducten.",

    "recipes.loading": "Recepten worden geladen…",
    "recipes.help": "Voeg een los recept toe via een directe link naar de receptpagina.",
    "recipes.urlPlaceholder": "https://voorbeeld.nl/recepten/mijn-recept",
    "recipes.courseFilterLabel": "Gang:",
    "recipes.allCourses": "Alle gangen",
    "recipes.count": "{count} recepten in de database",
    "recipes.rating": "Waardering",

    "shopping.loading": "Boodschappenlijst wordt geladen…",
    "shopping.help": "Alle ingrediënten van het weekmenu, min je basisproducten, plus wat je er zelf aan toevoegt. Plak het tekstblok in Todoist's snel-toevoegen venster — elke regel wordt een eigen taak.",
    "shopping.placeholder": "bv. wc-papier, eieren 6-pack",
    "shopping.frequentLabel": "Veelgebruikt:",
    "shopping.forgetTitle": "Niet meer onthouden",
    "shopping.copied": "Gekopieerd!",
    "shopping.copyButton": "Kopieer naar klembord",
    "shopping.copyFailed": "Kopiëren naar klembord mislukt: {error}",
    "shopping.empty": "Nog geen boodschappen voor deze week.",

    "sources.loading": "Bronnen worden geladen…",
    "sources.syncAll": "Synchroniseer alle bronnen",
    "sources.namePlaceholder": "Naam (bv. Mijn favoriete site)",
    "sources.urlPlaceholder": "https://voorbeeld.nl/recepten",
    "sources.addButton": "Bron toevoegen",
    "sources.colName": "Naam",
    "sources.colUrl": "URL",
    "sources.colEnabled": "Aan",
    "sources.colLastSync": "Laatst gesynchroniseerd",
    "sources.colRecipeCount": "Recepten",
    "sources.never": "nooit",
    "sources.syncOne": "Sync",
    "sources.confirmDelete": "Bron \"{name}\" en bijbehorende recepten verwijderen?",
    "sources.lastSyncHeading": "Laatste synchronisatie",
    "sources.syncResultNew": "{count} nieuwe recepten",
    "sources.syncResultUpdated": ", {count} ververst",
    "sources.syncResultPagesChecked": "({count} pagina's gecontroleerd)",

    "exclusions.loading": "Uitsluitingen worden geladen…",
    "exclusions.helpPrefix": "Vul een categorie in (bv.",
    "exclusions.helpMiddle": ") om alle verwante ingrediënten (kabeljauw, zalm, ...) uit te sluiten, of typ een los ingrediënt (bv.",
    "exclusions.helpSuffix": ").",
    "exclusions.example1": "vis",
    "exclusions.example2": "noten",
    "exclusions.example3": "varken",
    "exclusions.example4": "koriander",
    "exclusions.placeholder": "bv. vis, noten, koriander",
    "exclusions.addButton": "Uitsluiten",
    "exclusions.alsoLabel": "Ook:",
    "exclusions.empty": "Nog geen uitsluitingen.",

    "settings.loading": "Instellingen worden geladen…",
    "settings.courseCountsHelp": "Standaard aantal gerechten per gang wanneer je een nieuwe week genereert. Dit is het startpunt — je kan het altijd per week nog aanpassen op het Weekmenu-tabblad.",
    "settings.colorsHeading": "Kleuren",
    "settings.colorsHelp": "Pas de achtergrond- en accentkleur (knoppen, koppelingen, tabblad-highlight) van de app aan. Deze keuze geldt voor iedereen die de app gebruikt, ongeacht licht/donker modus van hun apparaat.",
    "settings.backgroundColorLabel": "Achtergrondkleur:",
    "settings.accentColorLabel": "Accentkleur:",
    "settings.resetColors": "Standaardkleuren",
    "settings.languageHeading": "Taal",
    "settings.languageHelp": "Kies de weergavetaal van de app.",
    "settings.languageLabel": "Taal:",
    "settings.languageEnglish": "English",
    "settings.languageDutch": "Nederlands",
  },
};

function interpolate(template, params) {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (match, key) => (key in params ? params[key] : match));
}

const LanguageContext = createContext(null);

export function LanguageProvider({ initialLanguage = DEFAULT_LANGUAGE, children }) {
  const [language, setLanguage] = useState(initialLanguage);

  // initialLanguage starts as the optimistic default and is only updated
  // once, when the real value comes back from GET /api/settings (see
  // App.jsx) - this syncs that one real update in without ever clobbering
  // a live switch made through the Settings language dropdown afterwards.
  useEffect(() => {
    setLanguage(initialLanguage);
  }, [initialLanguage]);

  const value = useMemo(() => {
    const dict = translations[language] || translations[DEFAULT_LANGUAGE];
    const t = (key, params) => interpolate(dict[key] ?? translations[DEFAULT_LANGUAGE][key] ?? key, params);
    return { language, setLanguage, t };
  }, [language]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useTranslation() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useTranslation must be used within a LanguageProvider");
  return ctx;
}
