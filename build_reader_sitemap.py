import json
import gzip
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote

SITE = "https://hornupdates.com"
ARTICLES_JSON = Path("articles.json")          # adjust if needed
SITEMAP_XML = Path("sitemap-reader.xml")       # output
SITEMAP_GZ = Path("sitemap-reader.xml.gz")     # optional compressed output

MAX_URLS = 50000  # Google limit per sitemap

def iso_date(dt_str: str | None) -> str | None:
    """Return YYYY-MM-DD from ISO-ish string, or None."""
    if not dt_str:
        return None
    try:
        # Handle trailing Z
        dt_str = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(dt_str)
        return dt.date().isoformat()
    except Exception:
        return None

def load_articles() -> list[dict]:
    data = json.loads(ARTICLES_JSON.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return data.get("articles", []) or []

def build_loc(source_url: str) -> str:
    # Reader URLs you already use:
    # https://hornupdates.com/reader.html?url=<encoded-source-url>
    return f"{SITE}/reader.html?url={quote(source_url, safe='')}"

def main():
    if not ARTICLES_JSON.exists():
        raise FileNotFoundError(f"Missing {ARTICLES_JSON.resolve()}")

    articles = load_articles()
    urls = []

    for a in articles:
        src = a.get("source_url") or a.get("link")
        if not src:
            continue

        loc = build_loc(src)
        lastmod = iso_date(a.get("published_at")) or iso_date(a.get("generated_at"))

        urls.append((loc, lastmod))
        if len(urls) >= MAX_URLS:
            break

    now = datetime.now(timezone.utc).date().isoformat()

    # Build XML
    lines = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    for loc, lastmod in urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{loc}</loc>")
        lines.append(f"    <lastmod>{lastmod or now}</lastmod>")
        lines.append("  </url>")

    lines.append("</urlset>")
    xml = "\n".join(lines) + "\n"

    SITEMAP_XML.write_text(xml, encoding="utf-8")

    # Optional: gzip it too (Google accepts .gz)
    with gzip.open(SITEMAP_GZ, "wb") as f:
        f.write(xml.encode("utf-8"))

    print(f"[OK] Wrote {SITEMAP_XML} ({len(urls)} URLs)")
    print(f"[OK] Wrote {SITEMAP_GZ} (compressed)")

if __name__ == "__main__":
    main()
