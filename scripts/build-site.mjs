// Regenerates the homepage, The Signal pages, sitemap.xml and feed.xml from data/signal.json.
// Run after any manual edit to data/signal.json:  node scripts/build-site.mjs
import { buildSite } from './lib/site.mjs';

const data = await buildSite({ touch: process.argv.includes('--touch') });
console.log(`Rebuilt site for ${data.editions.length} Signal edition(s).`);
