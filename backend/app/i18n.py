"""User-facing message translations for API error details and generation
warnings. UI labels/strings live in the frontend's own i18n dictionary -
this module only covers text that originates on the backend (HTTPException
details, week-generation warnings)."""

MESSAGES: dict[str, dict[str, str]] = {
    "empty_term": {
        "en": "Empty term",
        "nl": "Lege term",
    },
    "exclusion_exists": {
        "en": "This exclusion already exists",
        "nl": "Deze uitsluiting bestaat al",
    },
    "exclusion_not_found": {
        "en": "Exclusion not found",
        "nl": "Uitsluiting niet gevonden",
    },
    "pantry_staple_exists": {
        "en": "This pantry staple is already in the list",
        "nl": "Dit basisproduct staat al in de lijst",
    },
    "pantry_staple_not_found": {
        "en": "Pantry staple not found",
        "nl": "Basisproduct niet gevonden",
    },
    "leftover_exists": {
        "en": "This leftover is already in the list",
        "nl": "Dit restje staat al in de lijst",
    },
    "leftover_not_found": {
        "en": "Leftover not found",
        "nl": "Restje niet gevonden",
    },
    "unknown_store": {
        "en": "Unknown or unsupported store: {store}",
        "nl": "Onbekende of niet-ondersteunde winkel: {store}",
    },
    "course_counts_negative": {
        "en": "Number of dishes cannot be negative",
        "nl": "Aantal gerechten kan niet negatief zijn",
    },
    "course_counts_too_high": {
        "en": "Number of dishes cannot exceed {max}, got {total}",
        "nl": "Aantal gerechten kan niet meer dan {max} zijn, kreeg {total}",
    },
    "week_frozen": {
        "en": "This week's menu is frozen. Unfreeze it first to make changes.",
        "nl": "Weekmenu is bevroren. Ontdooi de week eerst om deze te wijzigen.",
    },
    "invalid_day_of_week": {
        "en": "day_of_week must be between 0 and 6",
        "nl": "day_of_week moet tussen 0 en 6 liggen",
    },
    "week_menu_not_found": {
        "en": "Week menu not found",
        "nl": "Weekmenu niet gevonden",
    },
    "no_week_menu_yet": {
        "en": "No week menu yet for this week — click 'Generate new week' to create one.",
        "nl": "Nog geen weekmenu voor deze week — klik op 'Genereer nieuwe week' om er een te maken.",
    },
    "fetch_page_failed": {
        "en": "Could not fetch the page: {error}",
        "nl": "Kon de pagina niet ophalen: {error}",
    },
    "no_recipe_data_found": {
        "en": "No recipe data (schema.org) found on this page.",
        "nl": "Geen recept-gegevens (schema.org) gevonden op deze pagina.",
    },
    "recipe_not_found": {
        "en": "Recipe not found",
        "nl": "Recept niet gevonden",
    },
    "recipe_title_required": {
        "en": "Title is required",
        "nl": "Titel is verplicht",
    },
    "recipe_ingredients_required": {
        "en": "At least one ingredient is required",
        "nl": "Minstens één ingrediënt is verplicht",
    },
    "recipe_not_manual": {
        "en": "This recipe wasn't added manually and can't be edited this way",
        "nl": "Dit recept is niet handmatig toegevoegd en kan zo niet bewerkt worden",
    },
    "invalid_course": {
        "en": "Invalid course",
        "nl": "Ongeldige gang",
    },
    "no_recipe_matches_query": {
        "en": "No recipe found matching \"{query}\".",
        "nl": "Geen recept gevonden dat overeenkomt met \"{query}\".",
    },
    "invalid_rating": {
        "en": "Invalid rating; must be 'like', 'dislike' or null",
        "nl": "Ongeldige rating; moet 'like', 'dislike' of null zijn",
    },
    "invalid_hex_color": {
        "en": "{field} must be a hex color, e.g. #c1440e",
        "nl": "{field} moet een hex-kleur zijn, bv. #c1440e",
    },
    "field_background_color": {
        "en": "Background color",
        "nl": "Achtergrondkleur",
    },
    "field_accent_color": {
        "en": "Accent color",
        "nl": "Accentkleur",
    },
    "empty_text": {
        "en": "Empty text",
        "nl": "Lege tekst",
    },
    "item_not_found": {
        "en": "Item not found",
        "nl": "Item niet gevonden",
    },
    "source_not_found": {
        "en": "Source not found",
        "nl": "Bron niet gevonden",
    },
    "no_recipes_for_course": {
        "en": "No recipes with course '{course}' available for {count} day(s).",
        "nl": "Geen recepten met gang '{course}' beschikbaar voor {count} dag(en).",
    },
    "too_few_unique_recipes": {
        "en": "Too few unique recipes with course '{course}'; a recipe may be repeated.",
        "nl": "Te weinig unieke recepten met gang '{course}'; een recept wordt mogelijk herhaald.",
    },
    "low_dish_type_variety": {
        "en": "Little variety in dish types within course '{course}'; sync more sources for a more varied week.",
        "nl": "Weinig variatie aan gerecht-types binnen gang '{course}'; synchroniseer meer bronnen voor een gevarieerdere week.",
    },
    "no_recipes_available": {
        "en": "No recipes available. Add sources and sync, or relax your exclusions.",
        "nl": "Geen recepten beschikbaar. Voeg bronnen toe en synchroniseer, of versoepel je uitsluitingen.",
    },
    "no_other_recipes_for_course": {
        "en": "No other recipes with course '{course}' available to swap to.",
        "nl": "Geen andere recepten met gang '{course}' beschikbaar om naar te wisselen.",
    },
    "repetition_unavoidable": {
        "en": "All other recipes are already used this week; repetition could not be avoided.",
        "nl": "Alle andere recepten worden al deze week gebruikt; herhaling kon niet worden voorkomen.",
    },
    "unexpected_sync_error": {
        "en": "Unexpected error during sync: {error}",
        "nl": "Onverwachte fout tijdens synchroniseren: {error}",
    },
    "sitemap_read_failed": {
        "en": "Could not read sitemap: {error}",
        "nl": "Kon sitemap niet lezen: {error}",
    },
    "no_recipe_urls_found": {
        "en": "No recipe URLs found via sitemap.xml / robots.txt",
        "nl": "Geen recepten-URL's gevonden via sitemap.xml / robots.txt",
    },
}


def t(key: str, lang: str, **kwargs) -> str:
    template = MESSAGES[key].get(lang) or MESSAGES[key]["en"]
    return template.format(**kwargs) if kwargs else template
