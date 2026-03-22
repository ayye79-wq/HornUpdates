#!/usr/bin/env python3
"""
backfill_context.py
Retroactively generate AI context for articles that don't have one yet.
Run once manually or add to CI if needed.

Usage:
  OPENAI_API_KEY=sk-... python3 backfill_context.py
  python3 backfill_context.py --limit 50   # process at most 50 articles
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path

try:
    import openai
except ImportError:
    print("ERROR: openai not installed. Run: pip install openai")
    sys.exit(1)

ARTICLES_JSON = Path("articles.json")


def generate_context(client, article):
    title = article.get("title", "")
    summary = article.get("summary") or article.get("excerpt") or ""
    countries = ", ".join(article.get("country_tags") or [])
    topics = ", ".join(article.get("topic_tags") or [])

    prompt = (
        f"Write 2-3 specific, informative sentences of background context for this Horn of Africa news article. "
        f"Reference specific actors, history, treaties, or ongoing dynamics relevant to THIS story — not generic regional commentary.\n\n"
        f"Title: {title}\n"
        f"Summary: {summary}\n"
        f"Countries: {countries}\n"
        f"Topics: {topics}\n\n"
        f"Context (2-3 sentences, no intro phrase like 'This article is about'):"
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=160,
    )
    return response.choices[0].message.content.strip()


def main():
    parser = argparse.ArgumentParser(description="Backfill AI context for articles")
    parser.add_argument("--limit", type=int, default=0, help="Max articles to process (0 = all)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done without writing")
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)

    client = openai.OpenAI(api_key=api_key)

    data = json.loads(ARTICLES_JSON.read_text())
    articles = data if isinstance(data, list) else data.get("articles", [])

    missing = [a for a in articles if not a.get("context")]
    print(f"Articles missing context: {len(missing)} / {len(articles)}")

    if args.limit:
        missing = missing[:args.limit]
        print(f"Processing first {args.limit}")

    updated = 0
    for i, article in enumerate(missing):
        title = article.get("title", "(no title)")
        print(f"[{i+1}/{len(missing)}] {title[:80]}")
        if args.dry_run:
            print("  (dry run — skipping)")
            continue
        try:
            ctx = generate_context(client, article)
            article["context"] = ctx
            updated += 1
            print(f"  → {ctx[:100]}...")
            time.sleep(0.3)  # rate limit buffer
        except Exception as e:
            print(f"  ERROR: {e}")
            time.sleep(2)

    if not args.dry_run and updated:
        ARTICLES_JSON.write_text(json.dumps(articles if isinstance(data, list) else {**data, "articles": articles}, ensure_ascii=False, indent=2))
        print(f"\nDone. Updated {updated} articles in articles.json")
    elif not args.dry_run:
        print("Nothing updated.")


if __name__ == "__main__":
    main()
