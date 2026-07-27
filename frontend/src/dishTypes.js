const DISH_TYPE_LABELS = {
  en: {
    soep: "Soup",
    salade: "Salad",
    pasta: "Pasta",
    "aziatisch-wok": "Asian / wok",
    "curry-indiaas": "Curry / Indian",
    "ovenschotel-stoof": "Casserole / stew",
    pizza: "Pizza",
    "taco-wrap": "Taco / wrap",
    risotto: "Risotto",
    "bbq-grill": "BBQ / grill",
    vis: "Fish",
    "schaal-schelpdieren": "Shellfish",
    kip: "Chicken",
    rund: "Beef",
    varken: "Pork",
    lam: "Lamb",
    vegetarisch: "Vegetarian",
    overig: "Other",
  },
  nl: {
    soep: "Soep",
    salade: "Salade",
    pasta: "Pasta",
    "aziatisch-wok": "Aziatisch / wok",
    "curry-indiaas": "Curry / Indiaas",
    "ovenschotel-stoof": "Ovenschotel / stoof",
    pizza: "Pizza",
    "taco-wrap": "Taco / wrap",
    risotto: "Risotto",
    "bbq-grill": "BBQ / grill",
    vis: "Vis",
    "schaal-schelpdieren": "Schaal- en schelpdieren",
    kip: "Kip",
    rund: "Rund",
    varken: "Varken",
    lam: "Lam",
    vegetarisch: "Vegetarisch",
    overig: "Overig",
  },
};

export function dishTypeLabel(dishType, lang = "en") {
  const labels = DISH_TYPE_LABELS[lang] || DISH_TYPE_LABELS.en;
  return labels[dishType] || dishType;
}
