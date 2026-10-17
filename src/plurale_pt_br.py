"""Brazilian Portuguese plural rules for Guild Wars 2 translation templates.
Baseado no script original adaptado para GW2.

singular + inglês -> texto com os marcadores do jogo:
    "Medalha precisa em juta"  ->  'Medalha[pl:"Medalhas"] precisa[pl:"precisas"] em juta'

Mudam-se apenas as primeiras palavras (o nome e seus adjetivos), até a primeira preposição,
dois pontos, vírgula ou parêntese. As palavras que aparecem também no inglês (nomes próprios,
termos do glossário deixados em inglês) não são tocadas. Se houver também a tradução
ao plural do modelo, alinhada palavra por palavra, as palavras mais à frente que o modelo
colocou no plural do mesmo modo das regras recebem também o marcador.
"""
from __future__ import annotations

import re

SPLIT_RE = re.compile(r"(\s+)")
EDGE_RE = re.compile(r"^([^\w%<\[]*)(.*?)([^\w%>\]]*)$", re.S)
WORD_RE = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ]+$")
EXISTING_MARKER_RE = re.compile(r'\[pl:"[^"\[\]\n]*"\]')

# A parte a ser colocada no plural termina aqui
STOP = {
    "de", "do", "da", "dos", "das", "dum", "duma", "duns", "dumas",
    "em", "no", "na", "nos", "nas", "num", "numa", "nuns", "numas",
    "por", "pelo", "pela", "pelos", "pelas",
    "a", "ao", "à", "aos", "às",
    "com", "sem", "contra", "sob", "sobre", "entre", "perante",
    "após", "desde", "até", "perto", "conforme", "segundo",
    "e", "ou", "mas", "porém", "contudo", "todavia", "como", "que", "depois", "antes",
}
ARTICLES = {"o": "os", "a": "as", "um": "uns", "uma": "umas"}
NO_PLURAL = {"um", "uma", "uns", "umas"}

IRREGULAR = {
    "cidadão": "cidadãos", "capitão": "capitães", "cão": "cães",
    "pão": "pães", "mão": "mãos", "vilão": "vilões", "cirurgião": "cirurgiões",
    "irmão": "irmãos", "cristão": "cristãos", "órfão": "órfãos", "órgão": "órgãos",
    "avião": "aviões", "botão": "botões", "coração": "corações", "dragão": "dragões",
    "leão": "leões", "limão": "limões", "melão": "melões", "fogão": "fogões",
    "vulcão": "vulcões",
    "guardião": "guardiões", "pião": "piões", "anão": "anões",
    "mulher": "mulheres", "mar": "mares", "lápis": "lápis", "ônibus": "ônibus",
    "vírus": "vírus", "tênis": "tênis", "atlas": "atlas", "pires": "pires",
    "fóssil": "fósseis", "réptil": "répteis", "projétil": "projéteis", "infantil": "infantis",
    "fácil": "fáceis", "difícil": "difíceis", "útil": "úteis", "inútil": "inúteis",
    "quilômetro": "quilômetros", "revólver": "revólveres", "caráter": "caracteres",
    "júnior": "júniores", "sênior": "seniores", "deus": "deuses", "barão": "barões",
    "anel": "anéis",
    "grão": "grãos", "sacristão": "sacristãos", "alemão": "alemães",
}

INVARIABLE = {
    "lápis", "ônibus", "vírus", "tênis", "atlas", "pires", "clímax", "tórax",
    "fênix", "status", "campus", "bônus", "arco-íris", "mini", "maxi", "super",
    "extra", "standard", "grátis", "simples",
}

APPOSITION = {
    "esmeralda", "rubi", "safira", "ouro", "prata", "bronze", "cobre", "ferro", "aço",
    "base", "sombra", "vinho", "noite", "fogo", "gelo", "sol", "lua", "céu", "mar",
    "tempestade", "dragão", "fantasma", "espírito", "mini", "extra", "standard", "premium",
}


def _case(model: str, word: str) -> str:
    if model.isupper() and len(model) > 1:
        return word.upper()
    return word[:1].upper() + word[1:] if model[:1].isupper() else word


