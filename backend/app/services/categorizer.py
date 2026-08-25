"""Dish-type inference (for weekly variety) and ingredient-exclusion matching
(so excluding 'vis' also catches 'kabeljauw', 'zalm', ...).
"""

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "data" / "taxonomy.json"

# Dish-style keywords checked first (title / category / keywords), in priority
# order. These describe *how* a meal is prepared, independent of protein.
DISH_STYLE_KEYWORDS: dict[str, list[str]] = {
    "soep": ["soep", "bouillon", "soup", "broth", "chowder"],
    "salade": ["salade", "salad"],
    "pasta": [
        "pasta", "spaghetti", "lasagne", "lasagna", "macaroni", "penne",
        "tagliatelle", "fettuccine", "linguine", "ravioli", "gnocchi",
        "mac and cheese",
    ],
    "aziatisch-wok": [
        "wok", "roerbak", "aziatisch", "chinees", "thai", "indonesisch",
        "noedel", "noedels", "nasi", "bami", "pad thai", "sushi",
        "asian", "chinese", "thai", "indonesian", "japanese", "korean",
        "vietnamese", "noodle", "noodles", "stir-fry", "stir fry",
        "teriyaki", "ramen",
    ],
    "curry-indiaas": [
        "curry", "indiaas", "masala", "tikka", "dal",
        "indian", "korma", "vindaloo", "biryani", "curried",
    ],
    "ovenschotel-stoof": [
        "ovenschotel", "oven schotel", "stoofpot", "stoofvlees", "stamppot",
        "gratin", "uit de oven",
        "casserole", "stew", "traybake", "tray bake", "one-pot",
        "one pot", "pot pie", "hotpot", "hot pot",
    ],
    "pizza": ["pizza"],
    "taco-wrap": ["taco", "wrap", "burrito", "quesadilla", "fajita", "enchilada"],
    "risotto": ["risotto"],
    "bbq-grill": ["bbq", "barbecue", "grill", "grilled"],
}

# Protein-based fallback categories, matched against ingredients via the
# same taxonomy used for exclusions. Order matters (first match wins).
PROTEIN_CATEGORY_PRIORITY = ["vis", "schaal-schelpdieren", "kip", "rund", "varken", "lam"]

# Course (gang) inference: explicit course words are checked first since
# they're the most authoritative signal (often straight from the site's own
# recipeCategory). Dessert food-type words are checked next because most
# recipe sites never label a cake or cookie recipe with the word
# "nagerecht" - the food itself is the only signal. Matched as
# substring-within-token like the ingredient taxonomy (handles Dutch
# compounds: "taart" catches "zandtaart", "aardbeientaart", ...) except for
# the terms in _EXACT_TOKEN_COURSE_TERMS, which are common substrings of
# unrelated everyday words ("gebak" in "gebakken", "koekjes" in
# "pannenkoekjes") and need a whole-word match instead.
COURSE_KEYWORDS: dict[str, list[str]] = {
    "nagerecht": [
        "nagerecht", "dessert", "toetje", "koekjes", "cookies", "cookie",
        "muffin", "muffins", "roomijs", "ijsje", "pudding", "crumble",
        "cheesecake", "brownie", "brownies", "panna cotta",
        "mousse", "trifle", "milkshake", "taart", "cake", "gebak",
        "sprits", "wafel", "bonbon", "banket", "kruidnoot", "kruidnoten",
        "pepernoot", "pepernoten", "gebakje",
        "ice cream", "sorbet", "pie", "tart", "pastry", "shortbread",
        "custard", "fudge", "sundae", "pavlova", "tiramisu",
    ],
    "voorgerecht": [
        "voorgerecht", "amuse", "borrelhapje", "borrelhapjes", "tapas",
        "carpaccio", "hapje", "hapjes",
        "starter", "starters", "appetizer", "appetizers", "appetiser",
        "appetisers", "hors d'oeuvre",
    ],
    "hoofdgerecht": [
        "hoofdgerecht", "hoofdgang", "main course", "maaltijd",
        "main dish", "main meal", "dinner",
    ],
}
# "tart" needs a whole-word match, not the usual compound/plural substring
# match: as a substring it also hits "starter" and "tartaar"/"tartare"
# (steak tartare, a starter/main - not a dessert), which would otherwise
# misclassify those as nagerecht.
_EXACT_TOKEN_COURSE_TERMS = {"gebak", "koekjes", "tart"}


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def normalize_text(text: str) -> str:
    return _strip_accents(text or "").lower().strip()


