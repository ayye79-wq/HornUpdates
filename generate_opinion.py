#!/usr/bin/env python3
"""
generate_opinion.py
Daily AI-generated opinion article for Horn Updates.
- Reads articles.json to find the most discussed topic this week
- Calls OpenAI to write a ~1,200-word analytical opinion piece
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

# Named author assignments by primary country covered
AUTHOR_MAP = {
    "Sudan":       {"name": "Amira Hassan",              "url": "/author-amira-hassan.html"},
    "South Sudan": {"name": "Amira Hassan",              "url": "/author-amira-hassan.html"},
    "Ethiopia":    {"name": "Daniel Haile",              "url": "/author-daniel-haile.html"},
    "Eritrea":     {"name": "Yared K Senbeto",           "url": "/author-yared-kunbi.html"},
    "Somalia":     {"name": "Omar Farah",                "url": "/author-omar-farah.html"},
    "Somaliland":  {"name": "Omar Farah",                "url": "/author-omar-farah.html"},
    "Kenya":       {"name": "Horn Updates Nairobi Desk", "url": None},
    "Djibouti":    {"name": "Omar Farah",                "url": "/author-omar-farah.html"},
}

EXISTING_OPINION_FILES = [
    ("opinion-sudan-war.html",     "Sudan's Civil War: Why Two Years of Fighting Have Produced No Winner"),
    ("opinion-ethiopia-sea.html",  "Ethiopia's Sea Access Push: Strategy, Risks, and the Regional Calculus"),
    ("opinion-kenya-mediator.html","Kenya as Africa's Mediator: A Role With Growing Costs"),
    ("opinion-somaliland.html",    "Somaliland's Recognition Bid: Why the International Community Keeps Hesitating"),
    ("opinion-assab.html",         "The Fate of Assab: Annexation, Access, or the Status Quo?"),
]


def title_to_slug(title, date_slug):
    """Convert an article title to a clean URL slug."""
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    slug = slug[:55].rstrip("-")
    return f"opinion-{slug}-{date_slug}"


def get_recently_used_countries(n=2):
    """Return countries used in the last n opinion articles (excluding fixed ones)."""
    base = Path(".")
    # Match any opinion file that isn't a fixed/named one
    fixed = {f for f, _ in EXISTING_OPINION_FILES}
    op_files = sorted(
        [f for f in base.glob("opinion-*.html")
         if f.name not in fixed
         and f.name not in ("opinion.html", "opinion-health.html")],
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )
    used = []
    for f in op_files[:n]:
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

Write a ~1,200-word opinion/analysis piece. The most covered country this week is {country} and the dominant theme is {topic}.

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
KEY_SIGNALS: [exactly 3 implications — separated by " | " — each 6-10 words, e.g. "Sudan: humanitarian pressure escalating | Regional spillover risk growing | Diplomatic track under pressure"]
BODY:
[Full article using <p> and <h2> tags only. No other HTML.]"""

    for attempt in range(2):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2800,
        )
        raw = response.choices[0].message.content
        if len(raw.split()) >= 700 or attempt == 1:
            return raw
        print(f"[generate_opinion] Too short ({len(raw.split())} words), retrying...")
    return raw


def parse_response(text):
    title = excerpt = body = ""
    key_signals = []
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
        elif line.startswith("KEY_SIGNALS:"):
            raw_sigs = line[12:].strip()
            key_signals = [s.strip() for s in raw_sigs.split("|") if s.strip()][:3]
        elif line.startswith("BODY:"):
            in_body = True
        elif in_body:
            body_lines.append(line)

    body = "\n".join(body_lines).strip()
    return title, countries, excerpt, body, key_signals


def country_tags_html(countries, include_opinion_tag=True):
    parts = ['<span class="tag">Opinion</span>'] if include_opinion_tag else []
    for c in countries:
        cls = COUNTRY_COLORS.get(c, "")
        parts.append(f'<span class="tag{" " + cls if cls else ""}">{c}</span>')
    return "".join(parts)


