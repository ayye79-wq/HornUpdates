# Future Astro migration plan

Horn Updates should migrate only after the stabilized static site has a reliable content inventory and regression suite. Existing public URLs are a hard compatibility boundary.

## Phase 1 — inventory and contracts

- Record every public HTML URL, redirect, canonical URL, author byline and content type.
- Define a content schema for analysis, explainer, opinion, signal and static pages.
- Require title, dek, author, published/updated dates, content label, sources, related reading, corrections note, canonical, social metadata and Article JSON-LD.
- Add HTML, internal-link, sitemap, structured-data and snapshot checks to CI.

## Phase 2 — shared presentation

- Convert redesign.css, the masthead, navigation, footer and ARTICLE_TEMPLATE.html into Astro layouts/components.
- Keep analytics G-7708VKPQSN, AdSense publisher ca-pub-7773342225754932, consent behavior, RSS and editorial disclosures intact.
- Import a representative page from each content type and compare rendered output before expanding.

## Phase 3 — content migration

- Create validated content collections and import pages in small batches.
- Preserve filenames through explicit Astro routes or generated pages; never rely on a changed slug convention.
- Retain Netlify redirects, headers, configuration, sitemap and feeds, updating generators only after parity tests pass.
- Preserve alias author URLs for author-khalid-kayo and author-yared-kumbi while using canonical identities.

## Phase 4 — automation and cutover

- Separate ingestion/tagging automation from publish authority. AI may support discovery, context and metadata but may not publish attributed opinion.
- Build previews for editorial review; only reviewed content enters production collections.
- Run a full URL/link comparison against the static build, deploy a Netlify preview, and cut over only after zero unexpected URL changes.

## Rollback

Keep the final static release tagged and deployable. If redirects, metadata, feeds or article rendering regress, restore the static artifact while correcting the Astro build.