@lru_cache(maxsize=1)
def load_taxonomy() -> dict[str, list[str]]:
    with open(TAXONOMY_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return {
        category: [normalize_text(term) for term in terms]
        for category, terms in raw.items()
    }


def taxonomy_categories() -> list[str]:
    return sorted(load_taxonomy().keys())


_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text)


# Terms that are a plain prefix of a common, unrelated word - substring-
# within-token matching would otherwise false-positive on those (e.g. "port"
# inside "portobello", which is itself a taxonomy term for mushrooms).
# Needs the same whole-word treatment as the <=3-char terms below even
# though it's longer.
_EXACT_TOKEN_TERMS = {"port"}


def _term_matches(tokens: list[str], full_text: str, term: str) -> bool:
    """Dutch ingredient text is full of compounds ('varkenshaasmedaillons')
    and irregular plurals ('kipfilets'), so a strict whole-word match misses
    most real matches. Multi-word phrases ('rode wijn') are matched as a
    substring of the full text; single words are matched per-token, with
    exact+simple-plural equality for short/ambiguous terms (<=3 chars, e.g.
    'ui', 'ei', 'ham') to avoid false hits inside unrelated words, and
    substring-within-token for longer terms (handles both compounds and
    plurals in one go: 'kipfilet' in 'kipfilets', 'varkenshaas' in
    'varkenshaasmedaillons')."""
    if not term:
        return False
    if " " in term or "-" in term:
        return term in full_text
    if len(term) <= 3 or term in _EXACT_TOKEN_TERMS:
        return term in tokens or f"{term}s" in tokens or f"{term}en" in tokens
    return any(term in tok for tok in tokens)


def expand_exclusion_term(term: str) -> list[str]:
    """A configured exclusion term may be a taxonomy category name (expands
    to all its synonyms) or a literal ingredient/word."""
    taxonomy = load_taxonomy()
    normalized = normalize_text(term)
    if normalized in taxonomy:
        return taxonomy[normalized]
    return [normalized]


def normalize_terms(terms: list[str]) -> list[str]:
    """Pre-normalize a term list once when it's about to be checked against
    many recipes in a loop (e.g. "does any recipe use a current offer?")
    - re-normalizing the same term list on every single call is the
    dominant cost when scanning thousands of recipes."""
    return [normalize_text(t) for t in terms if t]


# Words that show up in supermarket offer names but never in a recipe's own
# ingredient line: pack sizes/units, store/brand names, generic filler.
# Stripping these out of a name like "AH Kipfilet 500 g" leaves "kipfilet" -
# a word that can actually turn up in an ingredient list, unlike the name as
# a whole ever would.
_OFFER_NOISE_WORDS = {
    "kg", "g", "gr", "gram", "ml", "cl", "l", "liter",
    "stuks", "stuk", "st", "pak", "pack", "zak", "doos", "fles", "blik",
    "bakje", "krat", "x", "per", "voordeelverpakking", "verpakking",
    "ah", "aldi", "jumbo", "lidl", "coop", "plus", "ekoplaza", "huismerk",
    "de", "het", "een", "en", "van", "met", "voor",
}
_NUMBER_RE = re.compile(r"^\d+([.,]\d+)?$")


def normalize_offer_terms(offer_names: list[str]) -> list[str]:
    """Offer names are typically multi-word with a pack size/unit and often
    a brand ('Aardappelen 2 kg', 'AH Kipfilet 500 g') - matched as a whole
    phrase (like a normal multi-word term) they'd essentially never appear
    verbatim in a recipe's ingredient text, so the offer/preference signal
    would almost never fire. Flattening each name into its significant
    single words instead lets the normal single-word (compound/plural
    aware) matching in `_term_matches` do the work, at the cost of being a
    looser match than a literal phrase."""
    words: list[str] = []
    for name in offer_names:
        for word in _tokenize(normalize_text(name)):
            if word in _OFFER_NOISE_WORDS or _NUMBER_RE.match(word) or len(word) <= 2:
                continue
            words.append(word)
    return words


class TermMatcher(NamedTuple):
    """Terms pre-split by which check they need (see _term_matches), so
    matching many recipes against the same term list only pays the
    classification cost once instead of on every single recipe - see
    compile_terms."""

    exact: tuple[str, ...]
    phrase: tuple[str, ...]
    substring: tuple[str, ...]

    def matches(self, ingredients: list[str]) -> bool:
        if not (self.exact or self.phrase or self.substring):
            return False
        full_text = normalize_text(" | ".join(ingredients))
        if any(term in full_text for term in self.phrase):
            return True
        tokens = set(_tokenize(full_text))
        if any(
            term in tokens or f"{term}s" in tokens or f"{term}en" in tokens
            for term in self.exact
        ):
            return True
        return any(term in tok for term in self.substring for tok in tokens)


