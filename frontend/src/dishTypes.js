export const DISH_TYPE_LABELS = {
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
};

export function dishTypeLabel(dishType) {
  return DISH_TYPE_LABELS[dishType] || dishType;
}
