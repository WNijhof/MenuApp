export const COURSE_LABELS = {
  voorgerecht: "Voorgerecht",
  hoofdgerecht: "Hoofdgerecht",
  nagerecht: "Nagerecht",
};

export function courseLabel(course) {
  return COURSE_LABELS[course] || course;
}
