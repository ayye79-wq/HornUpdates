import json, re, hashlib, html
from urllib.parse import urlparse

def strip_html(s: str) -> str:
    if not s:
        return ""
    s = html.unescape(s)
    # remove scripts/styles
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", s, flags=re.I|re.S)
    # remove all tags
    s = re.sub(r"<[^>]+>", " ", s)
    # collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s

def extract_first_img(s: str) -> str:
    if not s:
        return ""
    m = re.search(r'<img[^>]+src="([^"]+)"', s, flags=re.I)
    return m.group(1).strip() if m else ""

def normalize_source_name(name: str) -> str:
    if not name:
        return ""
    name = name.strip()
    # remove leading "- " like "- The EastAfrican"
    name = re.sub(r"^\-\s*", "", name)
    return re.sub(r"\s+", " ", name).strip()

def detect_lang(text: str) -> str:
    # simple heuristic: Arabic unicode block
    if re.search(r"[\u0600-\u06FF]", text or ""):
        return "ar"
    return "en"

def make_id(url: str) -> str:
    return hashlib.sha1((url or "").encode("utf-8")).hexdigest()[:12]

with open("articles.json", "r", encoding="utf-8") as f:
    data = json.load(f)

articles = data.get("articles", [])
cleaned = []

for a in articles:
    summary_raw = a.get("summary", "") or ""
    img = extract_first_img(summary_raw) if "<img" in summary_raw else ""

    title = (a.get("title") or "").strip()
    source_url = (a.get("source_url") or "").strip()

    # plain text summary
    summary_plain = strip_html(summary_raw)

    # normalize tags
    country_tags = a.get("country_tags") or []
    topic_tags = a.get("topic_tags") or []

    item = {
        "id": make_id(source_url),
        "title": title,
        "summary": summary_plain,
        "country_tags": country_tags,
        "topic_tags": topic_tags,
        "published_at": a.get("published_at"),
        "source_url": source_url,
        "link": source_url,                 # alias for automations
        "source_name": normalize_source_name(a.get("source_name") or ""),
        "image_url": img or "",             # empty if none
        "lang": detect_lang(title + " " + summary_plain),
    }

    cleaned.append(item)

data["articles"] = cleaned

with open("articles.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✅ Cleaned {len(cleaned)} articles -> articles.json")
