"""Brazilian Portuguese plural markers for Guild Wars 2 translated names."""
from __future__ import annotations

import re

SPLIT_RE = re.compile(r"(\s+)")
EDGE_RE = re.compile(r"^([^\w%<\[]*)(.*?)([^\w%>\]]*)$", re.S)
WORD_RE = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ]+$")
STOP = {"a", "ao", "aos", "as", "com", "da", "das", "de", "do", "dos", "e", "em", "na", "nas", "no", "nos", "ou", "para", "por", "sem", "sob"}
ARTICLES = {"o": "os", "a": "as"}
NO_PLURAL = {"um", "uma", "uns", "umas"}
IRREGULAR = {"cão": "cães", "mão": "mãos", "pão": "pães", "alemão": "alemães", "capitão": "capitães", "cidadão": "cidadãos", "cristão": "cristãos", "irmão": "irmãos", "órgão": "órgãos", "órfão": "órfãos", "guardião": "guardiões", "vilão": "vilões", "leão": "leões", "dragão": "dragões", "coração": "corações", "missão": "missões", "homem": "homens", "mulher": "mulheres", "jovem": "jovens"}


def _case(original: str, plural: str) -> str:
    if original.isupper() and len(original) > 1:
        return plural.upper()
    if original[:1].isupper():
        return plural[:1].upper() + plural[1:]
    return plural


def plural_word(word: str) -> str | None:
    """Return a conservative Brazilian Portuguese plural, or None if the token is not Portuguese."""
    if not WORD_RE.fullmatch(word):
        return None
    low = word.lower()
    if low in IRREGULAR:
        return _case(word, IRREGULAR[low])
    if low.endswith(("s", "x")):
        if low.endswith("s") and low.endswith("ês"):
            return _case(word, low[:-2] + "eses")
        return word
    if low.endswith("m"):
        return _case(word, low[:-1] + "ns")
    if low.endswith("ão"):
        return _case(word, low[:-2] + "ões")
    if low.endswith("al"):
        return _case(word, low[:-2] + "ais")
    if low.endswith("el"):
        return _case(word, low[:-2] + "éis")
    if low.endswith("ol"):
        return _case(word, low[:-2] + "óis")
    if low.endswith("ul"):
        return _case(word, low[:-2] + "uis")
    if low.endswith("il"):
        return _case(word, low[:-2] + ("is" if len(low) > 3 else "eis"))
    return _case(word, word + "s")


def make_plural(singular: str, english: str, plural_model: str | None = None) -> tuple[str, str, list[str]]:
    """Add GW2 [pl:"..."] markers to the leading translated noun phrase."""
    english_words = {w.lower() for w in re.findall(r"[A-Za-zÀ-ÿ]+", english)}
    tokens = SPLIT_RE.split(singular.strip())
    words = [i for i, token in enumerate(tokens) if token and not token.isspace()]
    plural_tokens = SPLIT_RE.split(plural_model.strip()) if plural_model else None
    aligned = plural_tokens is not None and len(plural_tokens) == len(tokens)
    out = list(tokens)
    changed: list[str] = []
    head = True
    for pos, i in enumerate(words):
        lead, core, trail = EDGE_RE.fullmatch(tokens[i]).groups()
        low = core.lower()
        if head and ((low in STOP and low not in ARTICLES) or lead):
            head = False
        if not head:
            continue
        if pos == 0 and (low in NO_PLURAL or "'" in core or "’" in core):
            head = False
            continue
        if low in ARTICLES:
            form = ARTICLES[low]
            out[i] = f'{lead}{core}[pl:"{_case(core, form)}"]{trail}'
            changed.append(f"{core}>{form}")
        elif WORD_RE.fullmatch(core) and low not in english_words:
            form = plural_word(core)
            same_in_model = aligned and plural_tokens[i] == tokens[i]
            if form is None:
                head = False
            elif form != core and not same_in_model:
                out[i] = f'{lead}{core}[pl:"{form}"]{trail}'
                changed.append(f"{core}>{form}")
        if any(mark in trail for mark in ":,;("):
            head = False
    return "".join(out), "ok" if changed else "invariavel", changed