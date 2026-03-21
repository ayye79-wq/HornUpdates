"""
update_articles.py — Horn Updates RSS scraper
Fetches articles from Horn of Africa news sources, tags them, and writes articles.json.

Run locally:   python update_articles.py
Run via CI:    github actions calls this daily, then commits articles.json back to the repo
"""

import json
import re
import html as _html
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import feedparser
except ImportError:
    raise SystemExit("feedparser is required: pip install feedparser")

# ── Config ─────────────────────────────────────────────────────────────────────

OUTPUT_PATH = Path(__file__).resolve().parent / "articles.json"
PER_SOURCE_CAP = 25        # max articles kept per source in the final output
TOTAL_CAP = 350            # max total articles before pruning oldest
MAX_AGE_DAYS = 45          # discard articles older than this
SUMMARY_MAX = 600          # truncate summaries to this many characters
ENTRIES_PER_FEED = 30      # how many entries to read from each feed

# ── RSS Feeds ──────────────────────────────────────────────────────────────────
# Each dict: url, source_name, countries (default country tags), lang

FEEDS: List[Dict[str, Any]] = [
    # ── Ethiopia ──────────────────────────────────────────────────────────────
    {
        "url": "https://www.thereporterethiopia.com/feed/",
        "source_name": "The Reporter Ethiopia",
        "countries": ["Ethiopia"],
        "lang": "en",
    },
    {
        "url": "https://capitalethiopia.com/feed/",
        "source_name": "Capital Ethiopia",
        "countries": ["Ethiopia"],
        "lang": "en",
    },
    {
        "url": "https://addisstandard.com/feed/",
        "source_name": "Addis Standard",
        "countries": ["Ethiopia"],
        "lang": "en",
    },
    {
        "url": "https://ethiopianmonitor.com/feed/",
        "source_name": "Ethiopian Monitor",
        "countries": ["Ethiopia"],
        "lang": "en",
    },
    # ── Somalia ───────────────────────────────────────────────────────────────
    {
        "url": "https://www.garoweonline.com/en/rss",
        "source_name": "Garowe Online",
        "countries": ["Somalia"],
        "lang": "en",
    },
    # ── South Sudan ───────────────────────────────────────────────────────────
    {
        "url": "https://thenilepost.com/feed/",
        "source_name": "The Nile Post",
        "countries": ["South Sudan"],
        "lang": "en",
    },
    {
        "url": "https://radiotamazuj.org/en/feed",
        "source_name": "Radio Tamazuj",
        "countries": ["South Sudan"],
        "lang": "en",
    },
    {
        "url": "https://eyeradio.org/feed/",
        "source_name": "Eye Radio",
        "countries": ["South Sudan"],
        "lang": "en",
    },
    # ── Sudan ─────────────────────────────────────────────────────────────────
    {
        "url": "https://sudantribune.com/feed/",
        "source_name": "Sudan Tribune",
        "countries": ["Sudan"],
        "lang": "en",
    },
    {
        "url": "https://www.sudantribune.net/spip.php?page=backend",
        "source_name": "سودان تربيون",
        "countries": ["Sudan"],
        "lang": "ar",
    },
    # ── Kenya ─────────────────────────────────────────────────────────────────
    {
        "url": "https://www.theeastafrican.co.ke/sitemap/rss",
        "source_name": "The EastAfrican",
        "countries": ["Kenya"],
        "lang": "en",
    },
    {
        "url": "https://nation.africa/kenya/rss.xml",
        "source_name": "Nation Africa",
        "countries": ["Kenya"],
        "lang": "en",
    },
    # ── Eritrea ───────────────────────────────────────────────────────────────
    {
        "url": "https://www.tesfanews.net/feed/",
        "source_name": "Tesfa News",
        "countries": ["Eritrea"],
        "lang": "en",
    },
    # ── Regional / Multi-country ──────────────────────────────────────────────
    {
        "url": "https://feeds.bbci.co.uk/news/world/africa/rss.xml",
        "source_name": "BBC News",
        "countries": [],
        "lang": "en",
    },
    {
        "url": "https://www.aa.com.tr/en/rss/default?cat=africa",
        "source_name": "Anadolu Agency",
        "countries": [],
        "lang": "en",
    },
]

# ── Country keyword map ────────────────────────────────────────────────────────
# These phrases anywhere in title/summary trigger the country tag

