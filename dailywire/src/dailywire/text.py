"""Text utilities: hashing for dedupe, and shaping prose for the ear.

The "written for the ear" rules in the prompt are also enforced mechanically
here, because language models drift: a stray URL or a bare "1,200" slips
through often enough that a deterministic pass afterwards is worth having.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

_WORD_RE = re.compile(r"[a-z0-9']+")
_URL_RE = re.compile(r"https?://\S+|\bwww\.\S+", re.IGNORECASE)
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\((?:[^)]+)\)")
_BULLET_RE = re.compile(r"^\s*(?:[-*•‣▪]|\d+[.)])\s+", re.MULTILINE)
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)
_EMPHASIS_RE = re.compile(r"(\*\*|__|\*|_|`)")
_MULTISPACE_RE = re.compile(r"[ \t]{2,}")

# Domains that appear inside prose without a scheme, e.g. "arstechnica.com".
# Deliberately case-sensitive: people write domains in lowercase, while the
# things that would otherwise be caught here -- "cs.AI", "cs.LG" -- are not.
_BARE_DOMAIN_RE = re.compile(
    r"\b(?:[a-z0-9-]+\.)+(?:com|org|net|io|ai|gov|edu|co\.uk|dev|news)\b(?:/\S*)?"
)


def normalize(text: str) -> str:
    """Lowercase, strip accents and punctuation. Used for hashing/comparison."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(_WORD_RE.findall(text.lower()))


def url_hash(url: str) -> str:
    """Stable hash of a URL, ignoring tracking parameters and trailing slashes."""
    url = url.strip()
    url = re.sub(r"[?&](utm_[^=]+|ref|ref_src|src|cmpid|fbclid|gclid)=[^&]*", "", url)
    url = re.sub(r"^https?://(www\.)?", "", url, flags=re.IGNORECASE)
    url = url.rstrip("/?&#")
    return hashlib.sha256(url.lower().encode("utf-8")).hexdigest()[:32]


SHINGLE_CHARS = 4


def simhash(text: str, bits: int = 64) -> int:
    """Charikar simhash over character 4-grams of the normalised text.

    Character shingles rather than word shingles: headlines are short, so a
    single added word moves a word-shingle hash almost as far as an unrelated
    headline does. Measured over sample pairs, character 4-grams put genuine
    near-duplicates ("Foo acquires Bar" vs "Foo acquires Bar for $2B") within
    11 bits while unrelated headlines stay past 27 -- hence the threshold of
    16 in store.py.
    """
    normalized = normalize(text)
    if not normalized:
        return 0
    shingles = [
        normalized[i : i + SHINGLE_CHARS]
        for i in range(max(1, len(normalized) - SHINGLE_CHARS + 1))
    ]
    vector = [0] * bits
    for shingle in shingles:
        h = int.from_bytes(hashlib.blake2b(shingle.encode("utf-8"), digest_size=8).digest(), "big")
        for i in range(bits):
            vector[i] += 1 if (h >> i) & 1 else -1
    out = 0
    for i, v in enumerate(vector):
        if v > 0:
            out |= 1 << i
    return out


_MASK64 = (1 << 64) - 1


def hamming(a: int, b: int) -> int:
    # Mask so that a value round-tripped through SQLite's signed integers
    # (and therefore negative) still compares correctly.
    return bin((a ^ b) & _MASK64).count("1")


def to_signed64(value: int) -> int:
    """SQLite INTEGER is signed 64-bit; simhashes are unsigned."""
    value &= _MASK64
    return value - (1 << 64) if value >= (1 << 63) else value


def from_signed64(value: int) -> int:
    return value & _MASK64


# --------------------------------------------------------------------------
# Number spelling
# --------------------------------------------------------------------------

_ONES = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen",
]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
_SCALES = [(1_000_000_000_000, "trillion"), (1_000_000_000, "billion"), (1_000_000, "million"), (1_000, "thousand")]


