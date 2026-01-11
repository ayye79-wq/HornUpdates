import os, json, re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict

OUTPUT_PATH = Path("articles.json")

def now_utc_iso():
    return datetime.now(timezone.utc).isoformat()

def normalize_text(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s

def load_existing() -> Dict:
    if OUTPUT_PATH.exists():
        return json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    return {"generated_at": None, "articles": []}

def dedupe(existing: List[Dict], incoming: List[Dict]) -> List[Dict]:
    seen = set()
    merged = []

    for a in existing + incoming:
        key = (a.get("source"), a.get("source_url") or a.get("link"), a.get("title"))
        if key in seen:
            continue
        seen.add(key)
        merged.append(a)
    return merged

# -----------------------------
# SOURCE ADAPTERS (plug-in style)
# -----------------------------

def fetch_telegram() -> List[Dict]:
    """
    Telegram via Telethon (recommended).
    Requires:
      - TELEGRAM_API_ID
      - TELEGRAM_API_HASH
    and a session will be created on first run.
    """
    try:
        from telethon import TelegramClient
    except ImportError:
        print("[WARN] Telethon not installed. Run: pip install telethon")
        return []

    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    if not api_id or not api_hash:
        print("[WARN] TELEGRAM_API_ID / TELEGRAM_API_HASH not set. Skipping Telegram.")
        return []

    # Your channel allowlist (usernames without @)
    channels = [
        "FanaMediaCorp",
        "EthiopianPressAgency",
        # add more...
    ]

    results: List[Dict] = []

    client = TelegramClient("ethio_pulse_session", int(api_id), api_hash)

    async def _run():
        await client.start()
        for ch in channels:
            try:
                entity = await client.get_entity(ch)
                async for msg in client.iter_messages(entity, limit=25):
                    if not msg.message:
                        continue

                    text = normalize_text(msg.message)
                    title = text[:90] + ("…" if len(text) > 90 else "")
                    link = f"https://t.me/{ch}/{msg.id}"

                    results.append({
                        "title": title,
                        "summary": text[:240] + ("…" if len(text) > 240 else ""),
                        "source": f"Telegram: @{ch}",
                        "source_url": link,
                        "published_at": (msg.date.replace(tzinfo=timezone.utc).isoformat()
                                         if msg.date else now_utc_iso()),
                        "category": "Pulse",
                        "country": "Ethiopia",
                        "source_type": "telegram",
                    })
            except Exception as e:
                print(f"[WARN] Telegram channel {ch} failed: {e}")

        await client.disconnect()

    import asyncio
    asyncio.run(_run())
    return results

def fetch_rss_feeds() -> List[Dict]:
    """
    For gov/media sites that provide RSS/Atom.
    """
    try:
        import feedparser
    except ImportError:
        print("[WARN] feedparser not installed. Run: pip install feedparser")
        return []

    feeds = [
        # add Ethiopia-focused press feeds here if available
        # "https://example.gov.et/rss",
    ]

    results: List[Dict] = []
    for url in feeds:
        d = feedparser.parse(url)
        for e in d.entries[:25]:
            title = normalize_text(getattr(e, "title", ""))
            link = getattr(e, "link", None)
            summary = normalize_text(getattr(e, "summary", ""))[:280]
            published = getattr(e, "published", None) or getattr(e, "updated", None) or now_utc_iso()

            if not title or not link:
                continue

            results.append({
                "title": title,
                "summary": summary,
                "source": "RSS Feed",
                "source_url": link,
                "published_at": published,
                "category": "Pulse",
                "country": "Ethiopia",
                "source_type": "rss",
            })
    return results

def fetch_x() -> List[Dict]:
    """
    X API requires credentials and is the most stable option.
    We'll wire it once you choose the method:
      A) Official X API (recommended)
      B) Scraping (not recommended; breaks/ToS risk)
    """
    return []

def main():
    existing_payload = load_existing()
    existing = existing_payload.get("articles", [])

    new_items: List[Dict] = []
    new_items += fetch_telegram()
    new_items += fetch_rss_feeds()
    new_items += fetch_x()

    merged = dedupe(existing, new_items)

    payload = {
        "generated_at": now_utc_iso(),
        "articles": merged
    }

    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] Wrote {len(merged)} total items (new: {len(new_items)})")

if __name__ == "__main__":
    main()
