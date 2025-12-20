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
"""

import json
import datetime as dt
from pathlib import Path
import urllib.parse as urlparse
import re
import html
import urllib.request

import feedparser  # pip install feedparser


# ----------------------------
# 0. STRICT MODE STATE
# ----------------------------

LAST_RUN_FILE = Path(__file__).with_name("last_run_utc.txt")

def utc_now():
    return dt.datetime.now(dt.UTC)

def load_last_run():
    if LAST_RUN_FILE.exists():
        return dt.datetime.fromisoformat(LAST_RUN_FILE.read_text().strip())
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
    "https://www.addisstandard.com/feed/",
    "https://www.thereporterethiopia.com/feed/",
    "https://www.theeastafrican.co.ke/rss.xml",
    "https://sudantribune.net/feed/",
]

ALWAYS_INCLUDE_FEEDS = [
    "addisstandard.com",
    "thereporterethiopia.com",
    "hiiraan.com",
    "garoweonline.com",
    "theeastafrican.co.ke",
    "sudantribune.com",
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
    # de-duplicate while preserving order
    seen = set()
    unique = []
    for c in found:
        if c not in seen:
            unique.append(c)
            seen.add(c)
    return unique

def extract_published_dt(entry) -> dt.datetime | None:
    tm = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if tm:
        return dt.datetime(*tm[:6], tzinfo=dt.UTC)
    return None

def _strip_html(s: str) -> str:
    """Remove HTML tags/entities and normalize whitespace."""
    if not s:
        return ""
    s = html.unescape(s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _sentences(text: str):
    """Lightweight sentence splitter (good enough for news blurbs)."""
    if not text:
        return []
    text = text.strip()
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p and p.strip()]

def make_summary(entry) -> str:
    """
    Build a better summary than raw RSS teasers.
    - Prefer richer fields (content, summary_detail) when present
    - Strip HTML
    - Return up to 4 sentences
    - If teaser ends with "..." and is short, convert to a clean period
    """
    candidates = []

    # 1) Rich 'content' (list of dicts with 'value')
    content = getattr(entry, "content", None)
    if isinstance(content, list) and content:
        for c in content:
            val = (c.get("value") if isinstance(c, dict) else "") or ""
            val = _strip_html(val)
            if val:
                candidates.append(val)

    # 2) summary_detail can be better than summary
    sd = getattr(entry, "summary_detail", None)
    if isinstance(sd, dict):
        val = _strip_html(sd.get("value", "") or "")
        if val:
            candidates.append(val)

    # 3) Classic fields
    for field in ("summary", "description", "subtitle"):
        val = getattr(entry, field, "") or ""
        val = _strip_html(val)
        if val:
            candidates.append(val)

    text = max(candidates, key=len) if candidates else ""
    if not text:
        return ""

    sents = _sentences(text)
    out = " ".join(sents[:4]).strip() if sents else text

    # If it ends with "..." but is short, make it look complete
    if out.endswith("...") and len(out) < 180:
        out = out[:-3].rstrip()
        if out and not out.endswith((".", "!", "?")):
            out += "."

    return out

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

def load_existing_articles():
    """Return existing articles list from articles.json (if any)."""
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

def merge_dedupe(old_list, new_list):
    """
    Merge old + new, de-dupe by source_url (or link),
    keep newest version if duplicates appear.
    """
    merged = []
    seen = set()

    for a in new_list + old_list:
        key = (a.get("source_url") or a.get("link") or "").strip()
        if not key:
            key = (a.get("title","") + "|" + a.get("published_at","")).strip()
        if key in seen:
            continue
        seen.add(key)
        merged.append(a)

    merged.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    return merged[:MAX_ARTICLES]

def _fetch_html(url: str, timeout: int = 10) -> str:
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
    if not html_text:
        return ""
    # Remove scripts/styles
    html_text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html_text)
    # Pull paragraph-ish text
    paras = re.findall(r"(?is)<p[^>]*>(.*?)</p>", html_text)
    paras = [_strip_html(p) for p in paras]
    paras = [p for p in paras if len(p) > 40]  # keep meaningful paragraphs
    return " ".join(paras[:8]).strip()  # a few paragraphs is enough


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

            # --- EastAfrican upgrade: RSS is often teaser-only, fetch page text when needed
            host = urlparse.urlparse(link).netloc.lower()
            if "theeastafrican.co.ke" in host:
                # If too short or teaser-ish, try to expand using page text
                if (len(summary) < 170) or summary.strip().endswith("..."):
                    page_html = _fetch_html(link, timeout=10)
                    page_text = _extract_text_from_html(page_html)
                    if page_text:
                        sents = _sentences(page_text)
                        if sents:
                            summary = " ".join(sents[:4]).strip()

            combined_text = f"{title}\n{summary}"

            if not include_all and not is_horn_story(combined_text):
                continue

            published_at = published_dt.isoformat()
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

            new_articles.append(article)
            count_included += 1

        print(f"Included {count_included} items from this feed.")

    existing = load_existing_articles()
    merged_articles = merge_dedupe(existing, new_articles)

    if len(new_articles) == 0 and OUTPUT_PATH.exists():
        print("[INFO] No new articles since last run. Keeping existing articles.json.")
        save_last_run(now)
        print(f"[INFO] Updated last_run_utc.txt → {now.isoformat()}")
        return

    payload = {
        "generated_at": now.isoformat(),
        "articles": merged_articles,
    }

    print(f"\nWriting {len(merged_articles)} total articles to {OUTPUT_PATH} (new: {len(new_articles)})")
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    save_last_run(now)
    print(f"[INFO] Updated last_run_utc.txt → {now.isoformat()}")


if __name__ == "__main__":
    main()