def spell_integer(n: int) -> str:
    """Render an integer as English words."""
    if n < 0:
        return "minus " + spell_integer(-n)
    if n < 20:
        return _ONES[n]
    if n < 100:
        tens, rest = divmod(n, 10)
        return _TENS[tens] + (f"-{_ONES[rest]}" if rest else "")
    if n < 1000:
        hundreds, rest = divmod(n, 100)
        out = f"{_ONES[hundreds]} hundred"
        return out + (f" {spell_integer(rest)}" if rest else "")
    for value, name in _SCALES:
        if n >= value:
            count, rest = divmod(n, value)
            out = f"{spell_integer(count)} {name}"
            return out + (f" {spell_integer(rest)}" if rest else "")
    return str(n)


def spell_year(n: int) -> str:
    """1998 -> nineteen ninety-eight; 2007 -> two thousand seven."""
    if 1100 <= n < 2000 or 2100 <= n < 3000:
        high, low = divmod(n, 100)
        if low == 0:
            return f"{spell_integer(high)} hundred"
        if low < 10:
            return f"{spell_integer(high)} oh {_ONES[low]}"
        return f"{spell_integer(high)} {spell_integer(low)}"
    return spell_integer(n)


_ORDINAL_WORDS = {
    "1": "first", "2": "second", "3": "third", "4": "fourth", "5": "fifth",
    "6": "sixth", "7": "seventh", "8": "eighth", "9": "ninth", "10": "tenth",
    "11": "eleventh", "12": "twelfth", "13": "thirteenth", "20": "twentieth",
    "21": "twenty-first", "30": "thirtieth", "31": "thirty-first",
}

_CURRENCY = {"$": ("dollars", "dollar"), "£": ("pounds", "pound"), "€": ("euros", "euro"), "¥": ("yen", "yen")}
_MAGNITUDE = {"k": "thousand", "m": "million", "b": "billion", "bn": "billion", "t": "trillion", "tn": "trillion"}


def _spell_decimal(token: str) -> str:
    """'3.5' -> 'three point five'; '0.25' -> 'zero point two five'."""
    whole, _, frac = token.partition(".")
    whole_words = spell_integer(int(whole)) if whole else "zero"
    if not frac:
        return whole_words
    digits = " ".join(_ONES[int(d)] for d in frac)
    return f"{whole_words} point {digits}"


def _number_words(raw: str, *, allow_year: bool = True) -> str:
    """Spell out a plain number token (may contain commas and a decimal point).

    `allow_year` is off wherever the number is qualified by a unit -- "$1,200"
    is twelve hundred dollars to nobody.
    """
    token = raw.replace(",", "")
    if "." in token:
        return _spell_decimal(token)
    value = int(token)
    # Bare 4-digit numbers in news prose are almost always years.
    if allow_year and 1100 <= value <= 2999 and len(token) == 4:
        return spell_year(value)
    return spell_integer(value)