def plural_word(word: str) -> str | None:
    """Plural de um nome ou adjetivo em português; None se não souber."""
    w = word.lower()
    if not WORD_RE.match(word):
        return None
    if w in IRREGULAR:
        return _case(word, IRREGULAR[w])
    if w in INVARIABLE or w[-1] in "êîôû" or len(w) < 2:
        return word
    
    if w.endswith("ão"):
        if w in {"alemão", "cão", "pão", "capitão", "sacristão", "charlatão"}:
            if w == "alemão": return _case(word, "alemães")
            if w in {"cão", "pão"}: return _case(word, w[:-2] + "ães")
            if w == "capitão": return _case(word, "capitães")
            if w in {"sacristão", "charlatão"}: return _case(word, w[:-2] + "ãos")
        if w.endswith(("mão", "fão", "chão", "órfão", "sótão", "acórdão", "bênção", "órgão")):
            return _case(word, w + "s")
        return _case(word, w[:-2] + "ões")

    if w.endswith("al"):
        return _case(word, w[:-2] + "ais")
    if w.endswith("el"):
        return _case(word, w[:-2] + "éis")
    if w.endswith("ol"):
        return _case(word, w[:-2] + "óis")
    if w.endswith("ul"):
        return _case(word, w[:-2] + "uis")
    if w.endswith("il"):
        if w in {"fácil", "difícil", "útil", "inútil", "réptil", "fóssil", "projétil"}:
            return _case(word, w[:-2] + "eis")
        return _case(word, w[:-2] + "is")

    if w.endswith(("r", "z", "n")):
        return _case(word, w + "es")
    if w.endswith("s"):
        return None

    if w.endswith("m"):
        return _case(word, w[:-1] + "ns")
    if w.endswith(("a", "e", "o", "i", "u", "á", "é", "ó", "ú", "ã", "õ")):
        return _case(word, w + "s")

    return None


def make_plural(sing: str, english: str, plur_model: str | None = None) -> tuple[str, str, list]:
    """Retorna (texto com marcadores, resultado, palavras alteradas)."""
    if EXISTING_MARKER_RE.search(sing):
        return sing, "já possui marcadores", []
    eng_words = {x.lower() for x in re.findall(r"[A-Za-zÀ-ÿ]+", english)}
    toks = SPLIT_RE.split(sing.strip())
    words = [i for i, t in enumerate(toks) if not t.isspace()]
    ptoks = SPLIT_RE.split(plur_model.strip()) if plur_model else None
    aligned = ptoks is not None and len(ptoks) == len(toks)
    out, changed, doubt, head = list(toks), [], [], True
    for n, i in enumerate(words):
        lead, core, trail = EDGE_RE.match(toks[i]).groups()
        low = core.lower()
        if head and (low in STOP or lead):
            head = False
        if head:
            if n == 0 and (low in NO_PLURAL or "'" in core or "’" in core):
                doubt.append(core)
                head = False
            elif low in ARTICLES:
                out[i] = f'{lead}{core}[pl:"{_case(core, ARTICLES[low])}"]{trail}'
                changed.append(f"{core}>{ARTICLES[low]}")
            elif WORD_RE.match(core) and low not in eng_words:
                pl = plural_word(core)
                same_in_model = (aligned and changed and EDGE_RE.match(ptoks[i]).groups()[1] == core)
                if same_in_model or (changed and low in APPOSITION):
                    pass
                elif pl is None:
                    doubt.append(core)
                elif pl != core:
                    out[i] = f'{lead}{core}[pl:"{pl}"]{trail}'
                    changed.append(f"{core}>{pl}")
            if trail and any(c in trail for c in ":,;(–—"):
                head = False
            continue
        if aligned and WORD_RE.match(core) and low not in eng_words and low not in STOP:
            pcore = EDGE_RE.match(ptoks[i]).groups()[1]
            pl = plural_word(core)
            if pl and pl != core and pl.lower() == pcore.lower():
                out[i] = f'{lead}{core}[pl:"{pl}"]{trail}'
                changed.append(f"{core}>{pl} (confirmado)")
    if doubt:
        esito = "dúvida: " + ", ".join(doubt)
    elif not changed:
        esito = "invariável"
    else:
        esito = "ok"
    return "".join(out), esito, changed


# --------------------------------------------------------------------------- FRASES COM %num%
NUM_TOKEN_RE = re.compile(r"%num\d*%")
EN_MARK_RE = re.compile(r'(?<=\w)\[s\]|[\w\'’-]+\[pl:"([^"\[\]\n]*)"\]')
IT_MARK_RE = re.compile(r'\[pl:"[^"\[\]\n]*"\]')
ALPHA_RE = re.compile(r"[^\W\d_]+")
CLAUSE_END = set(".,;:!?()[]<>\"«»–—/")
ADVERBS = {"ainda", "já", "sempre", "só", "somente", "também", "pois", "mais", "menos", "nunca",
           "não", "cada", "cerca", "pelo", "quase", "junto", "subitamente", "além", "total"}
