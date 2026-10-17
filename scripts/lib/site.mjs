// Shared rendering for Horn Updates. data/signal.json is the single source of truth for
// The Signal; this module regenerates every page and file that lists editions:
// index.html, signal-brief.html, signal/<date>.html, sitemap.xml and feed.xml.
import { createHash } from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const SITE = 'https://hornupdates.com';
export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const SIGNAL_PATH = path.join(ROOT, 'data/signal.json');
const FEED_LIMIT = 30;
const HOME_ITEMS = 6;

export const COUNTRIES = ['Ethiopia', 'Eritrea', 'Djibouti', 'Somalia', 'Sudan', 'South Sudan', 'Kenya', 'Regional'];
export const TOPICS = ['Politics', 'Conflict & Security', 'Economy', 'Humanitarian', 'Diplomacy', 'Rights & Society'];

// Background reading Claude may attach to a Signal item.
export const EXPLAINERS = [
  { url: '/explainer-tigray.html', title: 'The Tigray war explained', blurb: 'Causes, human cost, the Pretoria deal and what remains unresolved.' },
  { url: '/explainer-gerd-nile.html', title: 'GERD and the Nile dispute', blurb: 'Why Ethiopia, Egypt and Sudan have not reached a deal on the dam.' },
  { url: '/explainer-ethiopia-sea.html', title: 'Why Ethiopia wants Red Sea access', blurb: 'The landlocked state’s options and how they reshape the region.' },
  { url: '/explainer-ethiopia-eritrea-border.html', title: 'The Ethiopia–Eritrea border', blurb: 'War, the Algiers Agreement, 2018 peace and an undemarcated line.' },
  { url: '/explainer-sudan-ethiopia-border.html', title: 'Sudan’s war and Ethiopia’s west', blurb: 'Benishangul-Gumuz, the dam and the risk of spillover.' },
  { url: '/explainer-iran-uae-ethiopia.html', title: 'Iran, the UAE and the Horn', blurb: 'How Gulf and Iran tensions reach Ethiopia through trade and the Red Sea.' },
  { url: '/explainer-sudan-war.html', title: 'Sudan’s war explained', blurb: 'Why it started, who is fighting and what comes next.' },
  { url: '/explainer-somalia-al-shabaab.html', title: 'How al-Shabaab survived', blurb: 'Why Somalia’s insurgency endures and what the next phase means.' },
  { url: '/explainer-south-sudan-crisis.html', title: 'South Sudan’s polycrisis', blurb: 'Violence, elections, hunger and displacement at once.' },
  { url: '/explainer-south-sudan-elections.html', title: 'Can South Sudan hold elections?', blurb: 'Why the vote keeps slipping and what it would take.' }
];

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

