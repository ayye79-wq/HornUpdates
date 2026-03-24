#!/usr/bin/env python3
"""
generate_opinion.py
Weekly AI-generated opinion article for Horn Updates.
- Reads articles.json to find the most discussed topic this week
- Calls OpenAI to write a ~900-word analytical opinion piece
- Saves the article as HTML and prepends it to opinion.html
"""

import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import openai
except ImportError:
    print("ERROR: openai package not installed. Run: pip install openai")
    sys.exit(1)

ARTICLES_JSON = Path("articles.json")
OPINION_HTML = Path("opinion.html")
SITE_URL = "https://hornupdates.com"

COUNTRY_COLORS = {
    "Sudan":       "tag2",
    "South Sudan": "tag2",
    "Ethiopia":    "tag-green",
    "Eritrea":     "",
    "Somalia":     "",
    "Somaliland":  "",
    "Kenya":       "tag-yellow",
    "Djibouti":    "",
}

HORN_COUNTRIES = list(COUNTRY_COLORS.keys())

EXISTING_OPINION_FILES = [
    ("opinion-sudan-war.html",     "Sudan's Civil War: Why Two Years of Fighting Have Produced No Winner"),
    ("opinion-ethiopia-sea.html",  "Ethiopia's Sea Access Push: Strategy, Risks, and the Regional Calculus"),
    ("opinion-kenya-mediator.html","Kenya as Africa's Mediator: A Role With Growing Costs"),
    ("opinion-somaliland.html",    "Somaliland's Recognition Bid: Why the International Community Keeps Hesitating"),
    ("opinion-assab.html",         "The Fate of Assab: Annexation, Access, or the Status Quo?"),
]


def get_recently_used_countries(n=2):
    """Return countries used in the last n auto-generated opinion articles."""
    base = Path(".")
    auto_files = sorted(base.glob("opinion-auto-*.html"), reverse=True)
    used = []
    for f in auto_files[:n]:
        content = f.read_text(encoding="utf-8")
        for country in HORN_COUNTRIES:
            if f">{country}<" in content and country not in used:
                used.append(country)
                break
    return used


def find_trending_topic(articles):
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent = []
    for a in articles:
        pub = a.get("published_at", "")
        if pub:
            try:
                dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                if dt > week_ago:
                    recent.append(a)
            except Exception:
                pass

    if len(recent) < 10:
        recent = articles[:40]

    country_counter = Counter()
    topic_counter = Counter()
    for a in recent:
        for c in (a.get("country_tags") or []):
            if c in HORN_COUNTRIES:
                country_counter[c] += 1
        for t in (a.get("topic_tags") or []):
            topic_counter[t] += 1

    # Pick top country, but avoid repeating the same country as the last 2 articles
    recently_used = get_recently_used_countries(n=2)
    ranked = country_counter.most_common()
    top_country = ranked[0][0] if ranked else "Ethiopia"

    if top_country in recently_used and len(ranked) > 1:
        for country, _ in ranked:
            if country not in recently_used:
                print(f"[variety] Skipping {top_country} (used recently), using {country} instead")
                top_country = country
                break

    top_topic = topic_counter.most_common(1)[0][0] if topic_counter else "Politics & Governance"

    samples = [
        a["title"] for a in recent
        if top_country in (a.get("country_tags") or [])
    ][:8]

    return top_country, top_topic, samples


