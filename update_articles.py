#!/usr/bin/env python3
"""
update_articles.py

Horn Updates scraper:
- Fetches RSS feeds
- Filters for Horn of Africa stories
- ALWAYS includes Horn-focused feeds (Addis Standard, Reporter, Hiiraan, Garowe, EastAfrican, Sudan Tribune)
- Blocks unwanted / geo-blocked sources (ENA, AJ, Borkena)
- Drops very old stories
- Builds articles.json for the frontend
"""

import json
import datetime as dt
from pathlib import Path
import urllib.parse as urlparse

import feedparser  # pip install feedparser

# ----------------------------
# 1. CONFIG
# ----------------------------

OUTPUT_PATH = Path("articles.json")

# Keep stories only from the last N days
MAX_AGE_DAYS = 10  # 🔧 Change this if you want a shorter/longer window

RSS_FEEDS = [
    # 🌍 General Africa / regional
    "https://www.reuters.com/rssFeed/africaNews",
    "https://www.voanews.com/rss/section/africa",
    "https://feeds.bbci.co.uk/news/world/africa/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",

    # 🇪🇹 Ethiopia
    "https://www.addisstandard.com/feed/",
    "https://www.thereporterethiopia.com/feed/",

    # 🇸🇴 Somalia
    "https://www.hiiraan.com/rss/english/news.xml",
    "https://www.garoweonline.com/en/rss",

    # 🇰🇪 Kenya / region
    "https://www.theeastafrican.co.ke/rss/2148232-2148660-format-rss-2.0.xml",

    # 🇸🇩 Sudan
    "https://sudantribune.com/feed/",
]

# Feeds that are already Horn-of-Africa focused -> keep ALL their stories
ALWAYS_INCLUDE_FEEDS = [
    "addisstandard.com",
    "thereporterethiopia.com",
    "hiiraan.com",
    "garoweonline.com",
    "theeastafrican.co.ke",
    "sudantribune.com",
    "bbci.co.uk",

]

# Block some domains entirely (e.g., ENA, Borkena, Al Jazeera)
BLOCKED_SOURCES = [
    "borkena.com",

]

HORN_KEYWORDS = [
    "ethiopia", "addis ababa", "amhara", "oromia", "tigray",
    "eritrea", "asmara",
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

# ----------------------------
# 2. HELPERS
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
    # de-duplicate
    seen = set()
    unique = []
    for c in found:
        if c not in seen:
            unique.append(c)
            seen.add(c)
    return unique


def extract_published_dt(entry) -> dt.datetime:
    """Return a datetime object (UTC) for the entry."""
    dt_obj = None

    if getattr(entry, "published_parsed", None):
        try:
            dt_obj = dt.datetime(*entry.published_parsed[:6])
        except Exception:
            dt_obj = None

    if dt_obj is None and getattr(entry, "updated_parsed", None):
        try:
            dt_obj = dt.datetime(*entry.updated_parsed[:6])
        except Exception:
            dt_obj = None

    if dt_obj is None:
        dt_obj = dt.datetime.utcnow()

    # assume feed timestamps are UTC or naive
    if dt_obj.tzinfo is not None:
        dt_obj = dt_obj.astimezone(dt.timezone.utc).replace(tzinfo=None)

    return dt_obj


def format_published_iso(entry) -> str:
    """Return ISO8601 string with Z suffix for JSON."""
    return extract_published_dt(entry).isoformat() + "Z"


def make_summary(entry):
    for field in ("summary", "description"):
        if hasattr(entry, field) and getattr(entry, field):
            return getattr(entry, field)
    return ""


def should_always_include(feed_url: str) -> bool:
    low = feed_url.lower()
    return any(snippet in low for snippet in ALWAYS_INCLUDE_FEEDS)


def is_blocked(link: str) -> bool:
    link = link or ""
    try:
        host = urlparse.urlparse(link).netloc.lower()
    except Exception:
        host = link.lower()
    return any(bad in host for bad in BLOCKED_SOURCES)


# ----------------------------
# 3. MAIN
# ----------------------------

def main():
    all_articles = []
    now = dt.datetime.utcnow()

    for feed_url in RSS_FEEDS:
        print(f"\n=== Fetching: {feed_url} ===")
        parsed = feedparser.parse(feed_url)

        if parsed.bozo:
            print(f"[!] Problem parsing feed: {parsed.bozo_exception}")

        include_all = should_always_include(feed_url)
        count_included = 0

        for entry in parsed.entries:
            title = getattr(entry, "title", "") or ""
            link = getattr(entry, "link", "") or ""
            summary = make_summary(entry)

            # 🔴 Skip blocked domains entirely
            if is_blocked(link):
                continue

            # 🔴 Drop very old stories
            published_dt = extract_published_dt(entry)
            age_days = (now - published_dt).days
            if age_days > MAX_AGE_DAYS:
                continue

            combined_text = f"{title}\n{summary}"

            # General feeds require Horn filtering
            if not include_all and not is_horn_story(combined_text):
                continue

            published_at = published_dt.isoformat() + "Z"
            countries = extract_countries(combined_text)

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

            source_name = parsed.feed.get("title", "") if parsed.feed else ""

            article = {
                "title": title,
                "summary": summary,
                "country_tags": countries,
                "topic_tags": topic_tags,
                "published_at": published_at,
                "source_url": link,
                "source_name": source_name,
            }

            all_articles.append(article)
            count_included += 1

        print(f"Included {count_included} items from this feed.")

    # Sort newest first
    all_articles.sort(key=lambda a: a.get("published_at", ""), reverse=True)

    # Optional: cap total articles
    MAX_ARTICLES = 200
    if len(all_articles) > MAX_ARTICLES:
        all_articles = all_articles[:MAX_ARTICLES]

    payload = {
        "generated_at": dt.datetime.utcnow().isoformat() + "Z",
        "articles": all_articles,
    }

    print(f"\nWriting {len(all_articles)} articles to {OUTPUT_PATH}")
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
