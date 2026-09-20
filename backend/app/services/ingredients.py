"""Turns free-text ingredient lines ("2 el olijfolie", "500 g rundergehakt",
"1 1/2 tsp salt") into structured pieces so the shopping list can add up
quantities across recipes and sort items in supermarket-walking order.

Only what can be read reliably is interpreted: a leading quantity, an
optional known unit, and the ingredient name. Lines that don't fit
(no leading number, odd phrasing) simply stay as their own plain item.
Nothing here looks at the recipe's language - lines reach it already
translated to the UI language (see services/shopping_list.py), and unit /
section vocabularies cover both Dutch and English.
"""

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.services.categorizer import _term_matches, _tokenize, normalize_text

SECTIONS_PATH = Path(__file__).resolve().parent.parent / "data" / "store_sections.json"

# --- quantities ------------------------------------------------------------

_VULGAR = {"½": 0.5, "¼": 0.25, "¾": 0.75, "⅓": 1 / 3, "⅔": 2 / 3, "⅛": 0.125}
_VULGAR_CLASS = "".join(_VULGAR)
_NUM = (
    rf"(?:\d+\s+\d+/\d+|\d+/\d+|\d+(?:[.,]\d+)?\s*[{_VULGAR_CLASS}]?|[{_VULGAR_CLASS}])"
)
_LINE_RE = re.compile(
    rf"^\s*(?P<a>{_NUM})(?:\s*(?:-|–|—|tot|to)\s*(?P<b>{_NUM}))?\s*(?P<rest>.*)$",
    re.IGNORECASE,
)


def _to_number(text: str) -> float:
    text = text.strip()
    total = 0.0
    if text and text[-1] in _VULGAR:
        total += _VULGAR[text[-1]]
        text = text[:-1].strip()
    if not text:
        return total
    if "/" in text:
        whole = 0.0
        if " " in text:
            whole_part, text = text.split(None, 1)
            whole = float(whole_part)
        num, den = text.split("/")
        return total + whole + float(num) / float(den)
    return total + float(text.replace(",", "."))


# --- units -----------------------------------------------------------------

# alias -> (canonical unit, factor to that unit). "" = plain count.
_UNIT_ALIASES: dict[str, tuple[str, float]] = {}


def _register(canonical: str, factor_by_alias: dict[str, float]) -> None:
    for alias, factor in factor_by_alias.items():
        _UNIT_ALIASES[alias] = (canonical, factor)


_register("g", {
    "g": 1, "gr": 1, "gram": 1, "gramme": 1, "grams": 1, "kg": 1000, "kilo": 1000, "kilogram": 1000, "kilos": 1000,
    "oz": 28.35, "ounce": 28.35, "ounces": 28.35, "lb": 453.6, "lbs": 453.6, "pound": 453.6, "pounds": 453.6,
})
_register("ml", {
    "ml": 1, "milliliter": 1, "cl": 10, "centiliter": 10, "dl": 100, "deciliter": 100, "l": 1000, "liter": 1000,
    "litre": 1000, "liters": 1000, "litres": 1000,
})
_register("tl", {"tl": 1, "tsp": 1, "teaspoon": 1, "teaspoons": 1, "theelepel": 1, "theelepels": 1})
_register("el", {"el": 1, "tbsp": 1, "tablespoon": 1, "tablespoons": 1, "eetlepel": 1, "eetlepels": 1})
_register("cup", {"cup": 1, "cups": 1, "kopje": 1, "kopjes": 1})
_register("", {"stuk": 1, "stuks": 1, "stukken": 1, "st": 1, "piece": 1, "pieces": 1, "x": 1})
_register("teentje", {"teentje": 1, "teentjes": 1, "teen": 1, "tenen": 1, "clove": 1, "cloves": 1})
_register("blik", {"blik": 1, "blikje": 1, "blikken": 1, "blikjes": 1, "can": 1, "cans": 1, "tin": 1, "tins": 1})
_register("pak", {"pak": 1, "pakje": 1, "pakken": 1, "pakjes": 1, "pack": 1, "packs": 1, "package": 1, "packet": 1})
_register("pot", {"pot": 1, "potje": 1, "potten": 1, "potjes": 1, "jar": 1, "jars": 1})
_register("bos", {"bos": 1, "bosje": 1, "bosjes": 1, "bunch": 1, "bunches": 1})
_register("takje", {"takje": 1, "takjes": 1, "sprig": 1, "sprigs": 1, "twijg": 1})
_register("plak", {"plak": 1, "plakje": 1, "plakken": 1, "plakjes": 1, "slice": 1, "slices": 1})
_register("handvol", {"handvol": 1, "handful": 1, "handfuls": 1})
_register("snufje", {"snufje": 1, "snuf": 1, "pinch": 1, "pinches": 1})
_register("scheut", {"scheut": 1, "scheutje": 1, "dash": 1, "dashes": 1, "splash": 1})
_register("zak", {"zak": 1, "zakje": 1, "zakken": 1, "zakjes": 1, "bag": 1, "bags": 1})
_register("bol", {"bol": 1, "bollen": 1, "bolletje": 1, "head": 1, "heads": 1})
_register("stengel", {"stengel": 1, "stengels": 1, "stalk": 1, "stalks": 1})