def generate_article(country, topic, headlines):
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    headline_list = "\n".join(f"- {h}" for h in headlines) if headlines else "(no specific headlines)"

    prompt = f"""You are a senior analyst writing for Horn Updates, a regional news site covering the Horn of Africa (Ethiopia, Somalia, Sudan, South Sudan, Eritrea, Kenya, Djibouti, Somaliland).

Write a ~900-word opinion/analysis piece. The most covered country this week is {country} and the dominant theme is {topic}.

This week's relevant headlines from our newsroom:
{headline_list}

Requirements:
- Pick ONE specific, timely angle — not a broad overview
- Write a compelling, specific title that a reader would want to click
- Use 3–4 subheadings (H2 level) to structure the piece
- Be analytical and evidence-based; cite specific facts, real actors, and dates where relevant
- Tone: serious and informed, like The Economist's Africa coverage or Foreign Affairs
- Do NOT be preachy; avoid clichés like "Africa must..." or "the world needs to..."
- The final paragraph should offer a concrete, specific forward-looking observation

Strictly follow this output format — no extra text outside it:

TITLE: [your title]
COUNTRIES: [comma-separated from: Ethiopia, Somalia, Sudan, South Sudan, Eritrea, Kenya, Djibouti, Somaliland]
EXCERPT: [2-sentence teaser for the article card, ~55 words, punchy]
BODY:
[Full article using <p> and <h2> tags only. No other HTML.]"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1800,
    )
    return response.choices[0].message.content


def parse_response(text):
    title = excerpt = body = ""
    countries = []
    body_lines = []
    in_body = False

    for line in text.strip().splitlines():
        if line.startswith("TITLE:"):
            title = line[6:].strip()
        elif line.startswith("COUNTRIES:"):
            countries = [c.strip() for c in line[10:].strip().split(",")]
        elif line.startswith("EXCERPT:"):
            excerpt = line[8:].strip()
        elif line.startswith("BODY:"):
            in_body = True
        elif in_body:
            body_lines.append(line)

    body = "\n".join(body_lines).strip()
    return title, countries, excerpt, body


def country_tags_html(countries, include_opinion_tag=True):
    parts = ['<span class="tag">Opinion</span>'] if include_opinion_tag else []
    for c in countries:
        cls = COUNTRY_COLORS.get(c, "")
        parts.append(f'<span class="tag{" " + cls if cls else ""}">{c}</span>')
    return "".join(parts)


def build_article_html(title, countries, excerpt, body, date_str, slug):
    tags = country_tags_html(countries)
    canonical = f"{SITE_URL}/{slug}.html"
    meta_desc = re.sub(r"<[^>]+>", "", excerpt)[:155]

    related_links = "\n".join(
        f'        <a href="/{f}">{t}</a>'
        for f, t in EXISTING_OPINION_FILES
    )

    countries_json = json.dumps(countries)
    ld_json = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": meta_desc,
        "datePublished": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "author": {"@type": "Organization", "name": "Horn Updates"},
        "publisher": {
            "@type": "Organization",
            "name": "Horn Updates",
            "url": "https://hornupdates.com",
            "logo": {"@type": "ImageObject", "url": "https://hornupdates.com/Horn1_logo.png"}
        },
        "url": canonical,
        "keywords": ", ".join(countries),
        "articleSection": "Opinion & Analysis"
    }, indent=2)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title} | Horn Updates</title>
  <meta name="description" content="{meta_desc}" />
  <meta name="robots" content="index,follow" />
  <link rel="canonical" href="{canonical}" />
  <script type="application/ld+json">{ld_json}</script>
  <style>
    *{{box-sizing:border-box}}
    body{{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;line-height:1.75;color:#111827;background:#f5f6f8}}
    a{{color:#2563eb;text-decoration:none}}
    a:hover{{text-decoration:underline}}
    .wrap{{max-width:920px;margin:0 auto;padding:18px}}
    .card{{background:#fff;border-radius:14px;padding:22px 24px;box-shadow:0 6px 22px rgba(0,0,0,.08)}}
    .top{{display:flex;align-items:center;gap:10px;margin-bottom:12px}}
    .logo{{width:34px;height:34px;border-radius:8px}}
    .muted{{color:#6b7280;font-size:14px}}
    .nav{{display:flex;gap:12px;flex-wrap:wrap;margin:8px 0 0}}
    h1{{margin:14px 0 8px;font-size:28px;line-height:1.25}}
    h2{{font-size:1.1rem;margin:24px 0 8px;color:#1e3a5f}}
    .meta{{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:8px 0 14px}}
    .tag{{display:inline-block;font-size:12px;padding:4px 10px;border-radius:999px;background:#eef2ff;color:#3730a3}}
    .tag2{{background:#fef2f2;color:#991b1b}}
    .tag-green{{background:#ecfdf5;color:#065f46}}
    .tag-yellow{{background:#fefce8;color:#854d0e}}
    .disclaimer{{margin:12px 0 16px;padding:12px;border-radius:12px;background:#fff7ed;border:1px solid #fed7aa;color:#7c2d12;font-size:14px}}
    .content p{{margin:0 0 16px;font-size:1.02rem}}
    .content h2{{font-size:1.1rem;margin:24px 0 8px;color:#1e3a5f}}
    .hr{{height:1px;background:#e5e7eb;margin:20px 0}}
    .back{{display:inline-block;margin-top:6px;font-weight:600}}
    .related{{margin-top:20px;padding:14px;border-radius:12px;background:#f9fafb;border:1px solid #e5e7eb}}
    .related h3{{margin:0 0 8px;font-size:.95rem;color:#6b7280;text-transform:uppercase;letter-spacing:.04em}}
    .related a{{display:block;margin:4px 0;font-size:.95rem}}
    footer{{margin-top:14px;font-size:14px;color:#6b7280}}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">

      <div class="top">
        <img class="logo" src="Horn1_logo.png" alt="Horn Updates logo" />
        <div>
          <strong>Horn Updates</strong>
          <div class="muted">Opinion &amp; Analysis</div>
        </div>
      </div>

      <div class="nav">
        <a href="/">Home</a>
        <a href="/opinion.html">Opinion</a>
        <a href="/about.html">About</a>
        <a href="/editorial-policy.html">Editorial Policy</a>
        <a href="/contact.html">Contact</a>
      </div>

      <h1>{title}</h1>

      <div class="meta">
        {tags}
        <span class="muted">By Horn Updates &nbsp;·&nbsp; {date_str}</span>
      </div>

      <div class="disclaimer">
        <strong>Opinion notice:</strong> This is analysis and commentary by Horn Updates editors. It does not represent the position of any government, institution, or external party.
      </div>

      <div class="content">
        {body}
      </div>

      <div class="hr"></div>

      <div class="related">
        <h3>Related analysis</h3>
{related_links}
      </div>

      <a class="back" href="/opinion.html">&#8592; Back to Opinion</a>
      <footer>&copy; 2026 Horn Updates. All rights reserved.</footer>

    </div>
  </div>
  <footer class="site-footer">
    <nav class="footer-nav">
      <a href="/index.html">Home</a>
      <a href="/about.html">About</a>
      <a href="/editorial-policy.html">Editorial Policy</a>
      <a href="/privacy.html">Privacy</a>
      <a href="/terms.html">Terms</a>
      <a href="/contact.html">Contact</a>
    </nav>
    <div class="footer-copy">&copy; 2026 Horn Updates. All rights reserved.</div>
  </footer>
</body>
</html>"""


