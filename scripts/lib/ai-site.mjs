// Shared helpers for the AI publication: article rendering plus regeneration of
// every file that lists stories. data/ai-news.json is the single source of truth.
import { createHash } from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const SITE = 'https://hornupdates.com';
export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const NEWS_PATH = path.join(ROOT, 'data/ai-news.json');
const LIST_LIMIT = 50;

export const CATEGORIES = {
  'Models & Research': 'models',
  'AI Agents': 'agents',
  'Tools & Products': 'tools',
  'AI & Cybersecurity': 'cybersecurity',
  'Business & Jobs': 'business',
  'Policy': 'policy',
  'Africa & AI': 'africa'
};
export const TAGS = ['models', 'agents', 'tools', 'cybersecurity', 'business', 'policy', 'africa'];

export const escapeHtml = (value = '') => String(value).replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[ch]));
const escapeXml = value => String(value ?? '').replace(/[&<>]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[ch]));

export const slugify = text => String(text).toLowerCase()
  .replace(/['’]/g, '')
  .replace(/[^a-z0-9]+/g, '-')
  .replace(/^-+|-+$/g, '')
  .slice(0, 70)
  .replace(/-+$/g, '');

// Stable id for an inbox candidate, used in the approval checklist.
export const candidateId = (source, url) => `${slugify(source || 'source').slice(0, 24)}-${createHash('sha1').update(url).digest('hex').slice(0, 8)}`;

const dateParts = iso => new Date(`${iso}T12:00:00Z`);
const longDate = iso => dateParts(iso).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
const shortDate = iso => dateParts(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
const rfc822 = iso => dateParts(iso).toUTCString();
export const today = () => new Date().toISOString().slice(0, 10);

export async function loadNews() {
  return JSON.parse(await fs.readFile(NEWS_PATH, 'utf8'));
}

export async function saveNews(data) {
  await fs.writeFile(NEWS_PATH, JSON.stringify(data, null, 2) + '\n');
}

const sorted = stories => [...stories].sort((a, b) => b.published.localeCompare(a.published));

export function renderArticle(story, sections) {
  const url = `${SITE}${story.internal_url}`;
  const paragraphs = list => (list || []).map(p => `<p>${escapeHtml(p)}</p>`).join('');
  const block = (heading, list) => list?.length ? `<h2>${heading}</h2>${paragraphs(list)}` : '';
  const ld = JSON.stringify({
    '@context': 'https://schema.org',
    '@type': 'NewsArticle',
    headline: story.title,
    datePublished: story.published,
    dateModified: story.modified || story.published,
    author: { '@type': 'Organization', name: 'Horn Updates Editorial Desk' },
    publisher: { '@type': 'Organization', name: 'Horn Updates', url: SITE },
    mainEntityOfPage: url
  }).replace(/</g, '\\u003c');

  return `<!doctype html><html lang="en"><head><script src="/consent-default.js"></script><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(story.title)} | Horn Updates</title><meta name="description" content="${escapeHtml(story.meta_description || story.summary)}"><link rel="canonical" href="${url}"><meta property="og:type" content="article"><meta property="og:title" content="${escapeHtml(story.title)}"><meta property="og:description" content="${escapeHtml(story.summary)}"><meta property="og:url" content="${url}"><link rel="stylesheet" href="/redesign.css"><script type="application/ld+json">${ld}</script></head><body><header class="site-header"><div class="masthead"><a class="brand" href="/">Horn Updates<small>AI news. Without the noise.</small></a><nav class="nav"><a href="/#latest">Latest AI</a><a href="/#models">Models</a><a href="/#agents">Agents</a><a href="/#cyber">Cybersecurity</a><a href="/#africa">Africa &amp; AI</a><a href="/newsletter.html">Briefing</a></nav></div></header><main><article class="article-shell"><div class="eyebrow">${escapeHtml(story.category)} · ${longDate(story.published)}</div><h1>${escapeHtml(story.title)}</h1><p class="dek">${escapeHtml(story.summary)}</p><div class="byline">By <strong>Horn Updates Editorial Desk</strong> · Updated ${longDate(story.modified || story.published)}</div><div class="article-body">${paragraphs(sections.what_happened)}${block('What changed', sections.what_changed)}${block('Why it matters', sections.why_it_matters)}${block('What to watch', sections.what_to_watch)}<div class="article-box"><strong>Primary source</strong><p><a href="${escapeHtml(story.source_url)}" rel="noopener noreferrer">${escapeHtml(story.source)} — “${escapeHtml(story.source_title || story.title)}”</a></p></div><p class="corrections">Horn Updates separates source facts from our analysis. See our <a href="/editorial-policy.html">editorial policy</a> or <a href="/contact.html">send a correction</a>.</p></div></article></main><footer class="footer"><div class="footer-inner"><span>© ${story.published.slice(0, 4)} Horn Updates</span><nav><a href="/editorial-policy.html">Editorial policy</a><a href="/about.html">About</a><a href="/contact.html">Contact</a><a href="/privacy.html">Privacy</a></nav></div></footer><script src="/cookie-consent.js"></script></body></html>
`;
}

async function replaceBetween(file, start, end, replacement) {
  const full = path.join(ROOT, file);
  const html = await fs.readFile(full, 'utf8');
  const i = html.indexOf(start);
  const j = html.indexOf(end, i + start.length);
  if (i < 0 || j < 0) throw new Error(`${file}: could not find generated region markers`);
  await fs.writeFile(full, html.slice(0, i + start.length) + replacement + html.slice(j));
}

async function buildArchive(stories) {
  const cards = stories.slice(0, LIST_LIMIT).map(s => {
    const tags = s.tags?.length ? s.tags : [CATEGORIES[s.category] || 'models'];
    return `<article class="story" data-category="${escapeHtml(tags.join(' '))}"><div class="eyebrow">${escapeHtml(s.category)} · ${shortDate(s.published)}</div><h3><a href="${escapeHtml(s.internal_url)}">${escapeHtml(s.title)}</a></h3><p>${escapeHtml(s.card_summary || s.summary)}</p></article>`;
  }).join('');
  await replaceBetween('ai/index.html', '<div class="story-grid" id="story-grid">', '</div><div class="empty-filter"', cards);
}

async function buildSitemap(stories) {
  const full = path.join(ROOT, 'sitemap.xml');
  const xml = await fs.readFile(full, 'utf8');
  const lines = xml.split('\n').filter(line => !/<loc>https:\/\/hornupdates\.com\/ai\/[^<]+\.html<\/loc>/.test(line));
  const newest = stories[0]?.modified || stories[0]?.published || today();
  const touch = loc => line => line.includes(`<loc>${loc}</loc>`) ? line.replace(/<lastmod>[^<]*<\/lastmod>/, `<lastmod>${newest}</lastmod>`) : line;
  const updated = lines.map(touch(`${SITE}/`)).map(touch(`${SITE}/ai/`));
  const at = updated.findIndex(line => line.includes(`<loc>${SITE}/ai/</loc>`));
  if (at < 0) throw new Error('sitemap.xml: missing /ai/ entry');
  const entries = stories.map(s => `  <url><loc>${SITE}${s.internal_url}</loc><lastmod>${s.modified || s.published}</lastmod><changefreq>monthly</changefreq><priority>0.9</priority></url>`);
  updated.splice(at + 1, 0, ...entries);
  await fs.writeFile(full, updated.join('\n'));
}

async function buildFeed(stories, builtAt) {
  const items = stories.slice(0, LIST_LIMIT).map(s => {
    const link = `${SITE}${s.internal_url}`;
    return `<item><title>${escapeXml(s.title)}</title><link>${link}</link><guid>${link}</guid><pubDate>${rfc822(s.published)}</pubDate><description>${escapeXml(s.summary)}</description></item>`;
  }).join('\n');
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Horn Updates — AI News Without the Noise</title><link>${SITE}/</link><description>Selected AI news and analysis covering models, agents, cybersecurity, business, policy and Africa &amp; AI.</description><language>en</language><lastBuildDate>${new Date(builtAt).toUTCString()}</lastBuildDate>
${items}
</channel></rss>
`;
  await fs.writeFile(path.join(ROOT, 'feed.xml'), xml);
}

// Regenerates the archive cards, sitemap and RSS from data/ai-news.json.
export async function buildSite({ touch = false } = {}) {
  const data = await loadNews();
  data.stories = sorted(data.stories);
  if (touch) data.updated_at = new Date().toISOString().replace(/\.\d+Z$/, 'Z');
  await saveNews(data);
  await buildArchive(data.stories);
  await buildSitemap(data.stories);
  await buildFeed(data.stories, data.updated_at);
  return data;
}
