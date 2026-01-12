#!/usr/bin/env python3
"""
update_articles.py

Horn Updates scraper:
- Fetches RSS feeds
- Filters for Horn of Africa stories
- ALWAYS includes Horn-focused feeds (Addis Standard, Reporter, Hiiraan, Garowe, EastAfrican, Sudan Tribune)
- Blocks unwanted sources
- Builds articles.json for the frontend

STRICT MODE:
- Only FETCHES entries newer than last_run_utc.txt
- But OUTPUT keeps a rolling backlog by MERGING with existing articles.json

FIXED / IMPROVED:
1) SudanTribune HTML + “The post ... appeared first ...” footer removed reliably (even when HTML is messy)
2) Title-as-summary duplicates detected strongly but safely; replaced with a clean fallback
3) We clean/normalize BOTH new AND existing (merged backlog) right before writing.
4) Country tags are forced whenever possible (keywords → patterns → domain defaults)
5) Addis Fortune / paywall promo junk filtered (subscribe / print edition / bank detail etc.)
6) Optional page-text fallback for teaser/junk summaries on select domains (safe extraction: meta/og/paragraphs)
"""

import json
import datetime as dt
from pathlib import Path
import urllib.request
import urllib.error
import re
import html
import unicodedata
from typing import Optional, List, Dict, Any

import feedparser  # pip install feedparser
from urllib.parse import urlparse

# ----------------------------
# 0. STRICT MODE STATE
# ----------------------------

LAST_RUN_FILE = Path(__file__).with_name("last_run_utc.txt")


def utc_now():
    return dt.datetime.now(dt.UTC)


def load_last_run():
    if LAST_RUN_FILE.exists():
        try:
            return dt.datetime.fromisoformat(LAST_RUN_FILE.read_text().strip())
        except Exception:
            pass
    # First run default: last 1 day
    return utc_now() - dt.timedelta(days=1)


def save_last_run(ts: dt.datetime):
    LAST_RUN_FILE.write_text(ts.isoformat())


# ----------------------------
# 1. CONFIG
# ----------------------------

OUTPUT_PATH = Path("articles.json")

RSS_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/africa/rss.xml",
    "https://www.thereporterethiopia.com/feed/",
    "https://www.theeastafrican.co.ke/rss.xml",
    "https://sudantribune.net/feed/",
    "https://addisfortune.news/feed/",
    # If you re-add Addis Standard later, keep it in ALWAYS_INCLUDE_FEEDS
    # "https://www.addisstandard.com/feed/",
]

ALWAYS_INCLUDE_FEEDS = [
    "addisstandard.com",
    "thereporterethiopia.com",
    "hiiraan.com",
    "garoweonline.com",
    "theeastafrican.co.ke",
    "sudantribune.net",
    "addisfortune.news",
]

BLOCKED_SOURCES = [
    "borkena.com",
]

HORN_KEYWORDS = [
    "ethiopia", "addis ababa", "amhara", "oromia", "tigray",
    "eritrea", "asmara", "oromo", "amhara", "amara", "tigray", "tegaru",
    "somalia", "mogadishu", "puntland", "somaliland",
    "djibouti",
    "sudan", "south sudan", "khartoum",
    "kenya", "nairobi",
    "horn of africa",
]

COUNTRY_TAGS = {
    "ethiopia": "Ethiopia",
    "eritrea": "Eritrea",
    "somalia": "Somalia",
    "djibouti": "Djibouti",
    "sudan": "Sudan",
    "south sudan": "South Sudan",
    "kenya": "Kenya",
}

MAX_ARTICLES = 200

# Addis Fortune / paywall promo junk patterns (lowercase matching)
SUBSCRIPTION_JUNK = [
    "subscribe",
    "subscription",
    "print edition",
    "digital edition",
    "call our office",
    "bank detail",
    "bonus in a form",
    "to subscribe",
    "birr",
    "br for",
    "weekly in ethiopia",
    "our subscribers",
    "early access",
]


# ----------------------------
# 2. HELPERS (GENERAL)
# ----------------------------

def is_horn_story(text: str) -> bool:
    if not text:
        return False
    lower = text.lower()
    return any(kw in lower for kw in HORN_KEYWORDS)