def update_opinion_index(slug, title, countries, excerpt, date_str):
    html = OPINION_HTML.read_text(encoding="utf-8")
    tags = country_tags_html(countries)

    new_post = f"""
          <div class="post">
            {tags}
            <h2><a href="/{slug}.html">{title}</a></h2>
            <p>{excerpt}</p>
            <div class="meta">By Horn Updates &nbsp;&middot;&nbsp; {date_str} &nbsp;&middot;&nbsp; ~900 words</div>
          </div>
"""

    marker = '<div style="display:flex;flex-direction:column;gap:14px;">'
    if marker not in html:
        print("Warning: could not find insertion marker in opinion.html")
        return
    html = html.replace(marker, marker + new_post, 1)
    OPINION_HTML.write_text(html, encoding="utf-8")


def main():
    # Check API key first — gives a clear error if secret is missing
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable is not set.")
        print("Add it as a GitHub secret named OPENAI_API_KEY in your repo settings.")
        sys.exit(1)
    print(f"API key found (ends ...{api_key[-4:]})")

    # Load articles
    if not ARTICLES_JSON.exists():
        print(f"ERROR: {ARTICLES_JSON} not found")
        sys.exit(1)
    data = json.loads(ARTICLES_JSON.read_text())
    articles = data.get("articles", [])
    if not articles:
        print("No articles found in articles.json")
        sys.exit(1)
    print(f"Loaded {len(articles)} articles")

    country, topic, headlines = find_trending_topic(articles)
    print(f"Trending this week: {country} / {topic} ({len(headlines)} matching headlines)")

    print("Calling OpenAI API...")
    try:
        raw = generate_article(country, topic, headlines)
    except openai.AuthenticationError:
        print("ERROR: OpenAI API key is invalid or expired. Check your OPENAI_API_KEY secret.")
        sys.exit(1)
    except openai.RateLimitError:
        print("ERROR: OpenAI rate limit or quota exceeded. Check your account billing.")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR calling OpenAI: {type(e).__name__}: {e}")
        sys.exit(1)

    print("Response received. Parsing...")
    title, countries, excerpt, body = parse_response(raw)
    if not title or not body:
        print("ERROR: Failed to parse AI response. Raw output:")
        print(raw)
        sys.exit(1)

    print(f"Title: {title}")
    print(f"Countries: {countries}")
    print(f"Excerpt: {excerpt[:80]}...")

    date_str = datetime.now(timezone.utc).strftime("%B %Y")
    date_slug = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = f"opinion-auto-{date_slug}"

    article_html = build_article_html(title, countries, excerpt, body, date_str, slug)
    Path(f"{slug}.html").write_text(article_html, encoding="utf-8")
    print(f"Written: {slug}.html")

    update_opinion_index(slug, title, countries, excerpt, date_str)
    print("Updated: opinion.html")

    print("Done — new opinion article ready.")


if __name__ == "__main__":
    main()
