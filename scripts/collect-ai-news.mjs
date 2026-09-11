import fs from 'node:fs/promises';

const sources = JSON.parse(await fs.readFile(new URL('../ai-sources.json', import.meta.url), 'utf8')).sources;
const keywords = ['ai','artificial-intelligence','artificial intelligence','gpt','claude','gemini','model','agent','machine-learning','deepmind','llm'];

const strip = s => s.replace(/&amp;/g, '&').replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
const absolutize = (href, base) => { try { return new URL(href, base).href; } catch { return null; } };

const results = [];
for (const source of sources.filter(s => s.priority <= 2)) {
  try {
    const res = await fetch(source.url, { headers: { 'user-agent': 'HornUpdates/1.0 (+https://hornupdates.com)' }, redirect: 'follow' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const html = await res.text();
    const links = [...html.matchAll(/<a\b[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi)];
    const seen = new Set();
    for (const [, href, rawText] of links) {
      const title = strip(rawText);
      if (title.length < 18 || title.length > 180) continue;
      const url = absolutize(href, source.url);
      if (!url || seen.has(url)) continue;
      const haystack = `${title} ${url}`.toLowerCase();
      if (!keywords.some(k => haystack.includes(k))) continue;
      seen.add(url);
      results.push({ source: source.name, source_type: source.type, title, url, discovered_at: new Date().toISOString(), status: 'candidate' });
      if (seen.size >= 12) break;
    }
  } catch (error) {
    results.push({ source: source.name, error: String(error.message || error), discovered_at: new Date().toISOString(), status: 'source_error' });
  }
}

const existingPath = new URL('../data/ai-inbox.json', import.meta.url);
let existing = { candidates: [] };
try { existing = JSON.parse(await fs.readFile(existingPath, 'utf8')); } catch {}

const byUrl = new Map();
for (const item of [...results, ...(existing.candidates || [])]) {
  if (item.url && !byUrl.has(item.url)) byUrl.set(item.url, item);
}

const output = {
  generated_at: new Date().toISOString(),
  note: 'Automated discovery inbox only. Candidates are not published until verified and promoted into data/ai-news.json.',
  candidates: [...byUrl.values()].slice(0, 120),
  source_errors: results.filter(x => x.status === 'source_error')
};

await fs.mkdir(new URL('../data/', import.meta.url), { recursive: true });
await fs.writeFile(existingPath, JSON.stringify(output, null, 2) + '\n');
console.log(`Collected ${results.filter(x => x.status === 'candidate').length} candidates from ${sources.filter(s => s.priority <= 2).length} priority sources.`);
