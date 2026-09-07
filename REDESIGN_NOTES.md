# Redesign notes

## Publication and homepage

- Repositioned the masthead around: “What is changing in the Horn of Africa, and why it matters.”
- Replaced the dense dashboard-like homepage with a restrained navy, serif-led editorial system in redesign.css.
- Reordered the homepage into lead analysis, five-item Signal, deep analysis, explainers, clearly labeled personal opinion and newsletter.
- Removed “Today,” “Live,” “Breaking,” animated urgency and empty/live metric presentation. The Signal identifies itself as a curated snapshot.
- Preserved analytics, AdSense, RSS, editorial-policy, contact, privacy and newsletter links.

## Editorial integrity and automation

- Removed the scheduled generate_opinion.yml workflow.
- Removed every opinion-generation, failure-alert and opinion-file commit step from the twice-daily article workflow.
- Kept feed ingestion and AI-assisted editorial metadata support, author-page syncing, redirects and site-index updates.
- Added an explicit distinction between institutional analysis and contributor opinion.
- Added ARTICLE_TEMPLATE.html as the standard contract for title, dek, byline, dates, label, body, sources, related reading, corrections, JSON-LD and social metadata.

## Tsimdo article and contributor

- Added opinion-tsimdo.html with the supplied headline, author, content type and publication date.
- Added author-aba-fantoli.html and linked the article from the contributor page, homepage and opinion index.
- The supplied transformation brief did not include the prepared manuscript. The page therefore carries a transparent manuscript-pending notice; no AI-written text is attributed to Aba Fantoli. Replace that notice only with the reviewed contributor manuscript.

## Authors and URLs

- Confirmed author-khalid-kayo.html is an HTML redirect to the canonical author-kalid-kayo.html.
- Confirmed author-yared-kumbi.html is an HTML redirect to the canonical author-yared-kunbi.html.
- Corrected Netlify extensionless aliases so both duplicate spellings resolve to their canonical author pages without deleting public URLs.
- Added Aba Fantoli to the author-page synchronization mapping.

## Repository and indexing

- Removed the accidental file “how -1 --name-only”; it contained only a pasted commit-status line.
- Added the new article and author URLs to the sitemap.
- Preserved Netlify configuration and all existing article URLs.
- Documented a staged, URL-safe Astro path in MIGRATION_PLAN.md; no framework migration was attempted.
