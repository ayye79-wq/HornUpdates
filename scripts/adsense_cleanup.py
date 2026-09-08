#!/usr/bin/env python3
"""Apply site-wide trust, consent, and crawl hygiene fixes."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TAG = '<script src="/consent-default.js"></script>'
CHOICE_TAG = '<script src="/cookie-consent.js"></script>'


def patch_html() -> int:
    changed = 0
    for path in ROOT.glob("*.html"):
        if path.name == "google85fd42af1e487dce.html":
            continue
        content = path.read_text(encoding="utf-8")
        original = content

        if DEFAULT_TAG not in content and "<head>" in content:
            content = content.replace("<head>", f"<head>\n{DEFAULT_TAG}", 1)
        if CHOICE_TAG not in content and "</body>" in content:
            content = content.replace("</body>", f"{CHOICE_TAG}\n</body>")

        if path.name != "opinion-health.html":
            content = re.sub(
                r'\s*<a href="/opinion-health\.html"[^>]*>(?:&#9679;\s*)?Pipeline status</a>',
                "",
                content,
            )

        if content != original:
            path.write_text(content, encoding="utf-8")
            changed += 1
    return changed


def patch_sitemap() -> None:
    path = ROOT / "sitemap.xml"
    content = path.read_text(encoding="utf-8")
    content = re.sub(
        r'\n\s*<url>\s*<loc>https://hornupdates\.com/opinion-health\.html</loc>.*?</url>',
        "",
        content,
        flags=re.DOTALL,
    )
    path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    count = patch_html()
    patch_sitemap()
    print(f"Patched {count} HTML files and cleaned sitemap.xml")
