import json
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
import html

SITE_TITLE = "Horn Updates"
SITE_LINK = "https://hornupdates.com"
SITE_DESC = "News from the Horn of Africa — AI summaries with links to original publishers."
OUT_FILE = "rss.xml"

def parse_dt(s):
    if not s:
        return None
    s = str(s).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None

def rfc822(dt):
    if not dt:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return format_datetime(dt.astimezone(timezone.utc))

def main():
    p = Path("articles.json")
    if not p.exists():
        raise FileNotFoundError("articles.json not found in current folder")

    data = json.loads(p.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("articles", [])

    # keep valid stories
    items = [a for a in items if a.get("title") and (a.get("source_url") or a.get("link"))]

    def item_dt(a):
        return (
            parse_dt(a.get("published_at"))
            or parse_dt(a.get("published"))
            or datetime(1970, 1, 1, tzinfo=timezone.utc)
        )

    items.sort(key=item_dt, reverse=True)

    rss_items = []
    for a in items[:50]:
        title = html.escape(str(a.get("title", "")).strip())
        source_url = str(a.get("source_url") or a.get("link") or "").strip()
        link = html.escape(source_url)
        guid = link or title

        # Summary/description (strip it down a bit)
        summary_raw = a.get("summary") or a.get("excerpt") or ""
        summary = html.escape(str(summary_raw).strip())

        pub = item_dt(a)
        pubdate = rfc822(pub)

        rss_items.append(f"""\
    <item>
      <title>{title}</title>
      <link>{link}</link>
      <guid isPermaLink="true">{guid}</guid>
      <pubDate>{pubdate}</pubDate>
      <description><![CDATA[{summary}]]></description>
    </item>""")

    now = rfc822(datetime.now(timezone.utc))

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{html.escape(SITE_TITLE)}</title>
    <link>{html.escape(SITE_LINK)}</link>
    <description>{html.escape(SITE_DESC)}</description>
    <lastBuildDate>{now}</lastBuildDate>
{chr(10).join(rss_items)}
  </channel>
</rss>
"""

    Path(OUT_FILE).write_text(rss, encoding="utf-8")
    print(f"[OK] Wrote {OUT_FILE} with {min(len(items), 50)} items")

if __name__ == "__main__":
    main()