def build_article_html(title, countries, excerpt, body, date_str, slug, author_name, author_url, key_signals=None):
      tags = country_tags_html(countries)
      key_signals_html = ""
      if key_signals:
          li_items = "".join(f"<li>{s}</li>" for s in key_signals)
          key_signals_html = f'      <div class="key-signals-box"><div class="key-signals-label">What this means</div><ul class="key-signals-list">{li_items}</ul></div>'
    canonical = f"{SITE_URL}/{slug}.html"
    meta_desc = re.sub(r"<[^>]+>", "", excerpt)[:155]

    # Byline with optional link to author page
    if author_url:
        byline_html = f'By <a href="{author_url}" style="color:#2563eb;">{author_name}</a> &nbsp;·&nbsp; {date_str}'
    else:
        byline_html = f'By {author_name} &nbsp;·&nbsp; {date_str}'

    related_links = "\n".join(
        f'        <a href="/{f}">{t}</a>'
        for f, t in EXISTING_OPINION_FILES
    )

    ld_json = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": meta_desc,
        "datePublished": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "author": {"@type": "Person", "name": author_name},
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
    .key-signals-box{{background:#fef3c7;border:1px solid #fde68a;border-radius:12px;padding:14px 18px;margin:18px 0}}
      .key-signals-label{{font-size:.7rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:#92400e;margin-bottom:8px}}
      .key-signals-list{{margin:0;padding:0;list-style:none}}
      .key-signals-list li{{font-size:.92rem;color:#111827;font-weight:600;padding:3px 0;display:flex;align-items:flex-start;gap:8px}}
      .key-signals-list li::before{{content:"→";color:#d97706;font-weight:800;flex-shrink:0}}
      .related{{margin-top:20px;padding:16px;border-radius:12px;background:#f9fafb;border:1px solid #e5e7eb}}
      .related h3{{margin:0 0 10px;font-size:.8rem;font-weight:800;color:#6b7280;text-transform:uppercase;letter-spacing:.08em}}
      .related a{{display:flex;align-items:center;gap:8px;margin:0 0 8px;font-size:.95rem;font-weight:600;color:#1e3a5f;text-decoration:none;padding:8px 10px;border-radius:8px;background:#fff;border:1px solid #e5e7eb;transition:background .12s}}
      .related a:hover{{background:#eef2ff;text-decoration:none}}
      .sb-nudge{{display:flex;align-items:center;gap:14px;background:linear-gradient(135deg,#0b1628 0%,#1e3a5f 100%);border-radius:12px;padding:16px 20px;margin:20px 0;flex-wrap:wrap}}
      .sb-nudge-pulse{{width:8px;height:8px;border-radius:50%;background:#ef4444;animation:pulse 1.6s infinite;flex-shrink:0}}
      @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
      .sb-nudge-body{{flex:1;min-width:160px}}
      .sb-nudge-title{{font-size:.9rem;font-weight:800;color:#fff;margin-bottom:3px}}
      .sb-nudge-desc{{font-size:.78rem;color:#93c5fd;line-height:1.4}}
      .sb-nudge-cta{{display:inline-block;background:#f59e0b;color:#111;font-size:.82rem;font-weight:800;padding:9px 16px;border-radius:8px;text-decoration:none;white-space:nowrap;flex-shrink:0}}
    footer{{margin-top:14px;font-size:14px;color:#6b7280}}
    .site-footer{{background:#0f172a;color:#cbd5e1;text-align:center;padding:18px 12px;margin-top:0}}
    .footer-nav{{display:flex;flex-wrap:wrap;justify-content:center;gap:4px 16px;margin-bottom:10px}}
    .footer-nav a{{color:#e5e7eb;text-decoration:none;font-size:14px}}
    .footer-nav a:hover{{text-decoration:underline}}
    .footer-copy{{font-size:12px;color:#9ca3af}}
  </style>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-7773342225754932"
     crossorigin="anonymous"></script>
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
        <span class="muted">{byline_html}</span>
      </div>

      <div class="disclaimer">
        <strong>Opinion notice:</strong> This is analysis and commentary by Horn Updates editors. It does not represent the position of any government, institution, or external party.
      </div>

{key_signals_html}
      <div class="content">
        {body}
      </div>

      <div class="hr"></div>

      <div class="related">
          <h3>Keep reading</h3>
  {related_links}
        </div>

        <div class="sb-nudge">
          <div class="sb-nudge-pulse"></div>
          <div class="sb-nudge-body">
            <div class="sb-nudge-title">Follow the Horn — Weekly Brief</div>
            <div class="sb-nudge-desc">Intelligence-style briefing on Ethiopia, Sudan, Somalia and the wider Horn. Free, every week.</div>
          </div>
          <div style="display:flex;flex-direction:column;gap:8px;flex-shrink:0;">
            <form id="art-sb-form" style="display:flex;gap:6px;flex-wrap:wrap;">
              <input id="art-sb-email" type="email" placeholder="your@email.com" style="border:none;border-radius:7px;padding:8px 12px;font-size:.85rem;min-width:160px;flex:1;outline:none;"/>
              <button type="submit" style="background:#ef4444;color:#fff;border:none;border-radius:7px;padding:8px 14px;font-size:.85rem;font-weight:800;cursor:pointer;white-space:nowrap;">Subscribe</button>
            </form>
            <div id="art-sb-ok" style="display:none;font-size:.82rem;color:#6ee7b7;font-weight:700;">You're in. Signal Brief comes every week.</div>
            <a href="/signal-brief.html" style="font-size:.78rem;color:#93c5fd;text-align:center;">or read this week's brief first →</a>
          </div>
        </div>
        <script>document.getElementById('art-sb-form').addEventListener('submit',function(e){{e.preventDefault();var em=document.getElementById('art-sb-email').value.trim();if(!em)return;fetch('https://formspree.io/f/mojpgkjw',{{method:'POST',headers:{{'Content-Type':'application/json',Accept:'application/json'}},body:JSON.stringify({{email:em}})}}).then(function(r){{if(r.ok){{document.getElementById('art-sb-form').style.display='none';document.getElementById('art-sb-ok').style.display='block';}}}});}});</script>

        <a class="back" href="/opinion.html">&#8592; More analysis</a>
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


def update_opinion_index(slug, title, countries, excerpt, date_str, author_name, author_url):
    html = OPINION_HTML.read_text(encoding="utf-8")
    tags = country_tags_html(countries)

    if author_url:
        byline = f'By <a href="{author_url}">{author_name}</a> &nbsp;&middot;&nbsp; {date_str} &nbsp;&middot;&nbsp; ~1,200 words'
    else:
        byline = f'By {author_name} &nbsp;&middot;&nbsp; {date_str} &nbsp;&middot;&nbsp; ~1,200 words'

    new_post = f"""
          <div class="post">
            {tags}
            <h2><a href="/{slug}.html">{title}</a></h2>
            <p>{excerpt}</p>
            <div class="meta">{byline}</div>
          </div>
"""

    marker = '<div style="display:flex;flex-direction:column;gap:14px;">'
    if marker not in html:
        print("Warning: could not find insertion marker in opinion.html")
        return
    html = html.replace(marker, marker + new_post, 1)
    OPINION_HTML.write_text(html, encoding="utf-8")


def main():
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable is not set.")
        sys.exit(1)
    print(f"API key found (ends ...{api_key[-4:]})")

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

    # Pick named author based on primary country
    author_info = AUTHOR_MAP.get(country, {"name": "Horn Updates Editorial Team", "url": None})
    author_name = author_info["name"]
    author_url  = author_info["url"]
    print(f"Assigned author: {author_name}")

    print("Calling OpenAI API...")
    try:
        raw = generate_article(country, topic, headlines)
    except openai.AuthenticationError:
        print("ERROR: OpenAI API key is invalid or expired.")
        sys.exit(1)
    except openai.RateLimitError:
        print("ERROR: OpenAI rate limit or quota exceeded.")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR calling OpenAI: {type(e).__name__}: {e}")
        sys.exit(1)

    print("Response received. Parsing...")
    title, countries, excerpt, body, key_signals = parse_response(raw)
    if not title or not body:
        print("ERROR: Failed to parse AI response. Raw output:")
        print(raw)
        sys.exit(1)

    print(f"Title: {title}")
    print(f"Countries: {countries}")
    print(f"Excerpt: {excerpt[:80]}...")

    date_slug = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    date_str  = datetime.now(timezone.utc).strftime("%B %-d, %Y")
    slug = title_to_slug(title, date_slug)

    article_html = build_article_html(title, countries, excerpt, body, date_str, slug, author_name, author_url, key_signals)
    Path(f"{slug}.html").write_text(article_html, encoding="utf-8")
    print(f"Written: {slug}.html")

    update_opinion_index(slug, title, countries, excerpt, date_str, author_name, author_url)
    print("Updated: opinion.html")

    print("Done — new opinion article ready.")


if __name__ == "__main__":
    main()
