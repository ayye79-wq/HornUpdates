// Integrity checks for The Signal and the files generated from data/signal.json.
import fs from 'node:fs/promises';
import path from 'node:path';
import { COUNTRIES, TOPICS } from './lib/site.mjs';

const root = process.cwd();
const read = file => fs.readFile(path.join(root, file), 'utf8');
const fail = message => { console.error(`ERROR: ${message}`); process.exitCode = 1; };

const data = JSON.parse(await read('data/signal.json'));
const sitemap = await read('sitemap.xml');
const feed = await read('feed.xml');
const home = await read('index.html');
const signalIndex = await read('signal-brief.html');
const editorial = await read('editorial-policy.html');

const ids = new Set();
for (const edition of data.editions || []) {
  for (const key of ['id', 'number', 'date', 'title', 'intro', 'url']) if (!edition[key]) fail(`edition ${edition.id || '?'} missing ${key}`);
  if (ids.has(edition.id)) fail(`duplicate edition id ${edition.id}`);
  ids.add(edition.id);
  if (!edition.items?.length) fail(`edition ${edition.id} has no items`);
  for (const [i, item] of (edition.items || []).entries()) {
    const where = `edition ${edition.id} item ${i + 1}`;
    for (const key of ['headline', 'country', 'topic', 'what_happened', 'why_it_matters', 'what_to_watch']) if (!item[key]) fail(`${where} missing ${key}`);
    if (!COUNTRIES.includes(item.country)) fail(`${where} has unknown country ${item.country}`);
    if (!TOPICS.includes(item.topic)) fail(`${where} has unknown topic ${item.topic}`);
    if (!item.sources?.length || item.sources.some(s => !/^https?:\/\//.test(s.url || ''))) fail(`${where} needs at least one source URL`);
    if (item.background) { try { await fs.access(path.join(root, item.background.url.replace(/^\//, ''))); } catch { fail(`${where} links missing background ${item.background.url}`); } }
  }
  try { await fs.access(path.join(root, edition.url.replace(/^\//, ''))); } catch { fail(`missing edition page ${edition.url}`); }
  if (!sitemap.includes(`https://hornupdates.com${edition.url}`)) fail(`sitemap missing ${edition.url}`);
  if (!feed.includes(`https://hornupdates.com${edition.url}`)) fail(`RSS missing ${edition.url}`);
}

const latest = [...(data.editions || [])].sort((a, b) => b.date.localeCompare(a.date))[0];
if (latest && !home.includes(latest.url)) fail('homepage does not link the latest edition');
if (latest && !signalIndex.includes(latest.url)) fail('signal-brief.html does not link the latest edition');
for (const [name, html] of [['index', home], ['signal-brief', signalIndex]]) {
  if (!html.includes('What is changing in the Horn of Africa, and why it matters.')) fail(`${name} missing brand line`);
}
if (/AI news\. Without the noise\./.test(home)) fail('homepage still carries the retired AI brand');
if (!editorial.includes('state media')) fail('editorial policy missing state-media standard');

if (!process.exitCode) console.log(`Publication checks passed for ${data.editions?.length || 0} Signal edition(s).`);