def extract_countries(text: str):
    if not text:
        return []
    lower = text.lower()
    found = []
    for needle, country_name in COUNTRY_TAGS.items():
        if needle in lower:
            found.append(country_name)

    # de-duplicate preserving order
    seen = set()
    unique = []
    for c in found:
        if c not in seen:
            unique.append(c)
            seen.add(c)
    return unique


def extract_published_dt(entry) -> Optional[dt.datetime]:
    tm = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if tm:
        return dt.datetime(*tm[:6], tzinfo=dt.UTC)
    return None


def should_always_include(feed_url: str) -> bool:
    low = (feed_url or "").lower()
    return any(snippet in low for snippet in ALWAYS_INCLUDE_FEEDS)


def is_blocked(link: str) -> bool:
    link = link or ""
    try:
        host = urlparse(link).netloc.lower()
    except Exception:
        host = link.lower()
    return any(bad in host for bad in BLOCKED_SOURCES)


def load_existing_articles():
    if not OUTPUT_PATH.exists():
        return []
    try:
        payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload.get("articles", []) or []
        if isinstance(payload, list):
            return payload
    except Exception:
        pass
    return []


def parse_feed_no_cache(url: str):
    from urllib.error import HTTPError, URLError

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "HornUpdatesBot/1.0 (+https://hornupdates.com)",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read()

    except HTTPError as e:
        # ✅ 304 = Not Modified (server says "nothing changed")
        if e.code == 304:
            print("[INFO] Feed returned 304 Not Modified → treating as no new items.")
            return None
        raise  # other HTTP errors should still raise

    except URLError as e:
        print(f"[WARN] Network error fetching feed: {e}")
        return None

    # ✅ Only runs if fetch succeeded
    return feedparser.parse(data)



def merge_dedupe(old_list, new_list):
    merged = []
    seen = set()

    for a in new_list + old_list:
        key = (a.get("source_url") or a.get("link") or "").strip()
        if not key:
            key = (a.get("title", "") + "|" + a.get("published_at", "")).strip()
        if key in seen:
            continue
        seen.add(key)
        merged.append(a)

    merged.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    return merged[:MAX_ARTICLES]


