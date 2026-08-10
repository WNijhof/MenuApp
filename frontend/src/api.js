const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // ignore non-JSON error bodies
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  getCurrentMenu: (weekStartDate) =>
    request(weekStartDate ? `/menu/current?week_start_date=${weekStartDate}` : "/menu/current"),
  getMenuHistory: () => request("/menu/history"),
  deleteMenuWeek: (weekStartDate) =>
    request(`/menu/${weekStartDate}`, { method: "DELETE" }),
  getShoppingList: (weekStartDate) =>
    request(
      weekStartDate
        ? `/menu/current/shopping-list?week_start_date=${weekStartDate}`
        : "/menu/current/shopping-list"
    ),
  generateMenu: (courseCounts, weekStartDate) =>
    request("/menu/generate", {
      method: "POST",
      body:
        courseCounts || weekStartDate
          ? JSON.stringify({ course_counts: courseCounts, week_start_date: weekStartDate })
          : undefined,
    }),
  refreshDay: (dayOfWeek, weekStartDate, query) => {
    const params = new URLSearchParams();
    if (weekStartDate) params.set("week_start_date", weekStartDate);
    if (query) params.set("query", query);
    const qs = params.toString();
    return request(`/menu/day/${dayOfWeek}/refresh${qs ? `?${qs}` : ""}`, { method: "POST" });
  },
  setWeekFrozen: (weekStartDate, frozen) =>
    request(`/menu/${weekStartDate}/freeze`, {
      method: "PATCH",
      body: JSON.stringify({ frozen }),
    }),

  getSources: () => request("/sources"),
  createSource: (payload) =>
    request("/sources", { method: "POST", body: JSON.stringify(payload) }),
  updateSource: (id, payload) =>
    request(`/sources/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteSource: (id) => request(`/sources/${id}`, { method: "DELETE" }),
  syncSource: (id) => request(`/sources/${id}/sync`, { method: "POST" }),
  syncAllSources: () => request("/sources/sync-all", { method: "POST" }),

  getRecipes: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.course) params.set("course", filters.course);
    if (filters.rating) params.set("rating", filters.rating);
    const qs = params.toString();
    return request(qs ? `/recipes?${qs}` : "/recipes");
  },
  addRecipeByUrl: (url) =>
    request("/recipes/add-url", { method: "POST", body: JSON.stringify({ url }) }),
  addManualRecipe: (payload) =>
    request("/recipes/manual", { method: "POST", body: JSON.stringify(payload) }),
  updateManualRecipe: (id, payload) =>
    request(`/recipes/${id}/manual`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteRecipe: (id) => request(`/recipes/${id}`, { method: "DELETE" }),
  rateRecipe: (id, rating) =>
    request(`/recipes/${id}/rating`, { method: "PATCH", body: JSON.stringify({ rating }) }),

  getExclusions: () => request("/exclusions"),
  getTaxonomyCategories: () => request("/exclusions/taxonomy"),
  createExclusion: (term) =>
    request("/exclusions", { method: "POST", body: JSON.stringify({ term }) }),
  deleteExclusion: (id) => request(`/exclusions/${id}`, { method: "DELETE" }),

  getPantryStaples: () => request("/pantry"),
  createPantryStaple: (term) =>
    request("/pantry", { method: "POST", body: JSON.stringify({ term }) }),
  deletePantryStaple: (id) => request(`/pantry/${id}`, { method: "DELETE" }),

  getLeftovers: () => request("/leftovers"),
  createLeftover: (term) =>
    request("/leftovers", { method: "POST", body: JSON.stringify({ term }) }),
  deleteLeftover: (id) => request(`/leftovers/${id}`, { method: "DELETE" }),

  addShoppingListItem: (text) =>
    request("/shopping/extras", { method: "POST", body: JSON.stringify({ text }) }),
  deleteShoppingListExtra: (id) => request(`/shopping/extras/${id}`, { method: "DELETE" }),
  getFrequentItems: () => request("/shopping/frequent"),
  deleteFrequentItem: (id) => request(`/shopping/frequent/${id}`, { method: "DELETE" }),

  getOffers: () => request("/offers"),
  syncOffers: () => request("/offers/sync", { method: "POST" }),

  getSettings: () => request("/settings"),
  updateSettings: (payload) =>
    request("/settings", { method: "PUT", body: JSON.stringify(payload) }),
};
