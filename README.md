# Horn Updates

**AI news. Without the noise.**

Horn Updates is an independent static AI news publication covering:

- Models & research
- AI agents
- Tools & products
- AI & cybersecurity
- Business & jobs
- Policy
- Africa & AI

## Publishing model

Automated jobs may discover candidate stories from approved sources, but candidates are not automatically published. Public stories are promoted into `data/ai-news.json` only after source verification and editorial review.

Each promoted story should have:

- a dedicated page under `/ai/`
- an identifiable primary or trusted source
- a clear summary and `why_it_matters` field
- a sitemap entry
- an RSS entry
- structured metadata where appropriate

Run the publication check locally with:

```bash
node scripts/validate-ai-publication.mjs
```

GitHub Actions runs the same validation for AI-publication changes.

## Main files

- `index.html` — publication homepage
- `ai/index.html` — AI coverage archive
- `data/ai-news.json` — verified public feed
- `data/ai-inbox.json` — automated discovery inbox; not public editorial approval
- `ai-sources.json` — source registry
- `scripts/collect-ai-news.mjs` — candidate discovery
- `scripts/validate-ai-publication.mjs` — publication integrity checks
- `editorial-policy.html` — sourcing and AI-assistance standards

Legacy Horn of Africa pages remain available as an archive so old links are not broken, but they are not promoted as the publication's current editorial focus.
