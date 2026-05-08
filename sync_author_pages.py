#!/usr/bin/env python3
"""
sync_author_pages.py

Reads opinion.html and ensures every named-author article is listed on the
corresponding author page.  Run after publishing new opinion pieces.

Usage:
    python sync_author_pages.py          # auto-update author pages
    python sync_author_pages.py --check  # report gaps without changing files
"""

import json
import os
import re
import sys

CHECK_ONLY = "--check" in sys.argv

UNMAPPED_OUTPUT_FILE = "unmapped_authors.json"

# Map normalised author names (lower-cased) to their author page files.
# Multiple byline variants can point to the same file.
AUTHOR_PAGE = {
    "omar farah": "author-omar-farah.html",
    "daniel haile": "author-daniel-haile.html",
    "amira hassan": "author-amira-hassan.html",
    "kalid kayo": "author-kalid-kayo.html",
    "yared senbeto": "author-yared-kunbi.html",
    "yared k senbeto": "author-yared-kunbi.html",
    "nesru hussien bambis": "author-nesru-hussien-bambis.html",
}

# Bylines to skip (editorial desks, not individual author pages)
SKIP_AUTHORS = {
    "horn updates",
    "horn updates editorial",
    "horn updates editorial desk",
    "nairobi desk",
}


def parse_opinion_articles(html: str) -> list[dict]:
    """Return a list of dicts with keys: href, title, meta_raw, description, author_raw."""
    posts = re.findall(
        r'<div class="post".*?</div>\s*\n\s*</div>',
        html,
        re.DOTALL,
    )
    articles = []
    for post in posts:
        href_m = re.search(r'<h2>\s*<a href="([^"]+)"', post)
        title_m = re.search(r'<a href="[^"]+">(.*?)</a>', post)
        desc_m = re.search(r'<p>(.*?)</p>', post, re.DOTALL)
        meta_m = re.search(r'<div class="meta">(.*?)</div>', post, re.DOTALL)
        if not (href_m and title_m and meta_m):
            continue

        meta_raw = meta_m.group(1).strip()
        # Extract author from meta, e.g. "By Omar Farah &nbsp;·&nbsp; April 17, 2026 ..."
        author_raw = ""
        author_m = re.match(r'By\s+([^&·<]+)', meta_raw)
        if author_m:
            author_raw = author_m.group(1).strip()

        description = ""
        if desc_m:
            description = re.sub(r'<[^>]+>', '', desc_m.group(1)).strip()

        articles.append({
            "href": href_m.group(1),
            "title": re.sub(r'<[^>]+>', '', title_m.group(1)).strip(),
            "meta_raw": meta_raw,
            "description": description,
            "author_raw": author_raw,
        })
    return articles


def extract_date_wordcount(meta_raw: str) -> str:
    """
    Turn the opinion.html meta string into the author-page ameta string.
    Input:  "By Omar Farah &nbsp;·&nbsp; April 17, 2026 &nbsp;·&nbsp; ~2,500 words"
    Output: "Opinion · April 17, 2026 · ~2,500 words"
    """
    # Strip HTML entities and split on separators
    clean = re.sub(r'&nbsp;', ' ', meta_raw)
    clean = re.sub(r'<[^>]+>', '', clean)
    parts = [p.strip() for p in re.split(r'[·\xa0]+', clean) if p.strip()]
    # parts[0] is "By Name", rest is date, word count, "Updated", etc.
    rest = [p for p in parts[1:] if p.lower() not in ('updated',)]
    return "Opinion · " + " · ".join(rest) if rest else "Opinion"


def get_existing_hrefs_in_opinion_section(html: str) -> set[str]:
    """
    Parse only the Opinion article-list block (between <h2>Opinion</h2> and the
    next <h2>) and return all hrefs found there.
    """
    opinion_block_m = re.search(
        r'<h2>Opinion</h2>(.*?)(?=<h2>|<p style="margin-top)',
        html,
        re.DOTALL,
    )
    if not opinion_block_m:
        return set()
    block = opinion_block_m.group(1)
    return set(re.findall(r'<a href="([^"]+)"', block))