# canonical unit -> {language: (singular, plural)}; g/ml/kg/l are language-neutral.
_UNIT_LABELS: dict[str, dict[str, tuple[str, str]]] = {
    "tl": {"nl": ("tl", "tl"), "en": ("tsp", "tsp")},
    "el": {"nl": ("el", "el"), "en": ("tbsp", "tbsp")},
    "cup": {"nl": ("kopje", "kopjes"), "en": ("cup", "cups")},
    "teentje": {"nl": ("teentje", "teentjes"), "en": ("clove", "cloves")},
    "blik": {"nl": ("blik", "blikken"), "en": ("can", "cans")},
    "pak": {"nl": ("pak", "pakken"), "en": ("pack", "packs")},
    "pot": {"nl": ("pot", "potten"), "en": ("jar", "jars")},
    "bos": {"nl": ("bos", "bossen"), "en": ("bunch", "bunches")},
    "takje": {"nl": ("takje", "takjes"), "en": ("sprig", "sprigs")},
    "plak": {"nl": ("plak", "plakken"), "en": ("slice", "slices")},
    "handvol": {"nl": ("handvol", "handvol"), "en": ("handful", "handfuls")},
    "snufje": {"nl": ("snufje", "snufjes"), "en": ("pinch", "pinches")},
    "scheut": {"nl": ("scheut", "scheuten"), "en": ("dash", "dashes")},
    "zak": {"nl": ("zak", "zakken"), "en": ("bag", "bags")},
    "bol": {"nl": ("bol", "bollen"), "en": ("head", "heads")},
    "stengel": {"nl": ("stengel", "stengels"), "en": ("stalk", "stalks")},
}

_SIZE_WORDS = {
    "grote", "kleine", "middelgrote", "flinke", "large", "small", "medium", "big", "extra",
}
_NAME_ALIASES = {
    "eieren": "ei", "uien": "ui", "tomaten": "tomaat", "aardappelen": "aardappel", "citroenen": "citroen",
    "wortelen": "wortel", "wortels": "wortel", "paprika's": "paprika", "eggs": "egg", "onions": "onion",
    "tomatoes": "tomato", "potatoes": "potato", "lemons": "lemon", "carrots": "carrot",
}


@dataclass(slots=True)
class ParsedLine:
    qty: float | None  # None: no readable quantity
    unit: str  # canonical unit ("" = plain count); only meaningful when qty is set
    name: str  # cleaned display name
    key: str  # normalized merge key


def _clean_name(raw: str) -> str:
    name = re.sub(r"\([^)]*\)", " ", raw)  # "(400 g)", "(optional)"
    name = name.split(",")[0]  # ", finely chopped"
    name = re.sub(r"\s+-\s+.*$", "", name)
    name = re.sub(r"^(van|of|de|het|een)\s+", "", name.strip(), flags=re.IGNORECASE)
    words = [w for w in name.split() if w.lower() not in _SIZE_WORDS]
    return " ".join(words).strip(" .;:")


def _name_key(name: str) -> str:
    key = normalize_text(name)
    if key in _NAME_ALIASES:
        return _NAME_ALIASES[key]
    if len(key) > 4 and key.endswith("s") and not key.endswith(("ss", "us", "is")):
        key = key[:-1]
    return key


