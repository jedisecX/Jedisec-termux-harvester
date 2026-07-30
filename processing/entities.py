"""Zero-dependency entity extraction.

No spaCy, no numpy, no thinc/blis -- nothing beyond the stdlib `re`
module. That's a deliberate trade: a trained NER model tags more
accurately, but spaCy's dependency chain (numpy + thinc + blis, all
with C/Cython extensions) is genuinely painful on Termux -- there are
no Android/aarch64 wheels for most of it, so pip falls back to
compiling from source against toolchains Termux doesn't ship by
default. This tagger trades some precision/recall for "installs
instantly everywhere, including a phone."

Approach: gazetteer + regex heuristics, four categories:
  DATE   - regex (month-name and numeric date formats)
  GPE    - gazetteer match against US states + a country list
  ORG    - runs of Title-Case words containing a known org keyword
           (Department, Commission, University, ...)
  PERSON - runs of Title-Case words immediately preceded by a title
           (Mr., Dr., Sen., Gov., Judge, ...)

If you want ML-grade NER and aren't on a constrained device, nothing
stops you from writing a drop-in replacement with the same signature
-- extract_entities(text) -> list[(entity_text, entity_type)] -- and
pointing downloader.py at it instead.
"""
import re

# ------------------------------------------------------------------
# DATE
# ------------------------------------------------------------------
_MONTHS = (
    "January|February|March|April|May|June|July|"
    "August|September|October|November|December"
)
_DATE_RE = re.compile(
    rf"\b(?:{_MONTHS})\s+\d{{1,2}},?\s+\d{{4}}\b"     # January 5, 2026
    rf"|\b\d{{1,2}}\s+(?:{_MONTHS})\s+\d{{4}}\b"        # 5 January 2026
    r"|\b\d{4}-\d{2}-\d{2}\b"                            # 2026-01-05 (ISO)
    r"|\b\d{1,2}/\d{1,2}/\d{2,4}\b"                      # 1/5/2026
)

# ------------------------------------------------------------------
# GPE / LOC gazetteer
# ------------------------------------------------------------------
_US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming", "Washington, D.C.",
]
_COUNTRIES = [
    "United States", "Canada", "Mexico", "United Kingdom", "France",
    "Germany", "China", "Japan", "Russia", "Brazil", "India",
    "Australia", "Spain", "Italy", "South Korea", "Cuba", "Haiti",
]
_GPE_GAZETTEER = sorted(set(_US_STATES + _COUNTRIES), key=len, reverse=True)
_GPE_RE = re.compile(r"\b(" + "|".join(re.escape(g) for g in _GPE_GAZETTEER) + r")\b")

# ------------------------------------------------------------------
# ORG: Title-Case run containing a recognizable org keyword
# ------------------------------------------------------------------
_ORG_KEYWORDS = (
    "Department", "Commission", "Board", "Bureau", "Agency", "Office",
    "Authority", "Committee", "Council", "Corporation", "Corp",
    "Company", "University", "College", "Institute", "Foundation",
    "Association", "Society", "Administration", "Division", "Service",
    "Services", "Directorate", "Ministry", "Legislature", "Senate",
    "Court", "Commission",
)
# A "title run" is a chain of capitalized words optionally glued
# together with lowercase connectors (of/the/and/for).
_TITLE_RUN_RE = re.compile(
    r"\b[A-Z][A-Za-z&'.-]*(?:[ \t]+(?:of|the|and|for)[ \t]+[A-Z][A-Za-z&'.-]*"
    r"|[ \t]+[A-Z][A-Za-z&'.-]*)*\b"
)

# ------------------------------------------------------------------
# PERSON: title word immediately before a Title-Case run
# ------------------------------------------------------------------
_PERSON_TITLES = (
    "Mr.", "Mrs.", "Ms.", "Dr.", "Sen.", "Rep.", "Gov.", "Judge",
    "Sheriff", "Chief", "Director", "Secretary", "Commissioner",
    "Superintendent", "Colonel", "Lieutenant", "Captain", "Sergeant",
    "President", "Governor", "Senator", "Representative", "Mayor",
)
_PERSON_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(t) for t in _PERSON_TITLES) + r")[ \t]+"
    r"([A-Z][a-zA-Z'.-]*(?:[ \t]+[A-Z][a-zA-Z'.-]*){0,3})"
)

_MAX_ENTITY_WORDS = 8


def _clean(s):
    return s.strip().rstrip('.,;:')


def _find_orgs(text):
    out = []
    for m in _TITLE_RUN_RE.finditer(text):
        run = _clean(m.group(0))
        words = run.split()
        if len(words) < 2 or len(words) > _MAX_ENTITY_WORDS:
            continue
        if any(kw in words for kw in _ORG_KEYWORDS):
            out.append((run, "ORG"))
    return out


def _find_gpe(text):
    return [(m.group(0), "GPE") for m in _GPE_RE.finditer(text)]


def _find_persons(text):
    return [(m.group(1).strip(), "PERSON") for m in _PERSON_RE.finditer(text)]


def _find_dates(text):
    return [(m.group(0), "DATE") for m in _DATE_RE.finditer(text)]


def extract_entities(text, max_chars=200000):
    """Returns a de-duplicated list of (entity_text, entity_type) tuples
    using pure-Python gazetteer/regex heuristics -- no external models,
    no numpy, safe to run anywhere pip runs (Termux included)."""
    if not text:
        return []
    text = text[:max_chars]

    seen = set()
    out = []
    for text_val, etype in (_find_dates(text) + _find_gpe(text)
                             + _find_persons(text) + _find_orgs(text)):
        key = (text_val.strip(), etype)
        if key[0] and key not in seen:
            seen.add(key)
            out.append(key)
    return out
