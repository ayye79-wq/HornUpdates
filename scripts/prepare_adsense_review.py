#!/usr/bin/env python3
"""Remove legacy automated publishing output before an AdSense review.

This script is intentionally conservative: two date-stamped, individually
edited articles are retained, while the repetitive daily-generator output is
removed. Deleted URLs receive a 410 response so search engines can retire them.
"""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent.parent
KEEP_DATED = {
    "opinion-eritrea-us-sanctions-red-sea-2026-05-05.html",
    "opinion-tigray-council-debretsion-2026-05-05.html",
}
REMOVE_PAGES = {
    "opinion-health.html",
    "author-amira-hassan.html",
    "author-daniel-haile.html",
    "author-omar-farah.html",
    "author-yared-kunbi.html",
    "author-yared-kumbi.html",
    "author-nesru-hussien-bambis.html",
}


def generated_daily_pages() -> list[Path]:
    pattern = re.compile(r"^opinion-.*-2026-\d{2}-\d{2}\.html$")
    return sorted(
        path for path in ROOT.glob("opinion-*.html")
        if pattern.match(path.name) and path.name not in KEEP_DATED
    )


def clean_redirects(removed: set[str]) -> None:
    path = ROOT / "_redirects"
    lines = path.read_text(encoding="utf-8").splitlines()
    kept = []
    for line in lines:
        retired_match = re.match(r"^/([^ ]+\.html)\s+.*\s410!$", line.strip())
        if retired_match and (ROOT / retired_match.group(1)).exists():
            # A reviewed page may have been restored after an earlier cleanup.
            # Never leave a force-410 rule in front of a live file.
            continue
        if any(f"/{name}" in line for name in removed):
            continue
        kept.append(line)
    kept.extend([f"/{name}  /opinion.html  410!" for name in sorted(removed)])
    path.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")


def clean_sitemap(removed: set[str]) -> None:
    path = ROOT / "sitemap.xml"
    content = path.read_text(encoding="utf-8")
    for name in removed:
        content = re.sub(
            rf"\s*<url>\s*<loc>https://hornupdates\.com/{re.escape(name)}</loc>.*?</url>",
            "",
            content,
            flags=re.DOTALL,
        )
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def main() -> None:
    generated = generated_daily_pages()
    # On a fresh checkout this catches an accidental scope expansion. On a
    # second pass the date-stamped pages have already been removed.
    if generated and not 70 <= len(generated) <= 90:
        raise SystemExit(f"Safety stop: expected 70-90 generated pages, found {len(generated)}")

    removed = {path.name for path in generated} | REMOVE_PAGES
    for name in sorted(removed):
        path = ROOT / name
        if path.exists():
            path.unlink()

    clean_redirects(removed)
    clean_sitemap(removed)
    print(
        f"Removed {len(generated)} generated articles and "
        f"{len(REMOVE_PAGES)} internal/unverified profile pages"
    )


if __name__ == "__main__":
    main()