SEG_STOP = STOP | ADVERBS | {
    "durante", "enquanto", "dentro", "além", "até", "quando", "se", "no", "na", "num", "numa",
    "pelo", "pela", "sob", "sobre", "entre", "o", "a", "os", "as", "um", "uma", "uns", "umas",
    "é", "são", "tem", "têm"}
PLURAL_DET = {"os", "as", "dos", "das", "nos", "nas", "aos", "às", "pelos", "pelas", "estes", "estas",
              "esses", "essas", "aqueles", "aquelas", "todos", "todas", "outros", "outras", "teus", "tuas",
              "seus", "suas", "vossos", "vossas", "nossos", "nossas", "alguns", "algumas", "diversos",
              "diversas", "vários", "várias", "muitos", "muitas", "poucos", "poucas"}
TAIL_LINK = {"de", "do", "da", "dos", "das", "em", "no", "na", "por", "pelo", "pela", "a", "ao", "à",
             "com", "sob", "sobre", "o", "a", "os", "as", "um", "uma"}
ADJ_RE = re.compile(r"(?:ado|ido|ável|ível|ante|ente|al|el|ar)[s]?$")
GERUND_RE = re.compile(r"[ae]ndo$")

SUFFIX = [("ções", "ção"), ("sões", "são"), ("istas", "ista"), ("osos", "oso"), ("osas", "osa"),
          ("ivos", "ivo"), ("ivas", "iva"), ("atos", "ato"), ("atas", "ata"), ("itos", "ito"),
          ("itas", "ita"), ("utos", "uto"), ("utas", "uta"), ("antes", "ante"), ("entes", "ente"),
          ("tores", "tor"), ("icos", "ico"), ("icas", "ica"), ("ais", "al"), ("eis", "el"),
          ("ois", "ol"), ("uis", "ul")]
REV_IRREGULAR = {v: k for k, v in IRREGULAR.items() if v != k}
SAME = {k for k, v in IRREGULAR.items() if v == k}
MIN_COUNT = 2
DOUBT = 0.3


def rules_data(version: int = 1) -> dict:
    """Return the rule data format that can be reviewed and updated independently of this code."""
    return {
        "version": version,
        "stop": sorted(STOP),
        "articles": ARTICLES,
        "no_plural": sorted(NO_PLURAL),
        "irregular": IRREGULAR,
        "invariable": sorted(INVARIABLE),
        "apposition": sorted(APPOSITION),
        "adverbs": sorted(ADVERBS),
        "plural_det": sorted(PLURAL_DET),
        "tail_link": sorted(TAIL_LINK),
        "seg_stop": sorted(SEG_STOP),
        "clause_end": sorted(CLAUSE_END),
        "suffix": [list(pair) for pair in SUFFIX],
        "min_count": MIN_COUNT,
        "doubt": DOUBT,
        "adjective_pattern": ADJ_RE.pattern,
        "gerund_pattern": GERUND_RE.pattern,
    }


def validate_rules(data: dict) -> dict:
    """Validate and normalize a complete, versioned rules document without applying it."""
    if not isinstance(data, dict):
        raise ValueError("plural rules must be an object")
    version = data.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ValueError("plural rules: invalid version")
    list_fields = ("stop", "no_plural", "invariable", "apposition", "adverbs",
                   "plural_det", "tail_link", "seg_stop", "clause_end")
    normalized = {"version": version}
    for field in list_fields:
        values = data.get(field)
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise ValueError(f"plural rules: {field!r} must be an array of strings")
        normalized[field] = values
    for field in ("articles", "irregular"):
        values = data.get(field)
        if not isinstance(values, dict) or any(
                not isinstance(key, str) or not isinstance(value, str)
                for key, value in values.items()):
            raise ValueError(f"plural rules: {field!r} must be a string map")
        normalized[field] = values
    suffix = data.get("suffix")
    if not isinstance(suffix, list) or any(
            not isinstance(pair, list) or len(pair) != 2
            or any(not isinstance(value, str) for value in pair) for pair in suffix):
        raise ValueError("plural rules: 'suffix' must be an array of string pairs")
    normalized["suffix"] = suffix
    min_count, doubt = data.get("min_count"), data.get("doubt")
    if not isinstance(min_count, int) or isinstance(min_count, bool) or min_count < 1:
        raise ValueError("plural rules: 'min_count' must be a positive integer")
    if not isinstance(doubt, (int, float)) or isinstance(doubt, bool) or not 0 <= doubt <= 1:
        raise ValueError("plural rules: 'doubt' must be between 0 and 1")
    normalized["min_count"], normalized["doubt"] = min_count, float(doubt)
    for field in ("adjective_pattern", "gerund_pattern"):
        pattern = data.get(field)
        if not isinstance(pattern, str):
            raise ValueError(f"plural rules: {field!r} must be a regular expression")
        try:
            re.compile(pattern)
        except re.error as exc:
            raise ValueError(f"plural rules: invalid {field}: {exc}") from exc
        normalized[field] = pattern
    return normalized