@lru_cache(maxsize=20000)
def parse_line(line: str) -> ParsedLine:
    # The translation API sometimes leaves markup or stray symbols around a
    # line ('<g id="1">• </g>75 grams ...') - strip it so the quantity can
    # still be read.
    line = re.sub(r"<[^>]+>", "", line)
    line = re.sub(rf"^[^\w{_VULGAR_CLASS}]+", "", line.strip())
    match = _LINE_RE.match(line)
    if not match or not match.group("rest").strip():
        name = _clean_name(line) or line
        return ParsedLine(None, "", name, _name_key(name))

    qty = _to_number(match.group("b") or match.group("a"))
    rest = match.group("rest").strip()

    unit, factor = "", 1.0
    first, _, remainder = rest.partition(" ")
    alias = first.lower().strip(".,")
    if alias in _UNIT_ALIASES and remainder.strip():
        unit, factor = _UNIT_ALIASES[alias]
        rest = remainder
    elif re.match(r"^(x)\b", rest, flags=re.IGNORECASE):
        rest = rest[1:].strip()

    name = _clean_name(rest)
    if not name:
        return ParsedLine(None, "", _clean_name(line) or line, _name_key(line))
    return ParsedLine(qty * factor, unit, name, _name_key(name))


# --- merging ---------------------------------------------------------------


def _format_number(value: float, lang: str) -> str:
    text = f"{round(value, 2):.2f}".rstrip("0").rstrip(".")
    return text.replace(".", ",") if lang == "nl" else text


def _format_quantity(qty: float, unit: str, lang: str) -> str:
    if unit == "g":
        if qty >= 1000:
            return f"{_format_number(qty / 1000, lang)} kg"
        return f"{_format_number(qty, lang)} g"
    if unit == "ml":
        if qty >= 1000:
            return f"{_format_number(qty / 1000, lang)} l"
        return f"{_format_number(qty, lang)} ml"
    number = _format_number(qty, lang)
    if unit == "":
        return number
    singular, plural = _UNIT_LABELS[unit].get(lang) or _UNIT_LABELS[unit]["en"]
    return f"{number} {singular if abs(qty - 1) < 1e-9 else plural}"


@dataclass(slots=True)
class MergedItem:
    key: str
    name: str
    quantities: dict[str, float]  # canonical unit -> summed quantity
    best_qty: float = 0.0  # largest single quantity seen; picks the display name
    section: str = "other"


def merge_lines(lines: list[str]) -> list[MergedItem]:
    """Groups parsed lines by ingredient name and adds up the quantities
    that share a unit. Order of first appearance is kept."""
    merged: dict[str, MergedItem] = {}
    for line in lines:
        parsed = parse_line(line)
        item = merged.get(parsed.key)
        if item is None:
            item = merged[parsed.key] = MergedItem(parsed.key, parsed.name, {})
        if parsed.qty is not None:
            item.quantities[parsed.unit] = item.quantities.get(parsed.unit, 0.0) + parsed.qty
            if parsed.qty >= item.best_qty:
                # "1 ui" + "2 uien" reads better as "3 uien" than "3 ui".
                item.best_qty = parsed.qty
                item.name = parsed.name
    return list(merged.values())


def format_item(item: MergedItem, lang: str) -> str:
    if not item.quantities:
        return item.name
    parts = [_format_quantity(qty, unit, lang) for unit, qty in item.quantities.items()]
    if len(parts) == 1:
        return f"{parts[0]} {item.name}"
    return f"{item.name} ({' + '.join(parts)})"


# --- supermarket sections --------------------------------------------------


@lru_cache(maxsize=1)
def _sections() -> list[tuple[str, list[str]]]:
    with open(SECTIONS_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [(entry["key"], [normalize_text(k) for k in entry["keywords"]]) for entry in raw]


def section_order() -> list[str]:
    return [key for key, _ in _sections()]


# Section keywords that are an explicit qualifier ("diepvries doperwten")
# outrank the plain product name even at equal length.
_SECTION_BONUS = {"frozen": 5}


@lru_cache(maxsize=20000)
def classify_section(name: str) -> str:
    """Section of the supermarket an ingredient is found in. The longest
    matching keyword wins ('tomatenpuree' beats 'tomaat', 'gepelde tomaten'
    beats 'tomaten'); anything unrecognised lands in 'other'."""
    text = normalize_text(name)
    tokens = _tokenize(text)
    best_key, best_score = "other", 0
    for key, keywords in _sections():
        bonus = _SECTION_BONUS.get(key, 0)
        for kw in keywords:
            score = len(kw) + bonus
            if score > best_score and _term_matches(tokens, text, kw):
                best_key, best_score = key, score
    return best_key