const at = iso => new Date(`${iso}T12:00:00Z`);
export const longDate = iso => at(iso).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
const shortDate = iso => at(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
export const today = () => new Date().toISOString().slice(0, 10);
const pad = n => String(n).padStart(2, '0');

export async function loadSignal() {
  try { return JSON.parse(await fs.readFile(SIGNAL_PATH, 'utf8')); }
  catch { return { updated_at: null, editions: [] }; }
}

export async function saveSignal(data) {
  data.editions.sort((a, b) => b.date.localeCompare(a.date));
  await fs.writeFile(SIGNAL_PATH, JSON.stringify(data, null, 2) + '\n');
}

// ── Page chrome ────────────────────────────────────────────────────────────────

const NAV = [
  ['/signal-brief.html', 'The Signal'],
  ['/explainers.html', 'Explainers'],
  ['/opinion.html', 'Opinion'],
  ['/about.html', 'About']
];

function page({ title, description, canonical, current, body, jsonLd, ogType = 'website', adsense = true }) {
  const nav = NAV.map(([href, label]) => `<a${href === current ? ' aria-current="page"' : ''} href="${href}">${label}</a>`).join('');
  const ld = jsonLd ? `<script type="application/ld+json">${JSON.stringify(jsonLd).replace(/</g, '\\u003c')}</script>` : '';
  return `<!doctype html><html lang="en"><head><script src="/consent-default.js"></script><script async src="https://www.googletagmanager.com/gtag/js?id=G-7708VKPQSN"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}gtag('js',new Date());gtag('config','G-7708VKPQSN');</script>${adsense ? '<script async src="https://pagead2.googlesyndication.com/pagead/js?client=ca-pub-7773342225754932" crossorigin="anonymous"></script>' : ''}<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(title)}</title><meta name="description" content="${escapeHtml(description)}"><meta name="robots" content="index,follow"><link rel="canonical" href="${SITE}${canonical}"><link rel="alternate" type="application/rss+xml" href="/feed.xml" title="The Signal — Horn Updates"><meta property="og:type" content="${ogType}"><meta property="og:site_name" content="Horn Updates"><meta property="og:title" content="${escapeHtml(title)}"><meta property="og:description" content="${escapeHtml(description)}"><meta property="og:url" content="${SITE}${canonical}"><meta property="og:image" content="${SITE}/Horn1_logo.png"><meta name="twitter:card" content="summary_large_image"><link rel="stylesheet" href="/redesign.css">${ld}</head><body><header class="site-header"><div class="masthead"><a class="brand" href="/">Horn Updates<small>What is changing in the Horn of Africa, and why it matters.</small></a><nav class="nav">${nav}</nav></div></header><main class="container">${body}</main><footer class="footer"><div class="footer-inner"><span>© ${new Date().getUTCFullYear()} Horn Updates</span><nav><a href="/editorial-policy.html">Editorial policy</a><a href="/about.html">About</a><a href="/advertise.html">Advertise</a><a href="/contact.html">Contact</a><a href="/privacy.html">Privacy</a><a href="/terms.html">Terms</a><a href="/disclaimer.html">Disclaimer</a><a href="/feed.xml">RSS</a></nav></div></footer><script src="/cookie-consent.js"></script></body></html>
`;
}

// ── The Signal ─────────────────────────────────────────────────────────────────

const editionLabel = e => `No. ${e.number} · ${longDate(e.date)}`;

function renderItem(item, index) {
  const sources = item.sources.map(s => `<a href="${escapeHtml(s.url)}" rel="noopener noreferrer">${escapeHtml(s.name)}</a>${s.language && s.language !== 'English' ? ` (${escapeHtml(s.language)})` : ''}${s.kind === 'state' || s.kind === 'state-affiliated' ? ' <span class="source-kind">state media</span>' : ''}`).join(' · ');
  const background = item.background ? `<dt>Background</dt><dd><a href="${escapeHtml(item.background.url)}">${escapeHtml(item.background.title)} →</a></dd>` : '';
  return `<article class="signal-item" id="item-${index + 1}"><div class="signal-num">${pad(index + 1)}</div><div><div class="eyebrow">${escapeHtml(item.country)} · ${escapeHtml(item.topic)}</div><h2>${escapeHtml(item.headline)}</h2><p>${escapeHtml(item.what_happened)}</p><dl><dt>Why it matters</dt><dd>${escapeHtml(item.why_it_matters)}</dd><dt>What to watch</dt><dd>${escapeHtml(item.what_to_watch)}</dd>${background}</dl><p class="signal-sources">Source: ${sources}</p></div></article>`;
}

function renderEdition(edition, newer, older) {
  const nav = `<nav class="edition-nav">${older ? `<a href="${older.url}">← ${escapeHtml(editionLabel(older))}</a>` : '<span></span>'}<a href="/signal-brief.html">All editions</a>${newer ? `<a href="${newer.url}">${escapeHtml(editionLabel(newer))} →</a>` : '<span></span>'}</nav>`;
  const body = `<section class="page-hero"><div class="eyebrow">The Signal · ${escapeHtml(editionLabel(edition))}</div><h1>${escapeHtml(edition.title)}</h1><p>${escapeHtml(edition.intro)}</p></section><section class="section"><div class="signal-list">${edition.items.map(renderItem).join('')}</div><p class="corrections">Each item links its source. State media is labelled and used for official positions, not as independent confirmation. See our <a href="/editorial-policy.html">editorial policy</a> or <a href="/contact.html">send a correction</a>.</p>${nav}</section>`;
  return page({
    title: `${edition.title} | The Signal | Horn Updates`,
    description: edition.intro.slice(0, 155),
    canonical: edition.url,
    current: '/signal-brief.html',
    ogType: 'article',
    body,
    jsonLd: { '@context': 'https://schema.org', '@type': 'NewsArticle', headline: edition.title, datePublished: edition.date, dateModified: edition.modified || edition.date, author: { '@type': 'Organization', name: 'Horn Updates Editorial Desk' }, publisher: { '@type': 'Organization', name: 'Horn Updates', url: SITE }, mainEntityOfPage: `${SITE}${edition.url}` }
  });
}

function renderSignalIndex(editions) {
  const [latest, ...older] = editions;
  const intro = '<p>A weekly briefing on Ethiopia and the Horn of Africa: what happened, why it matters and what to watch, with every item linked to its source, including reporting in Amharic, Afaan Oromoo and Tigrinya.</p>';
  const current = latest
    ? `<section class="section"><div class="section-title"><h2>${escapeHtml(latest.title)}</h2><p>${escapeHtml(editionLabel(latest))}</p></div><p class="edition-intro">${escapeHtml(latest.intro)}</p><div class="signal-list">${latest.items.map(renderItem).join('')}</div><p><a class="button" href="${latest.url}">Permalink to this edition</a></p></section>`
    : '<section class="section"><div class="signal-box"><div><div class="eyebrow">First edition</div><h2>Coming soon.</h2></div><div><p>The first weekly edition of The Signal is in preparation. Until then, our explainers cover the background to the stories that matter.</p><p><a href="/explainers.html"><strong>Browse explainers →</strong></a></p></div></div></section>';
  const archive = older.length
    ? `<section class="section"><div class="section-title"><h2>Past editions</h2></div><ul class="edition-list">${older.map(e => `<li><a href="${e.url}">${escapeHtml(e.title)}</a><span>${escapeHtml(editionLabel(e))}</span></li>`).join('')}</ul></section>`
    : '';
  return page({
    title: 'The Signal — Weekly Ethiopia and Horn of Africa Briefing | Horn Updates',
    description: 'A weekly, sourced briefing on Ethiopia and the Horn of Africa: what happened, why it matters and what to watch next.',
    canonical: '/signal-brief.html',
    current: '/signal-brief.html',
    body: `<section class="page-hero"><div class="eyebrow">Weekly briefing</div><h1>The Signal</h1>${intro}</section>${current}${archive}`
  });
}

function renderHome(editions) {
  const latest = editions[0];
  const card = latest
    ? `<aside class="brief-card"><div class="eyebrow">The Signal · ${escapeHtml(editionLabel(latest))}</div><h2>${escapeHtml(latest.title)}</h2><p>${escapeHtml(latest.intro)}</p><a class="button" href="${latest.url}">Read this week’s Signal →</a></aside>`
    : '<aside class="brief-card"><div class="eyebrow">The Signal</div><h2>Weekly briefing</h2><p>What happened in Ethiopia and the Horn this week, why it matters and what to watch, with sources.</p><a class="button" href="/newsletter.html">Get the first edition →</a></aside>';
  const items = latest
    ? `<section class="section" id="latest"><div class="section-title"><h2>This week in the Horn</h2><p>From The Signal · ${escapeHtml(shortDate(latest.date))}</p></div><div class="story-grid">${latest.items.slice(0, HOME_ITEMS).map((item, i) => `<article class="story"><div class="eyebrow">${escapeHtml(item.country)} · ${escapeHtml(item.topic)}</div><h3><a href="${latest.url}#item-${i + 1}">${escapeHtml(item.headline)}</a></h3><p>${escapeHtml(item.why_it_matters)}</p></article>`).join('')}</div><p><a class="button" href="${latest.url}">Read the full edition →</a></p></section>`
    : '';
  const explainers = `<section class="section" id="explainers"><div class="section-title"><h2>Background that lasts</h2><p><a href="/explainers.html">All explainers →</a></p></div><div class="beat-grid">${EXPLAINERS.slice(0, 6).map((e, i) => `<article><div class="beat-num">${pad(i + 1)}</div><h3><a href="${e.url}">${escapeHtml(e.title)}</a></h3><p>${escapeHtml(e.blurb)}</p></article>`).join('')}</div></section>`;
  const body = `<section class="home-hero"><div><div class="eyebrow">Horn Updates · Ethiopia and the Horn of Africa</div><h1>What is changing in the Horn — and why it matters.</h1><p class="dek">Sourced analysis of Ethiopia, Eritrea, Somalia, Sudan, South Sudan and Djibouti. We read local-language reporting so you get the context, not just the headline.</p><div class="topic-row">${COUNTRIES.slice(0, 6).map(c => `<span class="tag">${c}</span>`).join('')}</div></div>${card}</section>${items}${explainers}<section class="section"><div class="opinion-band"><div><div class="eyebrow">Opinion &amp; analysis</div><h2>Arguments, clearly labelled.</h2></div><div><p>Long-form analysis and signed commentary on Ethiopian politics, the Red Sea and the region’s wars, kept separate from reporting.</p><a class="button" href="/opinion.html">Read opinion &amp; analysis →</a></div></div></section><section class="section"><div class="signal-box"><div><div class="eyebrow">Editorial standard</div><h2>Every claim has a source.</h2></div><div><p>Automation helps us find and draft stories; an editor checks every item against its source before it is published. Contested claims are attributed to the party making them, and state media is labelled.</p><p><a href="/editorial-policy.html"><strong>Read the editorial policy →</strong></a></p></div></div></section><section class="section newsletter"><div class="eyebrow">The Signal by email</div><h2>One briefing a week. No noise.</h2><p>What happened in the Horn, why it matters and what to watch next.</p><a class="button" href="/newsletter.html">Subscribe</a></section>`;
  return page({
    title: 'Horn Updates — Ethiopia and Horn of Africa News Analysis',
    description: 'Sourced weekly analysis of Ethiopia and the Horn of Africa: politics, conflict, economy and diplomacy across Ethiopia, Eritrea, Somalia, Sudan, South Sudan and Djibouti.',
    canonical: '/',
    current: '/',
    body,
    jsonLd: { '@context': 'https://schema.org', '@graph': [{ '@type': 'Organization', name: 'Horn Updates', url: `${SITE}/` }, { '@type': 'WebSite', name: 'Horn Updates', url: `${SITE}/`, description: 'Weekly sourced analysis of Ethiopia and the Horn of Africa.' }] }
  }).replace('<a class="brand" href="/">', '<a class="brand" href="/" aria-current="page">');
}

// ── Sitemap and RSS ────────────────────────────────────────────────────────────

const STATIC_PAGES = [
  ['/', 'daily', '1.0'], ['/signal-brief.html', 'weekly', '0.9'], ['/explainers.html', 'monthly', '0.8'], ['/opinion.html', 'weekly', '0.8'],
  ['/newsletter.html', 'monthly', '0.6'], ['/about.html', 'yearly', '0.6'], ['/editorial-policy.html', 'yearly', '0.6'], ['/advertise.html', 'yearly', '0.5'],
  ['/contact.html', 'yearly', '0.5'], ['/privacy.html', 'yearly', '0.4'], ['/terms.html', 'yearly', '0.4'], ['/disclaimer.html', 'yearly', '0.4']
];

async function indexableArticles() {
  const files = (await fs.readdir(ROOT)).filter(f => /^(explainer|opinion|author)-.+\.html$/.test(f)).sort();
  const out = [];
  for (const file of files) {
    const html = await fs.readFile(path.join(ROOT, file), 'utf8');
    if (/<meta name="robots" content="noindex/i.test(html)) continue;
    out.push([`/${file}`, 'monthly', file.startsWith('author') ? '0.5' : '0.7']);
  }
  return out;
}

async function buildSitemap(editions, builtOn) {
  const file = path.join(ROOT, 'sitemap.xml');
  const previous = await fs.readFile(file, 'utf8').catch(() => '');
  const known = new Map([...previous.matchAll(/<loc>([^<]+)<\/loc><lastmod>([^<]+)<\/lastmod>/g)].map(m => [m[1], m[2]]));
  const newest = editions[0]?.date;
  const entry = ([loc, freq, priority], lastmod) => `  <url><loc>${SITE}${loc}</loc><lastmod>${lastmod}</lastmod><changefreq>${freq}</changefreq><priority>${priority}</priority></url>`;
  const lastmodFor = loc => (['/', '/signal-brief.html'].includes(loc) && newest) ? newest : (known.get(`${SITE}${loc}`) || builtOn);
  const lines = [
    ...STATIC_PAGES.map(p => entry(p, lastmodFor(p[0]))),
    ...editions.map(e => entry([e.url, 'yearly', '0.8'], e.modified || e.date)),
    ...(await indexableArticles()).map(p => entry(p, lastmodFor(p[0])))
  ];
  await fs.writeFile(file, `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${lines.join('\n')}\n</urlset>\n`);
}

async function buildFeed(editions, builtAt) {
  const items = editions.slice(0, FEED_LIMIT).map(e => {
    const link = `${SITE}${e.url}`;
    return `<item><title>${escapeXml(e.title)}</title><link>${link}</link><guid>${link}</guid><pubDate>${at(e.date).toUTCString()}</pubDate><description>${escapeXml(e.intro)}</description></item>`;
  }).join('\n');
  await fs.writeFile(path.join(ROOT, 'feed.xml'), `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>The Signal — Horn Updates</title><link>${SITE}/signal-brief.html</link><description>A weekly sourced briefing on Ethiopia and the Horn of Africa.</description><language>en</language><lastBuildDate>${new Date(builtAt || Date.now()).toUTCString()}</lastBuildDate>
${items}
</channel></rss>
`);
}

// Regenerates every page and file derived from data/signal.json.
export async function buildSite({ touch = false } = {}) {
  const data = await loadSignal();
  if (touch) data.updated_at = new Date().toISOString().replace(/\.\d+Z$/, 'Z');
  await saveSignal(data);
  const editions = data.editions;
  await fs.mkdir(path.join(ROOT, 'signal'), { recursive: true });
  for (const [i, edition] of editions.entries()) {
    await fs.writeFile(path.join(ROOT, edition.url.replace(/^\//, '')), renderEdition(edition, editions[i - 1], editions[i + 1]));
  }
  await fs.writeFile(path.join(ROOT, 'signal-brief.html'), renderSignalIndex(editions));
  await fs.writeFile(path.join(ROOT, 'index.html'), renderHome(editions));
  await buildSitemap(editions, (data.updated_at || new Date().toISOString()).slice(0, 10));
  await buildFeed(editions, data.updated_at);
  return data;
}
