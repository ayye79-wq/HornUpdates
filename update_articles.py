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

import os

try:
    import feedparser
except ImportError:
    raise SystemExit("feedparser is required: pip install feedparser")

try:
    import openai as _openai
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False

# ── Config ─────────────────────────────────────────────────────────────────────

OUTPUT_PATH = Path(__file__).resolve().parent / "articles.json"
PER_SOURCE_CAP = 25        # max articles kept per source in the final output
TOTAL_CAP = 350            # max total articles before pruning oldest
MAX_AGE_DAYS = 45          # discard articles older than this
SUMMARY_MAX = 600          # truncate summaries to this many characters
ENTRIES_PER_FEED = 30      # how many entries to read from each feed

# ── AI Context Generation ───────────────────────────────────────────────────────

def generate_article_context(title: str, summary: str, countries: List[str], topics: List[str]) -> Optional[str]:
    """Call OpenAI to write a specific 2-3 sentence background context for this article."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or not _OPENAI_AVAILABLE:
        return None
    try:
        client = _openai.OpenAI(api_key=api_key)
        country_str = ", ".join(countries) if countries else "Horn of Africa"
        topic_str = ", ".join(topics) if topics else ""
        prompt = (
            f"You are an editor at Horn Updates, a news site covering the Horn of Africa region.\n\n"
            f"Article title: {title}\n"
            f"Summary: {summary[:400]}\n"
            f"Countries: {country_str}\n"
            f"Topics: {topic_str}\n\n"
            f"Write 2-3 sentences of SPECIFIC background context for this article. "
            f"Explain the particular historical situation, ongoing conflict, political dynamic, "
            f"or regional relationship that makes THIS specific story significant right now. "
            f"Name specific actors, agreements, dates, or events where relevant. "
            f"Do NOT write generic sentences that could apply to many articles on this topic. "
            f"Maximum 75 words. Plain text only."
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=130,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"  [context] AI error for '{title[:50]}': {e}")
        return None


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
        "url": "https://alrakoba.net/feed/",
        "source_name": "الراكوبة",
        "countries": ["Sudan"],
        "lang": "ar",
    },
    {
        "url": "https://www.alnilin.com/feed",
        "source_name": "النيلين",
        "countries": ["Sudan"],
        "lang": "ar",
    },
    {
        "url": "https://feeds.bbci.co.uk/arabic/rss.xml",
        "source_name": "BBC عربي",
        "countries": [],
        "lang": "ar",
        "horn_only": True,
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
        # Arabic
        "إثيوبيا", "أثيوبيا", "أديس أبابا", "تيغراي", "أبي أحمد",
    ],
    "Somalia": [
        "somalia", "somali", "mogadishu", "puntland", "jubaland",
        "al-shabaab", "al shabaab", "alshabaab", "shabab",
        "galmudug", "hirshabelle",
        # Arabic
        "الصومال", "مقديشو", "موقديشو", "الشباب",
    ],
    "Somaliland": [
        "somaliland", "hargeisa",
        # Arabic
        "صوماليلاند", "هرجيسا",
    ],
    "Sudan": [
        "sudan", "khartoum", "darfur", "rsf", "rapid support forces",
        "sudanese armed forces", "saf", "port sudan", "el fasher",
        "omdurman", "kassala",
        # Arabic
        "السودان", "الخرطوم", "دارفور", "الفاشر", "بورتسودان",
        "أم درمان", "الدعم السريع", "القوات السودانية", "كسلا",
    ],
    "South Sudan": [
        "south sudan", "juba", "salva kiir", "riek machar",
        "upper nile", "jonglei", "unity state", "warrap",
        # Arabic
        "جنوب السودان", "جوبا", "سلفا كير", "رياك مشار",
    ],
    "Kenya": [
        "kenya", "kenyan", "nairobi", "mombasa", "kisumu", "william ruto",
        "ruto",
        # Arabic
        "كينيا", "نيروبي",
    ],
    "Eritrea": [
        "eritrea", "eritrean", "asmara", "isaias afwerki", "assab", "massawa",
        # Arabic
        "إريتريا", "أسمرة", "أسمارا",
    ],
    "Djibouti": [
        "djibouti", "djiboutian",
        # Arabic
        "جيبوتي",
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
        "hospital", "disease", "outbreak", "world health organization", "vaccine", "cholera",
        "covid", "malaria", "measles", "health ministry", "epidemic", "w.h.o.",
    ],
    "Climate": [
        "drought", "flood", "rainfall", "climate", "temperature", "locusts",
        "el nino", "la nina", "deforestation", "water shortage",
    ],
    "Justice & Rights": [
        "human rights", "court", "justice", "trial", "arrest", "detained",
        "prison", "accountability", "torture", "rights violation", "amnesty",
    ],
    "Sports": [
        "afcon", "football", "soccer", "athletics", "olympic", "world cup",
        "premier league", "tournament", "championship", "stadium", "fifa",
        "caf ", "marathon", "athlete", "medal", "rugby", "cricket",
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
    if found:
        # Only use keyword-detected countries; don't blindly inherit source country
        # This prevents e.g. Kenyan outlets tagging Trump/Iran stories as Kenya
        return list(dict.fromkeys(found))
    return default if default else []


def _word_match(text: str, phrase: str) -> bool:
    return bool(re.search(r"(?<![a-z])" + re.escape(phrase) + r"(?![a-z])", text))


def tag_topics(text: str) -> List[str]:
    lc = text.lower()
    return [t for t, kws in TOPIC_KEYWORDS.items() if any(_word_match(lc, kw) for kw in kws)] or ["General"]


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

    horn_only = feed_def.get("horn_only", not default_countries)

    for e in entries[:ENTRIES_PER_FEED]:
        title = clean_text(getattr(e, "title", ""))
        link = (getattr(e, "link", None) or "").strip()
        if not title or not link:
            continue

        # Quality filter — skip lifestyle, entertainment, clickbait
        _tl = title.lower()
        if any(kw in _tl for kw in [
            "horoscope", "recipe", "zodiac", "celebrity", "gossip",
            "beauty tip", "fashion", "lifestyle", "relationship advice",
            "quiz:", "poll:", "i have news for you", "here's to hoping",
            "success lies in human connection",
        ]):
            continue

        summary = get_summary(e)
        combined = f"{title} {summary}"

        pub = parse_dt(e)
        if pub and pub < cutoff:
            continue

        countries = tag_countries(combined, default_countries)

        # For regional feeds with no default country, skip if no Horn country detected
        if horn_only and not countries:
            continue

        pub_iso = pub.isoformat() if pub else datetime.now(timezone.utc).isoformat()
        lang = detect_lang(combined) if default_lang == "en" else default_lang
        topics = tag_topics(combined)
        context = generate_article_context(title, summary[:SUMMARY_MAX], countries, topics)

        results.append({
            "title": title,
            "summary": summary[:SUMMARY_MAX],
            "country_tags": countries,
            "topic_tags": topics,
            "language": lang,
            "published_at": pub_iso,
            "source_url": link,
            "source_name": source_name,
            "context": context,
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


  def update_homepage_deep_dive() -> None:
      """Rebuild the Deep Dive section in index.html with the 6 most recent opinion articles."""
      base = Path(__file__).resolve().parent
      index_path = base / "index.html"

      if not index_path.exists():
          print("[deep_dive] index.html not found — skipping")
          return

      SKIP = {"opinion.html", "opinion-post-1.html", "opinion-health.html"}

      articles = []
      for path in base.glob("opinion-*.html"):
          if path.name in SKIP or "health" in path.name:
              continue
          try:
              html = path.read_text(encoding="utf-8")

              # Title
              title_m = re.search(r"<title>([^<]+)</title>", html)
              if not title_m:
                  continue
              title = re.sub(r"\s*\|.*$", "", title_m.group(1)).strip()

              # Description
              desc_m = re.search(r'<meta name="description" content="([^"]+)"', html)
              if not desc_m:
                  continue
              desc = desc_m.group(1).strip()

              # datePublished from JSON-LD
              date_m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html)
              pub_date = None
              if date_m:
                  raw_date = date_m.group(1)[:10]  # keep YYYY-MM-DD
                  try:
                      pub_date = datetime.strptime(raw_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                  except Exception:
                      pass
              if not pub_date:
                  pub_date = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)

              # Author — find Person type in JSON-LD
              author = "Horn Updates"
              person_m = re.search(
                  r'"@type"\s*:\s*"Person"[^}]{0,200}"name"\s*:\s*"([^"]+)"',
                  html, re.DOTALL
              )
              if not person_m:
                  person_m = re.search(
                      r'"name"\s*:\s*"([^"]+)"[^}]{0,200}"@type"\s*:\s*"Person"',
                      html, re.DOTALL
                  )
              if person_m:
                  author = person_m.group(1)

              # Country tags from JSON-LD keywords
              kw_m = re.search(r'"keywords"\s*:\s*"([^"]+)"', html)
              countries = kw_m.group(1).split(", ")[:2] if kw_m else []

              # Word count from byline
              wc_m = re.search(r"~([\d,]+)\s*words", html)
              wc = f"~{wc_m.group(1)} words" if wc_m else ""

              articles.append({
                  "slug": path.name,
                  "title": title,
                  "desc": desc,
                  "date": pub_date,
                  "author": author,
                  "countries": countries,
                  "wc": wc,
              })
          except Exception as e:
              print(f"[deep_dive] Skipped {path.name}: {e}")

      articles.sort(key=lambda a: a["date"], reverse=True)
      top = articles[:6]

      if len(top) < 3:
          print("[deep_dive] Not enough articles — skipping")
          return

      def tag_html(a):
          label = "Analysis · " + " · ".join(a["countries"]) if a["countries"] else "Analysis · Horn of Africa"
          return f'<div class="acard-type t-analysis">{label}</div>'

      def meta_html(a):
          date_fmt = a["date"].strftime("%B %-d, %Y")
          parts = [a["author"], date_fmt]
          if a["wc"]:
              parts.append(a["wc"])
          return f'<div class="acard-meta">{" · ".join(parts)}</div>'

      def lead_card(a):
          return (
              f'          <a class="acard lead" href="/{a[\"slug\"]}">'
              f'\n            {tag_html(a)}'
              f'\n            <h3>{a[\"title\"]}</h3>'
              f'\n            <p>{a[\"desc\"]}</p>'
              f'\n            {meta_html(a)}'
              f'\n          </a>'
          )

      def grid_card(a):
          return (
              f'          <a class="acard" href="/{a[\"slug\"]}">'
              f'\n            {tag_html(a)}'
              f'\n            <h3>{a[\"title\"]}</h3>'
              f'\n            <p>{a[\"desc\"]}</p>'
              f'\n            {meta_html(a)}'
              f'\n          </a>'
          )

      lead_html = "\n".join(lead_card(a) for a in top[:2])
      grid_html = "\n".join(grid_card(a) for a in top[2:6])

      new_block = (
          "        <!-- ── LATEST ANALYSIS ── -->\n"
          "        <div class=\"section-head\">\n"
          "          <h2>Deep Dive</h2>\n"
          "          <a class=\"see-all\" href=\"/opinion.html\">See all →</a>\n"
          "        </div>\n\n"
          "        <div class=\"analysis-lead\">\n"
          + lead_html + "\n"
          "        </div>\n\n"
          "        <div class=\"analysis-grid\">\n"
          + grid_html + "\n"
          "        </div>\n\n"
          "        <!-- ── EXPLAINERS ── -->"
      )

      index_html = index_path.read_text(encoding="utf-8")
      pattern = r"        <!-- ── LATEST ANALYSIS ── -->.*?        <!-- ── EXPLAINERS ── -->"
      new_html, n = re.subn(pattern, new_block, index_html, flags=re.DOTALL)

      if n == 0:
          print("[deep_dive] Could not find Deep Dive markers in index.html — skipping")
          return

      if new_html == index_html:
          print("[deep_dive] Deep Dive unchanged — skipping write")
          return

      index_path.write_text(new_html, encoding="utf-8")
      print(f"[deep_dive] ✅ Updated Deep Dive: {top[0]['title'][:55]}… (+{len(top)-1} more)")

  
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

    # Only write (and update generated_at) when the articles list itself changed.
    # Comparing canonical JSON avoids spurious commits caused by the timestamp alone.
    final_json = json.dumps(final, indent=2, ensure_ascii=False)
    existing_json: str = ""
    if OUTPUT_PATH.exists():
        try:
            existing_data = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
            existing_articles = existing_data if isinstance(existing_data, list) else existing_data.get("articles", [])
            existing_json = json.dumps(existing_articles, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"  [WARN] Could not read existing {OUTPUT_PATH.name} for comparison: {e} — will overwrite")

    if final_json == existing_json:
        print(f"\n✅ Articles unchanged — skipping write ({len(final)} articles)")
    else:
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "articles": final,
        }
        OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n✅ Wrote {len(final)} articles to {OUTPUT_PATH.name}")

    source_counts: Dict[str, int] = {}
    for a in final:
        s = a.get("source_name", "?")
        source_counts[s] = source_counts.get(s, 0) + 1

    print("\nBreakdown by source:")
    for src, cnt in sorted(source_counts.items(), key=lambda x: -x[1]):
        print(f"  {cnt:3d}  {src}")

    generate_sitemap()
    update_homepage_deep_dive()


def generate_sitemap() -> None:
    """Auto-generate sitemap.xml discovering all content pages."""
    base = Path(__file__).resolve().parent

    # Pages to never include in sitemap
    exclude = {
        "reader.html", "disclaimer.html", "thank-you.html",
    }
    # Pages handled explicitly below — skip in glob pass
    handled_explicitly = {
        "index.html", "opinion.html", "explainers.html", "signal-brief.html",
        "about.html", "editorial-policy.html", "privacy.html", "terms.html", "contact.html",
    }

    entries: List[str] = []

    def add(loc, freq, pri, lastmod=None):
        parts = [f"  <url>", f"    <loc>{loc}</loc>"]
        if lastmod:
            parts.append(f"    <lastmod>{lastmod}</lastmod>")
        parts += [f"    <changefreq>{freq}</changefreq>", f"    <priority>{pri}</priority>", "  </url>"]
        entries.append("\n".join(parts))

    def mtime(path):
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%d")

    def page_mtime(fname):
        p = base / fname
        return mtime(p) if p.exists() else None

    # Core navigation pages — use file mtime so lastmod only changes when the file itself changes
    add("https://hornupdates.com/", "daily", "1.0", page_mtime("index.html"))
    add("https://hornupdates.com/opinion.html", "daily", "0.9", page_mtime("opinion.html"))
    add("https://hornupdates.com/explainers.html", "weekly", "0.8", page_mtime("explainers.html"))
    add("https://hornupdates.com/signal-brief.html", "weekly", "0.9", page_mtime("signal-brief.html"))
    add("https://hornupdates.com/about.html", "monthly", "0.6")
    add("https://hornupdates.com/editorial-policy.html", "monthly", "0.5")
    add("https://hornupdates.com/privacy.html", "yearly", "0.4")
    add("https://hornupdates.com/terms.html", "yearly", "0.4")
    add("https://hornupdates.com/contact.html", "yearly", "0.4")

    # Country landing pages
    for fname in ["ethiopia.html", "somalia.html", "sudan.html", "south-sudan.html",
                  "eritrea.html", "kenya.html", "djibouti.html"]:
        p = base / fname
        if p.exists():
            add(f"https://hornupdates.com/{fname}", "weekly", "0.8", mtime(p))

    # All manually written opinion articles (excluding auto-generated)
    for path in sorted(base.glob("opinion-*.html"), reverse=True):
        if "auto" in path.name or path.name in exclude or path.name in handled_explicitly:
            continue
        add(f"https://hornupdates.com/{path.name}", "monthly", "0.9", mtime(path))

    # All explainer articles
    for path in sorted(base.glob("explainer-*.html"), reverse=True):
        if path.name in exclude or path.name in handled_explicitly:
            continue
        add(f"https://hornupdates.com/{path.name}", "monthly", "0.8", mtime(path))

    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n\n'
    sitemap += "\n\n".join(entries)
    sitemap += "\n\n</urlset>\n"

    sitemap_path = base / "sitemap.xml"

    existing = sitemap_path.read_text(encoding="utf-8") if sitemap_path.exists() else ""
    if sitemap == existing:
        print(f"✅ Sitemap unchanged — skipping write ({len(entries)} URLs)")
        return

    sitemap_path.write_text(sitemap, encoding="utf-8")
    print(f"✅ Sitemap updated: {len(entries)} URLs → {sitemap_path.name}")


if __name__ == "__main__":
    main()