COUNTRY_KEYWORDS: Dict[str, List[str]] = {
    "Ethiopia": [
        "ethiopia", "ethiopian", "addis ababa", "abiy ahmed", "tigray",
        "oromia", "amhara", "afar", "somali region", "dire dawa",
    ],
    "Somalia": [
        "somalia", "somali", "mogadishu", "puntland", "jubaland",
        "al-shabaab", "al shabaab", "alshabaab", "shabab",
        "galmudug", "hirshabelle",
    ],
    "Somaliland": [
        "somaliland", "hargeisa",
    ],
    "Sudan": [
        "sudan", "khartoum", "darfur", "rsf", "rapid support forces",
        "sudanese armed forces", "saf", "port sudan", "el fasher",
        "omdurman", "kassala",
    ],
    "South Sudan": [
        "south sudan", "juba", "salva kiir", "riek machar",
        "upper nile", "jonglei", "unity state", "warrap",
    ],
    "Kenya": [
        "kenya", "kenyan", "nairobi", "mombasa", "kisumu", "william ruto",
        "ruto",
    ],
    "Eritrea": [
        "eritrea", "eritrean", "asmara", "isaias afwerki", "assab", "massawa",
    ],
    "Djibouti": [
        "djibouti", "djiboutian",
    ],
}

# ── Topic keyword map ──────────────────────────────────────────────────────────

TOPIC_KEYWORDS: Dict[str, List[str]] = {
    "Politics": [
        "election", "parliament", "president", "prime minister", "minister",
        "government", "opposition", "vote", "constitution", "coup",
        "cabinet", "political party", "senate",
    ],
    "Security": [
        "attack", "killed", "military", "bomb", "gunmen", "troops",
        "war", "armed group", "fighting", "airstrike", "militia",
        "offensive", "ambush", "clashes", "insurgent",
    ],
    "Humanitarian": [
        "aid", "refugee", "famine", "food insecurity", "displaced",
        "humanitarian", "relief", "malnutrition", "shelter", "un agencies",
        "wfp", "unhcr", "unicef",
    ],
    "Business & Economy": [
        "gdp", "inflation", "investment", "trade", "economy", "economic",
        "bank", "currency", "budget", "imf", "world bank", "revenue",
        "export", "import", "growth",
    ],
    "Diplomacy": [
        "agreement", "summit", "talks", "diplomat", "ambassador",
        "bilateral", "foreign minister", "treaty", "negotiation",
        "peace deal", "ceasefire", "mediation",
    ],
    "Health": [
        "hospital", "disease", "outbreak", "who ", "vaccine", "cholera",
        "covid", "malaria", "measles", "health ministry", "epidemic",
    ],
    "Climate": [
        "drought", "flood", "rainfall", "climate", "temperature", "locusts",
        "el nino", "la nina", "deforestation", "water shortage",
    ],
    "Justice & Rights": [
        "human rights", "court", "justice", "trial", "arrest", "detained",
        "prison", "accountability", "torture", "rights violation", "amnesty",
    ],
}

# ── Helpers ────────────────────────────────────────────────────────────────────

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_URL_RE = re.compile(r"https?://\S+")


def clean_text(s: str) -> str:
    s = _html.unescape(s or "")
    s = _HTML_TAG_RE.sub(" ", s)
    s = _URL_RE.sub("", s)
    s = _WS_RE.sub(" ", s).strip()
    return s


def detect_lang(text: str) -> str:
    if re.search(r"[\u0600-\u06FF]", text or ""):
        return "ar"
    return "en"


def tag_countries(text: str, default: List[str]) -> List[str]:
    lc = text.lower()
    found = [c for c, kws in COUNTRY_KEYWORDS.items() if any(kw in lc for kw in kws)]
    merged = list(dict.fromkeys(default + found))
    return merged if merged else default


def tag_topics(text: str) -> List[str]:
    lc = text.lower()
    return [t for t, kws in TOPIC_KEYWORDS.items() if any(kw in lc for kw in kws)] or ["General"]


def make_id(url: str) -> str:
    return hashlib.sha1((url or "").encode()).hexdigest()[:12]


def parse_dt(entry) -> Optional[datetime]:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    for attr in ("published", "updated"):
        s = getattr(entry, attr, None)
        if s:
            try:
                s = str(s).strip()
                if s.endswith("Z"):
                    s = s[:-1] + "+00:00"
                return datetime.fromisoformat(s)
            except Exception:
                pass
    return None


