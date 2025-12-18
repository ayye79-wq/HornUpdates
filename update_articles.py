#!/usr/bin/env python3
"""
update_articles.py

Horn Updates scraper:
- Fetches RSS feeds
- Filters for Horn of Africa stories
- ALWAYS includes Horn-focused feeds (Addis Standard, Reporter, Hiiraan, Garowe, EastAfrican, Sudan Tribune)
- Blocks unwanted / geo-blocked sources (ENA, AJ, Borkena)
- Builds articles.json for the frontend

STRICT MODE:
- Only includes entries with a real publish date
- Only includes entries newer than last_run_utc.txt
- Does NOT overwrite articles.json if 0 new items (keeps existing file)

FIX (Dec 2025):
- Do NOT update last_run_utc.txt when 0 items are found
- When items ARE found, update last_run_utc.txt to the newest published_dt included (not wall-clock "now")
"""

import json
import datetime as dt
from pathlib import Path
import urllib.parse as urlparse

import feedparser  # pip install feedparser


# ----------------------------
# 0. STRICT MODE STATE
# ----------------------------

LAST_RUN_FILE = Path(__file__).with_name("last_run_utc.txt")

def utc_now():
    return dt.datetime.now(dt.UTC)

def load_last_run():
    if LAST_RUN_FILE.exists():
        txt = LAST_RUN_FILE.read_text(encoding="utf-8").strip()
        if txt:
            try:
                return dt.datetime.fromisoformat(txt)
            except Exception:
                # If file content is corrupt, fall back safely
                pass
    # First run default: last 1 day
    return utc_now() - dt.timedelta(days=1)

def save_last_run(ts: dt.datetime):
    # Always write as ISO with timezone
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt.UTC)
    LAST_RUN_FILE.write_text(ts.isoformat(), encoding="utf-8")


# ----------------------------
# 1. CONFIG
# ----------------------------

OUTPUT_PATH = Path("articles.json")

RSS_FEEDS = [
    # 🌍 General Africa / regional
    "https://feeds.bbci.co.uk/news/world/africa/rss.xml",

    # 🇪🇹 Ethiopia
    "https://www.addisstandard.com/feed/",
    "https://www.thereporterethiopia.com/feed/",

    # 🇰🇪 Kenya / region
    "https://www.theeastafrican.co.ke/rss.xml",

    # 🇸🇩 Sudan
    "https://sudantribune.net/feed/",
]

# Feeds that are already Horn-of-Africa focused -> keep ALL their stories
ALWAYS_INCLUDE_FEEDS = [
    "addisstandard.com",
    "thereporterethiopia.com",
    "hiiraan.com",
    "garoweonline.com",
    "theeastafrican.co.ke",
    "sudantribune.com",
]

# Block some domains entirely
BLOCKED_SOURCES = [
    "borkena.com",
    # Add more blocked domains here if needed
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

def extract_published_dt(entry) -> dt.datetime | None:
    """Return a timezone-aware datetime in UTC for the entry, or None if missing."""
    tm = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if tm:
        return dt.datetime(*tm[:6], tzinfo=dt.UTC)
    return None

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

    last_run = load_last_run()
    now = utc_now()
    print(f"[INFO] Strict mode enabled. Last run = {last_run.isoformat()}")

    # Track newest published time we actually include
    newest_included: dt.datetime | None = None

    for feed_url in RSS_FEEDS:
        print(f"\n=== Fetching: {feed_url} ===")

        parsed = feedparser.parse(
            feed_url,
            request_headers={"User-Agent": "HornUpdatesBot/1.0 (+https://hornupdates.com)"}
        )

        if not parsed.entries:
            print(f"[!] No entries returned for: {feed_url}")
            continue

        include_all = should_always_include(feed_url)
        count_included = 0

        for entry in parsed.entries:
            title = getattr(entry, "title", "") or ""
            link = getattr(entry, "link", "") or ""
            summary = make_summary(entry)

            # Blocked domains
            if is_blocked(link):
                continue

            published_dt = extract_published_dt(entry)

            # STRICT: skip entries with no publish date
            if not published_dt:
                continue

            # STRICT: only include stories newer than last run
            if published_dt <= last_run:
                continue

            # Safety: skip future-dated items
            if published_dt > now + dt.timedelta(minutes=5):
                continue

            combined_text = f"{title}\n{summary}"

            # General feeds require Horn filtering
            if not include_all and not is_horn_story(combined_text):
                continue

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
                "published_at": published_dt.isoformat(),
                "source_url": link,
                "source_name": source_name,
            }

            all_articles.append(article)
            count_included += 1

            # Track newest included publish time
            if newest_included is None or published_dt > newest_included:
                newest_included = published_dt

        print(f"Included {count_included} items from this feed.")

    # Sort newest first (after all feeds)
    all_articles.sort(key=lambda a: a.get("published_at", ""), reverse=True)

    # Cap total articles
    MAX_ARTICLES = 200
    if len(all_articles) > MAX_ARTICLES:
        all_articles = all_articles[:MAX_ARTICLES]

    # 🚫 Do NOT overwrite articles.json if no new articles
    if len(all_articles) == 0 and OUTPUT_PATH.exists():
        print("[INFO] No new articles since last run. Keeping existing articles.json.")
        print("[INFO] last_run_utc.txt NOT updated (no new items).")
        return

    payload = {
        "generated_at": now.isoformat(),
        "articles": all_articles,
    }

    print(f"\nWriting {len(all_articles)} articles to {OUTPUT_PATH}")
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # ✅ Update last_run only when we actually included items,
    # and set it to the newest published_dt included (not wall-clock now).
    if newest_included:
        save_last_run(newest_included)
        print(f"[INFO] Updated last_run_utc.txt → {newest_included.isoformat()}")
    else:
        print("[INFO] last_run_utc.txt NOT updated (no new items).")


if __name__ == "__main__":
    main()
