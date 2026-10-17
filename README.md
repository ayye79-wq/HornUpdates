# Horn Updates

**What is changing in the Horn of Africa, and why it matters.**

Horn Updates is an independent static publication covering Ethiopia first, then
Eritrea, Somalia, Sudan, South Sudan, Djibouti, and Kenya where events cross borders.

- **The Signal** (`/signal-brief.html`, editions under `/signal/`): a weekly sourced
  briefing. Each item covers what happened, why it matters and what to watch, and
  links its source, including Amharic, Afaan Oromoo and Tigrinya reporting.
- **Explainers** (`explainer-*.html`): lasting background on the region's big questions.
- **Opinion and analysis** (`opinion-*.html`): signed, clearly labelled commentary.

## Publishing The Signal

1. **Collect.** `collect-news.yml` runs twice a day. It gathers candidates from
   `sources.json` into `data/inbox.json` and keeps a *Signal inbox* PR open whose
   body is a checklist. Ethiopia-focused outlets are listed first, with one item per
   outlet in turn, and state media is flagged.
2. **Choose.** Tick stories through the week; ticks survive each refresh. For
   contested events, tick more than one side's coverage. Merge when you're ready to
   assemble the edition.
3. **Draft.** `publish-signal.yml` runs on that merge. For each ticked candidate it
   fetches the source and has Claude (`claude-opus-5-5`) draft a structured item:
   facts attributed, analysis kept separate, local-language sources translated.
   Claude then writes the edition title and intro and orders the items. The
   workflow saves the edition to `data/signal.json`, regenerates the site, validates
   it and opens a *Publish* PR. Every skip or failure is listed with its reason.
4. **Review and publish.** Check each item against its source. To edit, change
   `data/signal.json` and run `node scripts/build-site.mjs`; don't edit the generated
   HTML. Merge the Publish PR and Netlify deploys.

To draft from a link the collector missed, run *Draft The Signal for publication*
from the Actions tab with a `source_url`.

`data/signal.json` is the single source of truth for `index.html`,
`signal-brief.html`, `signal/*.html`, `sitemap.xml` and `feed.xml`. After any manual
edit:

```bash
node scripts/build-site.mjs
node scripts/validate-publication.mjs
```

**Repository settings this needs:** Actions secret `ANTHROPIC_API_KEY`, and
*Settings → Actions → General → Allow GitHub Actions to create and approve pull
requests* enabled. Without that setting the collector cannot open its PR.

## Sources

`sources.json` lists RSS or HTML pages with a `kind` (independent, international,
state, state-affiliated, humanitarian). English regional feeds are filtered by
`horn_keywords`; Ethiopia-specific and local-language feeds take every item. Addis
Standard, AP, Reuters, Sudan Tribune, The EastAfrican and Crisis Group currently
block automated fetches, so they are not listed. Tips from them can still go in
by hand through the `source_url` run.

## Main files

- `data/signal.json`: published Signal editions
- `data/inbox.json`: automated discovery inbox; not editorial approval
- `sources.json`: source registry
- `scripts/collect-news.mjs`: candidate discovery
- `scripts/inbox-pr-body.mjs`: inbox PR checklist
- `scripts/draft-signal.mjs`: Claude drafting of an edition from ticked candidates
- `scripts/build-site.mjs` / `scripts/lib/site.mjs`: page rendering, sitemap and RSS
- `scripts/validate-publication.mjs`: publication integrity checks
- `editorial-policy.html`: sourcing, attribution, state-media and AI-assistance standards

The September–October 2026 AI coverage under `/ai/` stays reachable for old links
but is `noindex` and no longer linked; `/ai/` redirects to The Signal.

## Email approval requests

When a fresh Signal inbox PR opens, the collector can send an email through
Resend. Configure:

- Actions secret `RESEND_API_KEY`
- Actions variable `APPROVAL_EMAIL_TO` (defaults to `Ayye79@gmail.com`)
- Actions variable `APPROVAL_EMAIL_FROM` (defaults to
  `HornUpdates Approvals <approvals@hornupdates.com>`)

The sender domain must be verified in Resend.