def get_summary(entry) -> str:
    for attr in ("summary", "content"):
        val = getattr(entry, attr, None)
        if not val:
            continue
        if isinstance(val, list):
            val = val[0].get("value", "") if val else ""
        return clean_text(str(val))
    return ""


# ── Core fetch ─────────────────────────────────────────────────────────────────

def fetch_feed(feed_def: Dict[str, Any]) -> List[Dict[str, Any]]:
    url = feed_def["url"]
    source_name = feed_def["source_name"]
    default_countries = feed_def.get("countries", [])
    default_lang = feed_def.get("lang", "en")

    print(f"  Fetching {source_name} …", end=" ", flush=True)
    try:
        d = feedparser.parse(url)
    except Exception as e:
        print(f"ERROR: {e}")
        return []

    entries = getattr(d, "entries", [])
    if not entries:
        status = getattr(d, "status", "?")
        print(f"no entries (HTTP {status})")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    results: List[Dict[str, Any]] = []

    for e in entries[:ENTRIES_PER_FEED]:
        title = clean_text(getattr(e, "title", ""))
        link = (getattr(e, "link", None) or "").strip()
        if not title or not link:
            continue

        summary = get_summary(e)
        combined = f"{title} {summary}"

        pub = parse_dt(e)
        if pub and pub < cutoff:
            continue

        pub_iso = pub.isoformat() if pub else datetime.now(timezone.utc).isoformat()
        lang = detect_lang(combined) if default_lang == "en" else default_lang

        results.append({
            "title": title,
            "summary": summary[:SUMMARY_MAX],
            "country_tags": tag_countries(combined, default_countries),
            "topic_tags": tag_topics(combined),
            "language": lang,
            "published_at": pub_iso,
            "source_url": link,
            "source_name": source_name,
        })

    print(f"{len(results)} articles")
    return results


# ── Dedup + merge ──────────────────────────────────────────────────────────────

def load_existing() -> List[Dict[str, Any]]:
    if not OUTPUT_PATH.exists():
        return []
    try:
        data = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else data.get("articles", [])
    except Exception:
        return []


def dedupe(existing: List[Dict[str, Any]], incoming: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen_urls: set = set()
    seen_titles: set = set()
    merged: List[Dict[str, Any]] = []

    for a in incoming + existing:
        url = (a.get("source_url") or a.get("link") or "").strip().rstrip("/")
        title_key = re.sub(r"\W+", " ", (a.get("title") or "").lower()).strip()
        if url in seen_urls or (title_key and title_key in seen_titles):
            continue
        if url:
            seen_urls.add(url)
        if title_key:
            seen_titles.add(title_key)
        merged.append(a)

    return merged


def apply_caps(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def pub_dt(a):
        s = a.get("published_at") or ""
        try:
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            return datetime.fromisoformat(s)
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)

    articles.sort(key=pub_dt, reverse=True)

    source_counts: Dict[str, int] = {}
    result: List[Dict[str, Any]] = []
    for a in articles:
        src = a.get("source_name", "Unknown")
        if source_counts.get(src, 0) >= PER_SOURCE_CAP:
            continue
        source_counts[src] = source_counts.get(src, 0) + 1
        result.append(a)
        if len(result) >= TOTAL_CAP:
            break

    return result


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=== Horn Updates Scraper ===")
    print(f"Fetching {len(FEEDS)} feeds …\n")

    incoming: List[Dict[str, Any]] = []
    for feed_def in FEEDS:
        try:
            incoming.extend(fetch_feed(feed_def))
        except Exception as e:
            print(f"  [SKIP] {feed_def['source_name']}: {e}")

    print(f"\nFetched {len(incoming)} total new items")

    existing = load_existing()
    print(f"Loaded {len(existing)} existing articles")

    merged = dedupe(existing, incoming)
    final = apply_caps(merged)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "articles": final,
    }

    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    source_counts: Dict[str, int] = {}
    for a in final:
        s = a.get("source_name", "?")
        source_counts[s] = source_counts.get(s, 0) + 1

    print(f"\n✅ Wrote {len(final)} articles to {OUTPUT_PATH.name}")
    print("\nBreakdown by source:")
    for src, cnt in sorted(source_counts.items(), key=lambda x: -x[1]):
        print(f"  {cnt:3d}  {src}")


if __name__ == "__main__":
    main()
