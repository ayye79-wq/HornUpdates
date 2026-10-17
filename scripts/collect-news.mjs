// Discovers candidate Horn of Africa stories from sources.json into data/inbox.json.
// Discovery only: nothing here is published. An editor ticks candidates in the inbox PR.
import fs from 'node:fs/promises';
import { candidateId, loadSignal } from './lib/site.mjs';

const config = JSON.parse(await fs.readFile(new URL('../sources.json', import.meta.url), 'utf8'));
const keywords = config.horn_keywords;
const PER_SOURCE = 10;
const MAX_INBOX = 150;

const decode = s => s.replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, '$1').replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(Number(n))).replace(/&amp;/g, '&').replace(/&#x27;|&#39;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
const strip = s => decode(s).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
const absolutize = (href, base) => { try { return new URL(decode(href), base).href; } catch { return null; } };
const isHorn = text => { const t = text.toLowerCase(); return keywords.some(k => t.includes(k)); };

function rssItems(xml, base) {
  return [...xml.matchAll(/<item\b[\s\S]*?<\/item>/gi)].map(([item]) => ({
    title: strip((item.match(/<title[^>]*>([\s\S]*?)<\/title>/i) || [])[1] || ''),
    url: absolutize(strip((item.match(/<link[^>]*>([\s\S]*?)<\/link>/i) || [])[1] || ''), base),
    summary: strip((item.match(/<description[^>]*>([\s\S]*?)<\/description>/i) || [])[1] || '').slice(0, 300),
    published: (() => { const d = new Date(strip((item.match(/<pubDate[^>]*>([\s\S]*?)<\/pubDate>/i) || [])[1] || '')); return isNaN(d) ? '' : d.toISOString().slice(0, 10); })()
  }));
}

function htmlLinks(html, base, pattern) {
  return [...html.matchAll(/<a\b[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi)]
    .map(([, href, text]) => ({ title: strip(text), url: absolutize(href, base), summary: '', published: '' }))
    .filter(l => l.url && (!pattern || new RegExp(pattern).test(l.url)));
}

const results = [];
for (const source of config.sources) {
  try {
    const get = () => fetch(source.url, { headers: { 'user-agent': 'HornUpdates/1.0 (+https://hornupdates.com)', accept: 'application/rss+xml, application/xml;q=0.9, text/html;q=0.8, */*;q=0.5' }, redirect: 'follow' });
    let res = await get();
    // Some feeds (ReliefWeb) intermittently answer 406 or 5xx; one retry clears most of them.
    if (!res.ok && (res.status === 406 || res.status === 429 || res.status >= 500)) res = await get();
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const body = await res.text();
    const entries = source.type === 'rss' ? rssItems(body, source.url) : htmlLinks(body, source.url, source.link_pattern);
    const seen = new Set();
    for (const entry of entries) {
      if (!entry.url || seen.has(entry.url)) continue;
      if (entry.title.length < 12 || entry.title.length > 220) continue;
      // Keyword filtering only works for English; local-language and single-country feeds take everything.
      const keep = source.filter === 'all' || source.link_pattern || isHorn(`${entry.title} ${entry.summary} ${entry.url}`);
      if (!keep) continue;
      seen.add(entry.url);
      results.push({
        id: candidateId(source.name, entry.url),
        source: source.name,
        source_kind: source.kind,
        language: source.language || 'English',
        title: entry.title,
        url: entry.url,
        summary: entry.summary,
        source_published: entry.published,
        discovered_at: new Date().toISOString(),
        status: 'candidate'
      });
      if (seen.size >= PER_SOURCE) break;
    }
  } catch (error) {
    results.push({ source: source.name, error: String(error.message || error), discovered_at: new Date().toISOString(), status: 'source_error' });
  }
}

const inboxPath = new URL('../data/inbox.json', import.meta.url);
let existing = { candidates: [] };
try { existing = JSON.parse(await fs.readFile(inboxPath, 'utf8')); } catch {}

const signal = await loadSignal();
const published = new Set(signal.editions.flatMap(e => e.items.flatMap(i => i.sources.map(s => s.url))));

// Existing entries win so a re-discovered link keeps its original id and discovery time.
const byUrl = new Map();
for (const item of [...(existing.candidates || []), ...results]) {
  if (!item.url || byUrl.has(item.url) || published.has(item.url)) continue;
  byUrl.set(item.url, item);
}

const output = {
  generated_at: new Date().toISOString(),
  note: 'Automated discovery inbox only. Candidates are not published until an editor ticks them and reviews the drafted Signal edition.',
  candidates: [...byUrl.values()].sort((a, b) => b.discovered_at.localeCompare(a.discovered_at)).slice(0, MAX_INBOX),
  source_errors: results.filter(x => x.status === 'source_error')
};

await fs.mkdir(new URL('../data/', import.meta.url), { recursive: true });
await fs.writeFile(inboxPath, JSON.stringify(output, null, 2) + '\n');
console.log(`Collected ${results.filter(x => x.status === 'candidate').length} candidates from ${config.sources.length} sources; ${output.source_errors.length} source errors.`);