def build_article_item(href: str, title: str, ameta: str, description: str) -> str:
    desc_line = (
        f'\n        <div class="ameta" style="margin-top:4px;color:#374151;">{description}</div>'
        if description else ""
    )
    return (
        f'      <div class="article-item">\n'
        f'        <a href="{href}">{title}</a>\n'
        f'        <div class="ameta">{ameta}</div>{desc_line}\n'
        f'      </div>\n'
    )


def insert_into_opinion_section(html: str, new_item_html: str) -> str:
    """Insert new_item_html right after the opening <div class="article-list">
    that follows <h2>Opinion</h2>."""
    # Find the Opinion h2 and then the first article-list div after it
    pattern = r'(<h2>Opinion</h2>\s*\n\s*<div class="article-list">)(\s*\n)'
    replacement = r'\1\n' + new_item_html + r'\2'
    updated, count = re.subn(pattern, replacement, html, count=1)
    if count == 0:
        # Fallback: try without the explicit newline requirement
        pattern2 = r'(<h2>Opinion</h2>.*?<div class="article-list">)'
        replacement2 = r'\1\n' + new_item_html
        updated, count2 = re.subn(pattern2, replacement2, html, count=1, flags=re.DOTALL)
        if count2 == 0:
            print("  WARNING: could not find insertion point in author page")
            return html
    return updated


def main():
    with open("opinion.html", encoding="utf-8") as f:
        opinion_html = f.read()

    articles = parse_opinion_articles(opinion_html)
    print(f"Parsed {len(articles)} articles from opinion.html")

    # Group articles by author page file; warn about unmapped bylines
    page_to_articles: dict[str, list[dict]] = {}
    unmapped: dict[str, list[str]] = {}
    for art in articles:
        norm = art["author_raw"].lower().strip()
        if not norm or norm in SKIP_AUTHORS:
            continue
        page_file = AUTHOR_PAGE.get(norm)
        if not page_file:
            unmapped.setdefault(art["author_raw"], []).append(art["href"])
            continue
        page_to_articles.setdefault(page_file, []).append(art)

    if unmapped:
        print("WARNING: the following bylines have no author page mapping:")
        for byline, hrefs in sorted(unmapped.items()):
            for href in hrefs:
                print(f"  '{byline}' — {href}")
        print("  Add them to AUTHOR_PAGE in sync_author_pages.py to track their articles.")
        print()
        # Write unmapped bylines to a file so the workflow can open a GitHub issue
        with open(UNMAPPED_OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(
                [{"byline": b, "articles": hrefs} for b, hrefs in sorted(unmapped.items())],
                f,
                indent=2,
            )
        print(f"  Wrote {UNMAPPED_OUTPUT_FILE} for CI issue creation.")
    else:
        # Remove stale file from a previous run so the workflow step is a no-op
        if os.path.exists(UNMAPPED_OUTPUT_FILE):
            os.remove(UNMAPPED_OUTPUT_FILE)

    any_gap = False

    for page_file, arts in page_to_articles.items():
        try:
            with open(page_file, encoding="utf-8") as f:
                page_html = f.read()
        except FileNotFoundError:
            print(f"SKIP: {page_file} not found")
            continue

        existing = get_existing_hrefs_in_opinion_section(page_html)
        missing = [a for a in arts if a["href"] not in existing]

        if not missing:
            print(f"OK   {page_file} — all {len(arts)} article(s) already listed")
            continue

        any_gap = True
        print(f"SYNC {page_file} — adding {len(missing)} missing article(s):")
        for a in missing:
            print(f"       + {a['href']}")

        if CHECK_ONLY:
            continue

        # Insert missing articles at the top of the Opinion section (newest first)
        updated_html = page_html
        for art in reversed(missing):
            ameta = extract_date_wordcount(art["meta_raw"])
            item_html = build_article_item(
                art["href"], art["title"], ameta, art["description"]
            )
            updated_html = insert_into_opinion_section(updated_html, item_html)

        with open(page_file, "w", encoding="utf-8") as f:
            f.write(updated_html)
        print(f"       Wrote {page_file}")

    if CHECK_ONLY and any_gap:
        print("\nGaps detected (--check mode, no files changed).")
        sys.exit(1)
    elif not any_gap:
        print("\nAll author pages are in sync.")


if __name__ == "__main__":
    main()
