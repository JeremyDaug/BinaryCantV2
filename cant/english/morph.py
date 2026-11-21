"""Small English morphology: inflection rules plus per-word overrides."""

import re

VOWELS = "aeiou"


def _sibilant(w):
    return re.search(r"(s|x|z|ch|sh)$", w) is not None


def plural(w, forms=None):
    if forms and "pl" in forms:
        return forms["pl"]
    if _sibilant(w):
        return w + "es"
    if re.search(r"[^aeiou]y$", w):
        return w[:-1] + "ies"
    return w + "s"


def third(w, forms=None):
    if forms and "3sg" in forms:
        return forms["3sg"]
    if _sibilant(w) or w.endswith("o"):
        return w + "es"
    if re.search(r"[^aeiou]y$", w):
        return w[:-1] + "ies"
    return w + "s"


def past(w, forms=None):
    if forms and "past" in forms:
        return forms["past"]
    if w.endswith("e"):
        return w + "d"
    if re.search(r"[^aeiou]y$", w):
        return w[:-1] + "ied"
    return w + "ed"


def participle(w, forms=None):
    if forms and "pp" in forms:
        return forms["pp"]
    return past(w, forms)


def gerund(w, forms=None):
    if forms and "ing" in forms:
        return forms["ing"]
    if w.endswith("ie"):
        return w[:-2] + "ying"
    if w.endswith("e") and not w.endswith(("ee", "ye", "oe")) and len(w) > 2:
        return w[:-1] + "ing"
    return w + "ing"


def comparative(w, forms=None):
    """Returns the comparative form, or None when English uses 'more X'."""
    if forms and "cmp" in forms:
        return forms["cmp"]
    if len(w) > 6 or w.endswith(("ful", "ous", "ing", "ed")):
        return None
    if w.endswith("e"):
        return w + "r"
    if re.search(r"[^aeiou]y$", w):
        return w[:-1] + "ier"
    if re.fullmatch(r"[^aeiou]*[aeiou][^aeiouwyx]", w):
        return w + w[-1] + "er"
    return w + "er"


def article(word):
    return "an" if word[:1].lower() in VOWELS and not word.lower().startswith(("uni", "use", "eu")) else "a"


NUMBER_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
                "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
                "nineteen", "twenty"]
TENS = {"thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}


def number_value(tok):
    if tok.isdigit():
        return int(tok)
    if tok in NUMBER_WORDS:
        return NUMBER_WORDS.index(tok)
    if tok in TENS:
        return TENS[tok]
    if tok == "hundred":
        return 100
    if tok == "thousand":
        return 1000
    return None


def number_words(n):
    if 0 <= n <= 20:
        return NUMBER_WORDS[n]
    return str(n)