def load_rules(data: dict) -> int:
    """Apply validated plural rule data and return its version."""
    rules = validate_rules(data)
    global STOP, ARTICLES, NO_PLURAL, IRREGULAR, INVARIABLE, APPOSITION
    global ADVERBS, PLURAL_DET, TAIL_LINK, SEG_STOP, CLAUSE_END, SUFFIX
    global REV_IRREGULAR, SAME, MIN_COUNT, DOUBT, ADJ_RE, GERUND_RE
    STOP = set(rules["stop"])
    ARTICLES = dict(rules["articles"])
    NO_PLURAL = set(rules["no_plural"])
    IRREGULAR = dict(rules["irregular"])
    INVARIABLE = set(rules["invariable"])
    APPOSITION = set(rules["apposition"])
    ADVERBS = set(rules["adverbs"])
    PLURAL_DET = set(rules["plural_det"])
    TAIL_LINK = set(rules["tail_link"])
    SEG_STOP = set(rules["seg_stop"])
    CLAUSE_END = set(rules["clause_end"])
    SUFFIX = [tuple(pair) for pair in rules["suffix"]]
    REV_IRREGULAR = {v: k for k, v in IRREGULAR.items() if v != k}
    SAME = {k for k, v in IRREGULAR.items() if v == k}
    MIN_COUNT, DOUBT = rules["min_count"], rules["doubt"]
    ADJ_RE = re.compile(rules["adjective_pattern"])
    GERUND_RE = re.compile(rules["gerund_pattern"])
    return rules["version"]


def num_vocabulary(texts) -> dict[str, int]:
    voc: dict[str, int] = {}
    for t in texts:
        update_num_vocabulary(voc, t)
    return voc


def update_num_vocabulary(voc: dict[str, int], text: str, delta: int = 1) -> None:
    for word in ALPHA_RE.findall(IT_MARK_RE.sub("", text).lower()):
        count = voc.get(word, 0) + delta
        if count > 0:
            voc[word] = count
        else:
            voc.pop(word, None)


def singular_candidates(w: str) -> list[str]:
    c = []
    if w.endswith("ões"):
        c.append(w[:-3] + "ão")
    elif w.endswith("ães"):
        c.append(w[:-3] + "ão")
    elif w.endswith("ãos"):
        c.append(w[:-3] + "ão")
    elif w.endswith("is"):
        c += [w[:-2] + "l", w[:-2] + "el", w[:-2] + "il", w[:-2] + "z"]
    elif w.endswith("eis"):
        c += [w[:-3] + "el", w[:-3] + "il"]
    elif w.endswith("ois"):
        c.append(w[:-3] + "ol")
    elif w.endswith("uis"):
        c.append(w[:-3] + "ul")
    elif w.endswith("es"):
        c += [w[:-2], w[:-2] + "r", w[:-2] + "z", w[:-2] + "s"]
    elif w.endswith("ns"):
        c.append(w[:-2] + "m")
    elif w.endswith("s"):
        c.append(w[:-1])
    return [x for x in dict.fromkeys(c) if x != w and len(x) >= 3]


def singular_of(word: str, voc: dict[str, int], en_voc: set[str]) -> tuple[str | None, str]:
    w = word.lower()
    if w in REV_IRREGULAR:
        return _case(word, REV_IRREGULAR[w]), ""
    scored = []
    for cand in singular_candidates(w):
        n = voc.get(cand, 0)
        if n >= MIN_COUNT:
            scored.append((n, cand))
    if len(scored) > 1:
        it_only = [x for x in scored if x[1] not in en_voc]
        scored = it_only or scored
    if not scored:
        for end, sing in SUFFIX:
            if w.endswith(end) and len(w) > len(end) + 1:
                return _case(word, w[:-len(end)] + sing), ""
        return None, "singular desconhecido"
    scored.sort(reverse=True)
    if len(scored) > 1 and scored[1][0] >= DOUBT * scored[0][0]:
        return None, f"singular incerto ({scored[0][1]}/{scored[1][1]})"
    return _case(word, scored[0][1]), ""


def adjective(low: str, sing: str, voc: dict[str, int]) -> bool:
    if ADJ_RE.search(low):
        return True
    s = sing.lower()
    if s[-1:] in ("o", "a"):
        other = s[:-1] + ("a" if s.endswith("o") else "o")
        return voc.get(s, 0) >= MIN_COUNT and voc.get(other, 0) >= MIN_COUNT
    return False


