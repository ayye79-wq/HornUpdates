// Regenerates ai/index.html cards, sitemap.xml and feed.xml from data/ai-news.json.
// Run after any manual edit to data/ai-news.json:  node scripts/build-ai-site.mjs
import { buildSite } from './lib/ai-site.mjs';

const data = await buildSite({ touch: process.argv.includes('--touch') });
console.log(`Rebuilt archive, sitemap and RSS for ${data.stories.length} stories.`);
