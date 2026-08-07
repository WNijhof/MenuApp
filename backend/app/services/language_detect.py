"""Lightweight nl/en detection for recipe text.

The app only ever deals with two languages, so a full language-detection
library is more than this needs - a stopword-overlap heuristic is enough to
tell Dutch and English prose apart. schema.org's `inLanguage` hint (see
recipe_parser._extract_language_hint) is preferred over this whenever a
site provides one; this is the fallback for sites that don't, and for
backfilling recipes scraped before that hint was tracked.
"""

import re

_WORD_RE = re.compile(r"[a-z]+")

SUPPORTED_LANGUAGES = ("nl", "en")

# Function/measurement words common in recipe prose (instructions,
# ingredient lines) that essentially never appear in the other language -
# plain grammatical stopwords alone are too sparse in short ingredient
# lines ("2 tbsp olive oil" has none), so cooking-specific terms are mixed
# in to give the heuristic enough signal on that kind of short text too.
_NL_SIGNAL_WORDS = {
    "de", "het", "een", "van", "voor", "met", "en", "in", "op", "is",
    "zijn", "dit", "deze", "of", "aan", "uit", "tot", "over", "naar",
    "door", "bij", "wat", "wordt", "worden", "als", "dan", "snufje",
    "minuten", "eetlepel", "eetlepels", "theelepel", "theelepels",
    "oven", "voorverwarmen", "verwarm", "gesneden", "gehakt", "beetje",
}
_EN_SIGNAL_WORDS = {
    "the", "and", "of", "with", "for", "this", "these", "or", "in",
    "is", "are", "to", "from", "into", "without", "by", "your", "a",
    "an", "until", "then", "over", "on", "pinch",
    "minutes", "tablespoon", "tablespoons", "teaspoon", "teaspoons",
    "oven", "preheat", "chopped", "minced", "until",
}


def detect_language(text: str) -> str:
    """Returns 'nl' or 'en'. Defaults to 'nl' when the signal is absent or
    tied, matching this app's original Dutch-only behavior."""
    tokens = set(_WORD_RE.findall((text or "").lower()))
    nl_hits = len(tokens & _NL_SIGNAL_WORDS)
    en_hits = len(tokens & _EN_SIGNAL_WORDS)
    return "en" if en_hits > nl_hits else "nl"


def resolve_language(hint: str | None, text: str) -> str:
    """`hint` is an already-normalized 'nl'/'en' code from the site itself
    (see recipe_parser._extract_language_hint) - trusted as-is when present
    since it's an explicit signal from the page, falling back to heuristic
    detection otherwise."""
    if hint in SUPPORTED_LANGUAGES:
        return hint
    return detect_language(text)