def compile_terms(terms: list[str]) -> TermMatcher:
    """Classifies (and dedupes) a normalized term list once. Callers
    matching many recipes against the same term list (see
    _preferred_recipe_ids, get_available_recipes, _has_offer) should call
    this once and reuse the result via TermMatcher.matches, rather than
    re-deriving the same classification (and re-scanning every ingredient
    token) on every single recipe - that's the dominant cost when checking
    e.g. hundreds of offer terms against thousands of recipes."""
    exact: list[str] = []
    phrase: list[str] = []
    substring: list[str] = []
    for term in dict.fromkeys(t for t in terms if t):
        if " " in term or "-" in term:
            phrase.append(term)
        elif len(term) <= 3 or term in _EXACT_TOKEN_TERMS:
            exact.append(term)
        else:
            substring.append(term)
    return TermMatcher(tuple(exact), tuple(phrase), tuple(substring))


def _any_normalized_term_matches(ingredients: list[str], normalized_terms: list[str]) -> bool:
    return compile_terms(normalized_terms).matches(ingredients)


def _any_term_matches(ingredients: list[str], terms: list[str]) -> bool:
    return _any_normalized_term_matches(ingredients, normalize_terms(terms))


def compile_exclusion_terms(exclusion_terms: list[str]) -> TermMatcher:
    """expand_exclusion_term already returns normalized words (from
    load_taxonomy/normalize_text), so this skips the raw-term
    normalize_terms step _any_term_matches does for terms that haven't
    been normalized yet."""
    banned_words: set[str] = set()
    for term in exclusion_terms:
        banned_words.update(expand_exclusion_term(term))
    return compile_terms(list(banned_words))


def ingredient_matches_pantry(ingredient: str, pantry_terms: list[str]) -> bool:
    """Whether a single shopping-list ingredient line names an
    always-on-hand staple (zout, olie, ...) and should be left off the
    list. Same literal, non-expanding match as leftovers."""
    return _any_term_matches([ingredient], pantry_terms)


def infer_dish_type(title: str, category: str | None, keywords: str | None, ingredients: list[str]) -> str:
    signal_text = normalize_text(" ".join(filter(None, [title, category, keywords])))

    for dish_type, kw_list in DISH_STYLE_KEYWORDS.items():
        for kw in kw_list:
            if normalize_text(kw) in signal_text:
                return dish_type

    full_text = normalize_text(" | ".join(ingredients))
    # Bouillon/stock cubes ("runderbouillon", "kippenbouillon") name a meat
    # but are a flavour base, not the dish's headline protein - a huge
    # share of recipes use beef or chicken stock regardless of what they're
    # actually built around, so they'd otherwise drown out the real signal.
    protein_tokens = [
        t for t in _tokenize(full_text) if "bouillon" not in t and "fond" not in t
    ]
    taxonomy = load_taxonomy()
    for protein_category in PROTEIN_CATEGORY_PRIORITY:
        words = taxonomy.get(protein_category, [])
        if any(_term_matches(protein_tokens, full_text, w) for w in words):
            return protein_category

    has_animal_protein = any(
        any(_term_matches(protein_tokens, full_text, w) for w in taxonomy.get(cat, []))
        for cat in PROTEIN_CATEGORY_PRIORITY
    )
    if not has_animal_protein:
        return "vegetarisch"

    return "overig"


def _course_kw_matches(tokens: list[str], full_text: str, kw: str) -> bool:
    if kw in _EXACT_TOKEN_COURSE_TERMS:
        return kw in tokens or f"{kw}s" in tokens
    return _term_matches(tokens, full_text, kw)


def infer_course(title: str, category: str | None, keywords: str | None) -> str:
    """Classify a recipe as voorgerecht / hoofdgerecht / nagerecht. Defaults
    to hoofdgerecht, the overwhelmingly common case on dinner-recipe sites.
    "hartige taart" (savory tart/quiche) - and equally "hartige muffins",
    "hartige cake", etc. - is excluded from every nagerecht keyword, not
    just the sweet-bake fallback terms, so an explicitly-savory dish never
    gets misclassified as dessert."""
    signal_text = normalize_text(" ".join(filter(None, [title, category, keywords])))
    tokens = _tokenize(signal_text)
    is_savory = any(t.startswith("hartig") for t in tokens)

    for course in ("nagerecht", "voorgerecht", "hoofdgerecht"):
        for kw in COURSE_KEYWORDS[course]:
            if course == "nagerecht" and is_savory:
                continue
            if _course_kw_matches(tokens, signal_text, kw):
                return course

    return "hoofdgerecht"