def spell_out_numbers(text: str) -> str:
    """Replace numerals with spoken-word equivalents.

    Handles ordinals, percentages, currency with magnitude suffixes, decimals
    and plain integers. Leaves version-like tokens (GPT-4, R128) alone --
    those read fine as-is and mangling them hurts more than it helps.
    """

    def ordinal(m: re.Match[str]) -> str:
        digits = m.group(1)
        if digits in _ORDINAL_WORDS:
            return _ORDINAL_WORDS[digits]
        return spell_integer(int(digits)) + m.group(2)

    def currency(m: re.Match[str]) -> str:
        symbol, amount, suffix = m.group(1), m.group(2), (m.group(3) or "").lower()
        plural, singular = _CURRENCY[symbol]
        words = _number_words(amount, allow_year=False)
        unit = plural
        if amount.replace(",", "") == "1" and not suffix:
            unit = singular
        if suffix:
            return f"{words} {_MAGNITUDE[suffix]} {plural}"
        return f"{words} {unit}"

    def percent(m: re.Match[str]) -> str:
        return f"{_number_words(m.group(1), allow_year=False)} percent"

    def magnitude(m: re.Match[str]) -> str:
        return f"{_number_words(m.group(1), allow_year=False)} {_MAGNITUDE[m.group(2).lower()]}"

    def plain(m: re.Match[str]) -> str:
        return _number_words(m.group(0))

    # Order matters: the more specific patterns run first.
    text = re.sub(r"\b(\d+)(st|nd|rd|th)\b", ordinal, text)
    text = re.sub(
        r"([$£€¥])\s?(\d[\d,]*(?:\.\d+)?)(?:\s?(bn|tn|[kmbt])\b)?",
        currency,
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\b(\d[\d,]*(?:\.\d+)?)\s?(?:%|\bpercent\b)", percent, text)
    text = re.sub(r"\b(\d[\d,]*(?:\.\d+)?)\s?(bn|tn|[kmbt])\b(?!\w)", magnitude, text)
    # Plain numbers, but not ones glued to a letter (GPT-4, H100, R128, 5G).
    text = re.sub(r"(?<![\w$£€¥.-])\d[\d,]*(?:\.\d+)?(?![\w%])", plain, text)
    return text


# --------------------------------------------------------------------------
# Speakability
# --------------------------------------------------------------------------

_SYMBOLS = {
    "&": " and ",
    "@": " at ",
    "#": " number ",
    "~": " about ",
    "+": " plus ",
    "=": " equals ",
    "/": " slash ",
    "…": "...",
    "—": " -- ",
    "–": " -- ",
    "“": '"', "”": '"', "‘": "'", "’": "'",
}


def strip_markup(text: str) -> str:
    """Remove markdown scaffolding that has no spoken equivalent."""
    text = _MD_LINK_RE.sub(r"\1", text)
    text = _HEADING_RE.sub("", text)
    text = _BULLET_RE.sub("", text)
    text = _EMPHASIS_RE.sub("", text)
    return text


def strip_urls(text: str) -> str:
    text = _URL_RE.sub("", text)
    text = _BARE_DOMAIN_RE.sub(lambda m: m.group(0).split(".")[0], text)
    return text


def speakable(text: str, *, numbers: bool = True, urls: bool = True) -> str:
    """Full spoken-word cleanup pass over generated script text."""
    text = strip_markup(text)
    if urls:
        text = strip_urls(text)
    # "/" is a slash only between words, not inside a stripped URL remnant.
    for symbol, replacement in _SYMBOLS.items():
        text = text.replace(symbol, replacement)
    if numbers:
        text = spell_out_numbers(text)
    text = _MULTISPACE_RE.sub(" ", text)
    text = re.sub(r" +([,.;:!?])", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()


def lint_speakable(text: str) -> list[str]:
    """Report anything left that a listener would trip over."""
    problems: list[str] = []
    if _URL_RE.search(text):
        problems.append("contains a URL")
    if _BULLET_RE.search(text):
        problems.append("contains bullet points")
    if _HEADING_RE.search(text):
        problems.append("contains markdown headings")
    digits = re.findall(r"(?<![\w-])\d[\d,]*(?![\w-])", text)
    if digits:
        problems.append(f"contains bare numerals: {', '.join(digits[:5])}")
    return problems


def estimate_duration_seconds(text: str, words_per_minute: int = 155) -> float:
    return len(text.split()) / max(1, words_per_minute) * 60.0


def chunk_text(text: str, max_chars: int = 1800) -> list[str]:
    """Split text into TTS-sized chunks on sentence, then word, boundaries."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        while len(sentence) > max_chars:  # pathological single sentence
            cut = sentence.rfind(" ", 0, max_chars)
            cut = cut if cut > 0 else max_chars
            if current:
                chunks.append(current.strip())
                current = ""
            chunks.append(sentence[:cut].strip())
            sentence = sentence[cut:].lstrip()
        if len(current) + len(sentence) + 1 > max_chars and current:
            chunks.append(current.strip())
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if c]
