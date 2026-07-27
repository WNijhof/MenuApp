const COURSE_LABELS = {
  en: {
    voorgerecht: "Starter",
    hoofdgerecht: "Main course",
    nagerecht: "Dessert",
  },
  nl: {
    voorgerecht: "Voorgerecht",
    hoofdgerecht: "Hoofdgerecht",
    nagerecht: "Nagerecht",
  },
};

export function courseLabels(lang = "en") {
  return COURSE_LABELS[lang] || COURSE_LABELS.en;
}

export function courseLabel(course, lang = "en") {
  return courseLabels(lang)[course] || course;
}
