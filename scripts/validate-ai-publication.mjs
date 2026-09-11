import fs from 'node:fs/promises';
import path from 'node:path';

const root = process.cwd();
const read = file => fs.readFile(path.join(root, file), 'utf8');
const fail = message => { console.error(`ERROR: ${message}`); process.exitCode = 1; };

const data = JSON.parse(await read('data/ai-news.json'));
const sitemap = await read('sitemap.xml');
const feed = await read('feed.xml');
const index = await read('index.html');
const about = await read('about.html');
const editorial = await read('editorial-policy.html');

if (!Array.isArray(data.stories) || data.stories.length < 3) fail('Need at least three verified stories.');
const seenIds = new Set();
const seenUrls = new Set();
for (const story of data.stories || []) {
  for (const key of ['id','title','summary','category','source','published','internal_url','source_url','why_it_matters','status']) {
    if (!story[key]) fail(`${story.id || 'story'} missing ${key}`);
  }
  if (story.status !== 'verified') fail(`${story.id} is public but not verified`);
  if (seenIds.has(story.id)) fail(`Duplicate story id: ${story.id}`);
  if (seenUrls.has(story.internal_url)) fail(`Duplicate internal URL: ${story.internal_url}`);
  seenIds.add(story.id); seenUrls.add(story.internal_url);

  const relative = story.internal_url.replace(/^\//, '');
  try { await fs.access(path.join(root, relative)); } catch { fail(`Missing article file: ${relative}`); }
  if (!sitemap.includes(`https://hornupdates.com${story.internal_url}`)) fail(`Sitemap missing ${story.internal_url}`);
  if (!feed.includes(`https://hornupdates.com${story.internal_url}`)) fail(`RSS missing ${story.internal_url}`);
}

for (const [name, html] of [['index', index], ['about', about], ['editorial-policy', editorial]]) {
  if (!html.includes('AI news. Without the noise.')) fail(`${name} missing current brand line`);
}
if (!index.includes('/ai/')) fail('Homepage is missing AI archive link');
if (!editorial.includes('No synthetic volume')) fail('Editorial policy missing synthetic-volume standard');

if (!process.exitCode) console.log(`AI publication checks passed for ${data.stories.length} verified stories.`);
