# update_pulse.py  (EthioPulse)
# Produces: ethio_articles.json (separate from HornUpdates articles.json)

import os
import re
import json
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

OUTPUT_PATH = Path(__file__).resolve().parent / "ethio_articles.json"
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / "ethio" / "ethio_articles.json"
print("✅ EthioPulse OUTPUT_PATH:", OUTPUT_PATH)



def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s


def load_existing() -> Dict[str, Any]:
    if OUTPUT_PATH.exists():
        try:
            return json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        except Exception:
            # If file is corrupted for any reason, start clean
            return {"generated_at": None, "articles": []}
    return {"generated_at": None, "articles": []}


def dedupe(existing: List[Dict[str, Any]], incoming: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate by (source, url, title). Keeps first occurrence order.
    """
    seen = set()
    merged: List[Dict[str, Any]] = []

    for a in (existing or []) + (incoming or []):
        key = (
            a.get("source"),
            a.get("source_url") or a.get("link"),
            a.get("title"),
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(a)

    return merged


# -----------------------------
# SOURCE ADAPTERS (plug-in style)
# -----------------------------

def fetch_telegram() -> List[Dict[str, Any]]:
    """
    Telegram via Telethon (recommended).
    Requires env vars:
      - TELEGRAM_API_ID
      - TELEGRAM_API_HASH
    A session file will be created on first run.
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
        "addisstandard",
        "EthiopiaGov",
        "ENA_Ethiopia",
        "OMN_Oromia",
        "EBCWorld",
        "WaltaInfo",
    ]

    results: List[Dict[str, Any]] = []
    client = TelegramClient("ethio_pulse_session", int(api_id), api_hash)

    async def _run() -> None:
        await client.start()
        for ch in channels:
            try:
                entity = await client.get_entity(ch)
                async for msg in client.iter_messages(entity, limit=25):
                    if not getattr(msg, "message", None):
                        continue

                    text = normalize_text(msg.message)
                    if not text:
                        continue

                    title = text[:90] + ("…" if len(text) > 90 else "")
                    link = f"https://t.me/{ch}/{msg.id}"

                    # Telethon's msg.date is typically timezone-aware; but we normalize to UTC ISO anyway.
                    published_at = now_utc_iso()
                    if getattr(msg, "date", None):
                        dt = msg.date
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        published_at = dt.astimezone(timezone.utc).isoformat()

                    results.append(
                        {
                            "title": title,
                            "summary": text[:240] + ("…" if len(text) > 240 else ""),
                            "source": f"Telegram: @{ch}",
                            "source_url": link,
                            "published_at": published_at,
                            "category": "Pulse",
                            "country": "Ethiopia",
                            "source_type": "telegram",
                        }
                    )
            except Exception as e:
                print(f"[WARN] Telegram channel {ch} failed: {e}")

        await client.disconnect()

    asyncio.run(_run())
    return results


def fetch_rss_feeds() -> List[Dict[str, Any]]:
    """
    For Ethiopia-focused RSS/Atom feeds (optional).
    """
    try:
        import feedparser
    except ImportError:
        print("[WARN] feedparser not installed. Run: pip install feedparser")
        return []

    feeds = [
        # Add Ethiopia-focused RSS feeds here if available
        # "https://example.com/rss",
    ]

    results: List[Dict[str, Any]] = []
    for url in feeds:
        d = feedparser.parse(url)
        for e in getattr(d, "entries", [])[:25]:
            title = normalize_text(getattr(e, "title", ""))
            link = getattr(e, "link", None)
            summary = normalize_text(getattr(e, "summary", ""))[:280]

            published = getattr(e, "published", None) or getattr(e, "updated", None) or now_utc_iso()

            if not title or not link:
                continue

            results.append(
                {
                    "title": title,
                    "summary": summary,
                    "source": "RSS Feed",
                    "source_url": link,
                    "published_at": published,
                    "category": "Pulse",
                    "country": "Ethiopia",
                    "source_type": "rss",
                }
            )

    return results


def fetch_x() -> List[Dict[str, Any]]:
    """
    Placeholder for X integration.
    """
    return []


def main() -> None:
    existing_payload = load_existing()
    existing = existing_payload.get("articles", [])

    new_items: List[Dict[str, Any]] = []
    new_items += fetch_telegram()
    new_items += fetch_rss_feeds()
    new_items += fetch_x()

    merged = dedupe(existing, new_items)

    payload = {
        "generated_at": now_utc_iso(),
        "articles": merged,
    }

    OUTPUT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"[OK] Wrote {len(merged)} total items (new fetched this run: {len(new_items)})")
    print(f"[OK] Output → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
