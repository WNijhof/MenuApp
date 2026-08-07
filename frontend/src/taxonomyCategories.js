// Display labels only, for the category keys returned by GET
// /api/exclusions/taxonomy. The underlying key (submitted as the exclusion
// term itself) stays the taxonomy.json key - only how it's shown changes
// with the UI language. The taxonomy's actual matching synonyms
// (kabeljauw, zalm, salmon, cod, ...) include both Dutch and English words
// regardless of UI language, since recipes can come from either Dutch or
// English sources and ingredient text is matched as scraped, not
// translated.
const TAXONOMY_CATEGORY_LABELS = {
  en: {
    vis: "Fish",
    "schaal-schelpdieren": "Shellfish",
    rund: "Beef",
    varken: "Pork",
    kip: "Chicken",
    lam: "Lamb",
    noten: "Nuts",
    gluten: "Gluten",
    zuivel: "Dairy",
    ei: "Egg",
    peulvruchten: "Legumes",
    paddenstoelen: "Mushrooms",
    "ui-look": "Onion / garlic",
    alcohol: "Alcohol",
    "vegetarisch-vervangers": "Vegetarian substitutes",
  },
  nl: {
    vis: "Vis",
    "schaal-schelpdieren": "Schaal- en schelpdieren",
    rund: "Rund",
    varken: "Varken",
    kip: "Kip",
    lam: "Lam",
    noten: "Noten",
    gluten: "Gluten",
    zuivel: "Zuivel",
    ei: "Ei",
    peulvruchten: "Peulvruchten",
    paddenstoelen: "Paddenstoelen",
    "ui-look": "Ui en knoflook",
    alcohol: "Alcohol",
    "vegetarisch-vervangers": "Vegetarische vervangers",
  },
};

export function taxonomyCategoryLabel(category, lang = "en") {
  const labels = TAXONOMY_CATEGORY_LABELS[lang] || TAXONOMY_CATEGORY_LABELS.en;
  return labels[category] || category;
}