def _norm_text(s: str) -> str:
    s = s or ""
    s = unicodedata.normalize("NFKC", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.lower()


def _almost_same(a: str, b: str) -> bool:
    a = _norm_text(a)
    b = _norm_text(b)
    if not a or not b:
        return False
    if a == b:
        return True
    if a.startswith(b) and len(a) - len(b) <= 30:
        return True
    if b.startswith(a) and len(b) - len(a) <= 30:
        return True
    return False


def _clean_source_name(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r"^\s*-\s*", "", name)
    return name.strip()


def _strip_html(s: str) -> str:
    if not s:
        return ""
    s = html.unescape(s)
    s = re.sub(r"<img\b[^>]*>", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _sentences(text: str) -> List[str]:
    if not text:
        return []
    text = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p and p.strip()]


def looks_like_subscription_text(text: str) -> bool:
    low = (text or "").lower()
    return any(j in low for j in SUBSCRIPTION_JUNK)


# ----------------------------
# 2a. SUMMARY BUILDING (RSS + SAFE FALLBACK)
# ----------------------------

def make_summary(entry) -> str:
    """
    Build a usable summary from RSS fields:
    - Prefer richer fields (content, summary_detail) when present
    - Strip HTML
    - Drop subscription/promo junk
    - Return up to 4 sentences
    """
    candidates: List[str] = []

    # 1) Rich 'content' list of dicts with 'value'
    content = getattr(entry, "content", None)
    if isinstance(content, list) and content:
        for c in content:
            val = (c.get("value") if isinstance(c, dict) else "") or ""
            val = _strip_html(val)
            if val:
                candidates.append(val)

    # 2) summary_detail
    sd = getattr(entry, "summary_detail", None)
    if isinstance(sd, dict):
        val = _strip_html(sd.get("value", "") or "")
        if val:
            candidates.append(val)

    # 3) Common fields
    for field in ("summary", "description", "subtitle"):
        val = getattr(entry, field, "") or ""
        val = _strip_html(val)
        if val:
            candidates.append(val)

    # Filter obvious subscription junk candidates
    candidates = [c for c in candidates if not looks_like_subscription_text(c)]

    text = max(candidates, key=len) if candidates else ""
    if not text:
        return ""

    sents = _sentences(text)
    out = " ".join(sents[:4]).strip() if sents else text

    # Final check
    if looks_like_subscription_text(out):
        return ""

    return out


def _fetch_html(url: str, timeout: int = 12) -> str:
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (HornUpdatesBot/1.0; +https://hornupdates.com)"
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace")
    except Exception:
        return ""


def _extract_text_from_html(html_text: str) -> str:
    """
    Safe-ish extraction:
    - Try meta description / og:description
    - Try JSON-LD (articleBody/description) via regex
    - Fallback to first paragraphs (after removing scripts/styles)
    """
    if not html_text:
        return ""

    # JSON-LD blocks
    jsonld_blocks = re.findall(
        r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html_text
    )
    for block in jsonld_blocks:
        block = block.strip()
        m = re.search(r'"articleBody"\s*:\s*"([^"]{80,})"', block)
        if m:
            return _strip_html(m.group(1))
        m = re.search(r'"description"\s*:\s*"([^"]{80,})"', block)
        if m:
            return _strip_html(m.group(1))

    # meta description
    m = re.search(
        r'(?is)<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
        html_text
    )
    if m:
        meta_desc = _strip_html(m.group(1))
        if len(meta_desc) > 100 and not looks_like_subscription_text(meta_desc):
            return meta_desc

    # og:description
    m = re.search(
        r'(?is)<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']',
        html_text
    )
    if m:
        og_desc = _strip_html(m.group(1))
        if len(og_desc) > 100 and not looks_like_subscription_text(og_desc):
            return og_desc

    # Remove scripts/styles
    cleaned = re.sub(r"(?is)<style.*?>.*?</style>", " ", html_text)
    cleaned = re.sub(r"(?is)<script.*?>.*?</script>", " ", cleaned)

    paras = re.findall(r"(?is)<p[^>]*>(.*?)</p>", cleaned)
    paras = [_strip_html(p) for p in paras]
    paras = [p for p in paras if len(p) > 50 and not looks_like_subscription_text(p)]
    text = " ".join(paras[:10]).strip()
    return text


def maybe_upgrade_summary_from_page(link: str, current_summary: str) -> str:
    """
    Only try this when summary is empty/teaser/junk and domain is known to be teaser-heavy.
    """
    if not link:
        return current_summary

    host = urlparse(link).netloc.lower()

    # Only these domains get page fallback (to keep runs fast & safe)
    allowed_hosts = {
        "www.theeastafrican.co.ke", "theeastafrican.co.ke",
        "www.addisfortune.news", "addisfortune.news",
        "www.sudantribune.net", "sudantribune.net",
    }
    if host not in allowed_hosts:
        return current_summary

    # Only if needed
    s = (current_summary or "").strip()
    if s and len(s) >= 160 and not s.endswith("...") and not looks_like_subscription_text(s):
        return current_summary

    page_html = _fetch_html(link, timeout=12)
    page_text = _extract_text_from_html(page_html)
    if not page_text or looks_like_subscription_text(page_text):
        return current_summary

    sents = _sentences(page_text)
    if not sents:
        return current_summary

    upgraded = " ".join(sents[:4]).strip()
    if looks_like_subscription_text(upgraded):
        return current_summary

    return upgraded


# ----------------------------
# 2b. SUMMARY CLEANING + NORMALIZATION
# ----------------------------

def clean_summary(raw: str, title: str = "", source_name: str = "") -> str:
    raw = raw or ""
    title = title or ""
    source_name = _clean_source_name(source_name or "")

    s = html.unescape(raw)

    # 1) Remove any <img ...> tags anywhere
    s = re.sub(r"<img\b[^>]*>", " ", s, flags=re.IGNORECASE)

    # 2) Remove WP footer while still HTML
    s = re.sub(
        r"(?:<p>\s*)?The post .*? appeared first on .*?(?:</p>)?",
        " ",
        s,
        flags=re.IGNORECASE | re.DOTALL
    )

    # 3) Strip ALL HTML tags
    s = re.sub(r"<[^>]+>", " ", s)

    # 4) Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()

    # 5) Remove WP footer again (plain text)
    s = re.sub(r"The post .*? appeared first on .*?$", " ", s, flags=re.IGNORECASE).strip()

    # 6) Drop subscription junk
    if looks_like_subscription_text(s):
        s = ""

    # 7) Title duplication detection
    if _almost_same(s, title):
        s = ""

    # 8) If still empty/too short, fallback
    if len(s) < 25:
        s = f"Read the full story on {source_name}." if source_name else "Read the full story at the source."

    # 9) Soft cap (keeps reader clean)
    if len(s) > 650:
        s = s[:647].rsplit(" ", 1)[0] + "..."

    return s


# ----------------------------
# 2c. COUNTRY FORCING
# ----------------------------

COUNTRY_PATTERNS = [
    ("Ethiopia", r"\b(ethiopia|addis(\s+ababa)?|tigray|oromia|amhara|gondar|bahir\s+dar|mekelle)\b"),
    ("Somalia", r"\b(somalia|mogadishu|puntland|somaliland|hargeisa|kismayo|galmudug)\b"),
    ("Sudan", r"\b(sudan|khartoum|darfur|rsf|saf|burhan|hemeti|omdurman|port\s*sudan|kassala|el\s*fasher)\b"),
    ("South Sudan", r"\b(south\s+sudan|juba|upper\s+nile|bentiu)\b"),
    ("Kenya", r"\b(kenya|nairobi|mombasa|kisumu|ruto|raila|eldoret|nakuru)\b"),
    ("Djibouti", r"\b(djibouti)\b"),
    ("Eritrea", r"\b(eritrea|asmara|massawa)\b"),
]

DOMAIN_DEFAULT_COUNTRY = {
    "standardmedia.co.ke": "Kenya",
    "www.standardmedia.co.ke": "Kenya",
    "theeastafrican.co.ke": "Kenya",
    "www.theeastafrican.co.ke": "Kenya",
    "sudantribune.net": "Sudan",
    "www.sudantribune.net": "Sudan",
    "thereporterethiopia.com": "Ethiopia",
    "www.thereporterethiopia.com": "Ethiopia",
    "addisfortune.news": "Ethiopia",
    "www.addisfortune.news": "Ethiopia",
    "addisstandard.com": "Ethiopia",
    "www.addisstandard.com": "Ethiopia",
    "hiiraan.com": "Somalia",
    "www.hiiraan.com": "Somalia",
    "garoweonline.com": "Somalia",
    "www.garoweonline.com": "Somalia",
}


def infer_country_tags(title: str, url: str, existing_tags=None, max_tags: int = 2):
    existing_tags = existing_tags or []
    existing_tags = [t.strip() for t in existing_tags if t and t.strip()]
    if existing_tags:
        return existing_tags[:max_tags]

    text = f"{title or ''} {url or ''}".lower()
    found = []

    for country, pattern in COUNTRY_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            found.append(country)

    deduped = []
    for c in found:
        if c not in deduped:
            deduped.append(c)

    if deduped:
        return deduped[:max_tags]

    host = ""
    try:
        host = urlparse(url or "").netloc.lower()
    except Exception:
        host = ""

    if host in DOMAIN_DEFAULT_COUNTRY:
        return [DOMAIN_DEFAULT_COUNTRY[host]]

    return []


def normalize_article(article: dict) -> dict:
    title = (article.get("title") or "").strip()
    source_name = _clean_source_name(article.get("source_name") or "")
    source_url = article.get("source_url") or article.get("link") or ""

    raw_summary = (
        article.get("summary")
        or article.get("description")
        or article.get("content")
        or ""
    )

    article["source_name"] = source_name
    article["summary"] = clean_summary(raw_summary, title=title, source_name=source_name)

    existing = article.get("country_tags") or []
    article["country_tags"] = infer_country_tags(title, source_url, existing_tags=existing, max_tags=2)

    return article


# ----------------------------
# 3. MAIN
# ----------------------------

def main():
    new_articles = []
    last_run = load_last_run()
    now = utc_now()
    print(f"[INFO] Strict mode enabled. Last run = {last_run.isoformat()}")

    for feed_url in RSS_FEEDS:
        print(f"\n=== Fetching: {feed_url} ===")

        # Reporter sometimes caches aggressively
        if "thereporterethiopia.com" in feed_url:
            parsed = parse_feed_no_cache(feed_url)
        else:
            parsed = feedparser.parse(
                feed_url,
                request_headers={"User-Agent": "HornUpdatesBot/1.0 (+https://hornupdates.com)"}
            )

        entries = getattr(parsed, "entries", None) or []
        if not entries:
            print(f"[!] No entries returned for: {feed_url}")
            continue

        include_all = should_always_include(feed_url)
        count_included = 0

        source_name = _clean_source_name(parsed.feed.get("title", "") if getattr(parsed, "feed", None) else "")

        for entry in entries:
            title = getattr(entry, "title", "") or ""
            link = getattr(entry, "link", "") or ""

            if is_blocked(link):
                continue

            published_dt = extract_published_dt(entry)

            # STRICT: skip entries with no publish date
            if not published_dt:
                continue

            # STRICT: only fetch stories newer than last run
            if published_dt <= last_run:
                continue

            # Safety: skip future-dated items
            if published_dt > now + dt.timedelta(minutes=5):
                continue

            # 1) RSS summary (clean build)
            summary_raw = make_summary(entry)

            # 2) If teaser/junk, try safe page fallback for select domains
            if not summary_raw or looks_like_subscription_text(summary_raw) or summary_raw.endswith("...") or len(_strip_html(summary_raw)) < 140:
                summary_raw = maybe_upgrade_summary_from_page(link, summary_raw)

            # 3) Final cleaning (handles SudanTribune footer, title duplication, etc.)
            summary = clean_summary(summary_raw, title=title, source_name=source_name)

            combined_text = f"{title}\n{summary}"

            # Keep BBC Africa feed from being too restrictive (BBC is broad; we still want Horn matches)
            is_bbc_africa = "feeds.bbci.co.uk" in (feed_url or "").lower()

            if not include_all and not is_bbc_africa and not is_horn_story(combined_text):
                continue

            published_at = published_dt.isoformat()

            countries = infer_country_tags(
                title,
                link,
                existing_tags=extract_countries(combined_text),
                max_tags=2
            )

            topic_tags = []
            lower = combined_text.lower()
            if any(w in lower for w in ["election", "parliament", "government", "president", "prime minister"]):
                topic_tags.append("Politics & Governance")
            if any(w in lower for w in ["attack", "clash", "conflict", "war", "military", "fighting", "strike"]):
                topic_tags.append("Security & Conflict")
            if any(w in lower for w in ["investment", "economy", "business", "market", "trade", "company", "debt"]):
                topic_tags.append("Business & Economy")
            if not topic_tags:
                topic_tags.append("General")

            article = {
                "title": title,
                "summary": summary,
                "country_tags": countries,
                "topic_tags": topic_tags,
                "published_at": published_at,
                "source_url": link,
                "source_name": source_name,
            }

            new_articles.append(article)
            count_included += 1

        print(f"Included {count_included} items from this feed.")

    existing = load_existing_articles()
    merged_articles = merge_dedupe(existing, new_articles)

    # ✅ Clean BOTH new + existing right before writing (includes forced country tags)
    merged_articles = [normalize_article(a) for a in merged_articles]

    # If nothing new AND file exists, keep it (still update last_run)
    if len(new_articles) == 0 and OUTPUT_PATH.exists():
        print("[INFO] No new articles since last run. Keeping existing articles.json.")
        save_last_run(now)
        print(f"[INFO] Updated last_run_utc.txt → {now.isoformat()}")
        return

    payload = {
        "generated_at": now.isoformat(),
        "articles": merged_articles,
    }

    print(f"\nWriting {len(merged_articles)} total articles to {OUTPUT_PATH} (new fetched: {len(new_articles)})")
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    save_last_run(now)
    print(f"[INFO] Updated last_run_utc.txt → {now.isoformat()}")


if __name__ == "__main__":
    main()
