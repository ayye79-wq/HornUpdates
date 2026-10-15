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

### From candidate to published story

1. **Collect.** `collect-ai-news.yml` runs twice a day and opens or refreshes the
   *Refresh AI news candidate inbox* PR. Its body is a checklist of candidates.
2. **Choose.** Tick the candidates worth covering and merge the inbox PR.
3. **Draft.** `publish-ai-stories.yml` runs on that merge. For each ticked
   candidate it fetches the source and has Claude (`claude-opus-5-5`) draft a
   structured story. It then writes the page under `/ai/`, adds the entry to
   `data/ai-news.json`, regenerates the archive cards, sitemap and RSS, validates
   everything and opens a *Publish* PR. Claude may suggest skipping a candidate;
   the PR body lists every skip and failure with its reason.
4. **Review and publish.** Check each draft against its source, edit as needed and
   merge the Publish PR. Netlify deploys on merge.

To draft from a link the collector missed, run *Draft AI stories for publication*
from the Actions tab with a `source_url`.

`data/ai-news.json` is the single source of truth for the archive cards, sitemap and
RSS. After editing it by hand, regenerate the derived files:

```bash
node scripts/build-ai-site.mjs
```

Run the publication check locally with:

```bash
node scripts/validate-ai-publication.mjs
```

GitHub Actions runs the same validation for AI-publication changes.

**Repository settings this needs:** Actions secret `ANTHROPIC_API_KEY`, and
*Settings → Actions → General → Allow GitHub Actions to create and approve pull
requests* enabled. Without that setting the collector cannot open its PR.

## Main files

- `index.html` — publication homepage
- `ai/index.html` — AI coverage archive
- `data/ai-news.json` — verified public feed
- `data/ai-inbox.json` — automated discovery inbox; not public editorial approval
- `ai-sources.json` — source registry
- `scripts/collect-ai-news.mjs` — candidate discovery
- `scripts/inbox-pr-body.mjs` — inbox PR checklist
- `scripts/draft-ai-story.mjs` — Claude drafting for ticked candidates
- `scripts/build-ai-site.mjs` / `scripts/lib/ai-site.mjs` — article rendering and archive/sitemap/RSS regeneration
- `scripts/validate-ai-publication.mjs` — publication integrity checks
- `editorial-policy.html` — sourcing and AI-assistance standards

Legacy Horn of Africa pages remain available as an archive so old links are not broken, but they are not promoted as the publication's current editorial focus.
# Email approval requests

The AI candidate collector opens or refreshes a review pull request and can send
a branded HornUpdates approval email through Resend. Configure these repository
settings before expecting mail:

- Actions secret `RESEND_API_KEY`
- Actions variable `APPROVAL_EMAIL_TO` (defaults to `Ayye79@gmail.com`)
- Actions variable `APPROVAL_EMAIL_FROM` (defaults to
  `HornUpdates Approvals <approvals@hornupdates.com>`)

The sender domain must be verified in Resend. Merging the candidate-inbox PR only
drafts the ticked stories into a separate Publish PR; nothing goes live until that
PR is reviewed and merged.