def fixed_form(low: str, voc: dict[str, int]) -> bool:
    """Verifica se a palavra é invariável em número no português."""
    if low in INVARIABLE or low in SAME:
        return True
    return low.endswith("s") and not any(
        voc.get(candidate, 0) >= MIN_COUNT for candidate in singular_candidates(low)
    )


def marker_nums(text: str, mark_re) -> list[str | None]:
    nums = [(m.start(), m.group(0)) for m in NUM_TOKEN_RE.finditer(text)]
    seq = []
    for m in mark_re.finditer(text):
        prev = [n for p, n in nums if p < m.start()]
        b = prev[-1] if prev else None
        if not seq or seq[-1] != b:
            seq.append(b)
    return seq


def english_plurals(english: str, sing_fn, plur_fn) -> dict[str, str]:
    a, b = sing_fn(english).split(), plur_fn(english).split()
    out = {}
    if len(a) == len(b):
        for s, p in zip(a, b):
            s, p = s.strip(".,;:!?\"()"), p.strip(".,;:!?\"()")
            if s != p and ALPHA_RE.fullmatch(s) and ALPHA_RE.fullmatch(p):
                out[p.lower()] = s
    return out


def num_markers(english: str, it: str, voc: dict[str, int], en_voc: set[str],
                sing_fn, plur_fn) -> tuple[str, str]:
    if "\n" in it or IT_MARK_RE.search(it):
        return it, "salto: quebra de linha ou marcadores já presentes"
    eng_words = {x.lower() for x in ALPHA_RE.findall(EN_MARK_RE.sub("", english))}
    en_pl = english_plurals(english, sing_fn, plur_fn)
    toks = re.split(r"(\s+)", it)
    out = list(toks)
    marks, reasons = 0, []
    for i, t in enumerate(toks):
        nm = list(NUM_TOKEN_RE.finditer(t))
        if not nm or not t.endswith(nm[-1].group(0)) or i + 2 >= len(toks):
            continue
        if i >= 2 and toks[i - 2].lower() in PLURAL_DET:
            reasons.append(f"'{toks[i - 2]}' antes do número")
            continue
        head, k, ok, last_letter = [], i + 2, True, None
        while k < len(toks) and len(head) < 6:
            lead, core, trail = EDGE_RE.match(toks[k]).groups()
            low = core.lower()
            if (lead or not core or low in SEG_STOP or not WORD_RE.match(core)
                    or GERUND_RE.search(low)):
                break
            if low in en_pl:
                head.append((k, lead, en_pl[low], core, trail))
                last_letter = None
            elif fixed_form(low, voc):
                head.append((k, None, None, core, trail))
            else:
                s, why = singular_of(core, voc, en_voc)
                if s is None:
                    if low in eng_words:
                        head.append((k, None, None, core, trail))
                    else:
                        ok = False
                        reasons.append(f"{core}: {why}")
                        break
                else:
                    head.append((k, lead, s, core, trail))
                    last_letter = low[-1]
            k += 2
            if trail:
                break
        marked = [h for h in head if h[2]]
        if not ok or not marked:
            continue
        tail = []
        trail0 = head[-1][4] if head else ""
        if last_letter in ("s", "is", "es") and not any(c in CLAUSE_END for c in trail0):
            linked = False
            while k < len(toks):
                lead, core, trail = EDGE_RE.match(toks[k]).groups()
                low = core.lower()
                if lead or not core or NUM_TOKEN_RE.search(toks[k]):
                    break
                if low in TAIL_LINK:
                    linked = True
                elif re.fullmatch(r"\d+", core) or not WORD_RE.match(core):
                    pass
                elif low in PLURAL_DET or low in SEG_STOP:
                    break
                else:
                    s = None if fixed_form(low, voc) else singular_of(core, voc, en_voc)[0]
                    if s is not None:
                        if linked and adjective(low, s, voc):
                            tail.append((k, lead, s, core, trail))
                        else:
                            break
                if trail and any(c in CLAUSE_END for c in trail):
                    break
                k += 2
        for k2, lead, s, core, trail in marked + tail:
            out[k2] = f'{lead}{s}[pl:"{core}"]{trail}'
            marks += 1
    if not marks:
        return it, "; ".join(reasons) or "nenhum nome após os números"
    res = "".join(out)
    if marker_nums(english, EN_MARK_RE) != marker_nums(res, IT_MARK_RE):
        return it, "marcadores ligados a números diferentes do inglês"
    return res, "ok"