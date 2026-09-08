# Horn Updates

## Project overview

Horn Updates is an independent static publication focused on context, explainers,
analysis and clearly labelled opinion about the Horn of Africa. The public site is
plain HTML, CSS and JavaScript; there is no persistent application server.

## Editorial safeguards

- Opinion and analysis require contributor attribution and human editorial review.
- The former automated opinion generator is retired; `generate_opinion.py` is a
  non-writing compatibility stub.
- Repetitive legacy daily opinion output was removed in September 2026.
- Automated feed and opinion publishing are retired. The Signal Brief workflow is
  a manual, non-writing editorial check.
- AI-assisted research or drafting must be reviewed under `editorial-policy.html`.

## Key files

- `index.html` — publication homepage
- `opinion.html` — selected opinion and analysis
- `explainers.html` — background explainers
- `signal-brief.html` — editor-reviewed regional snapshot
- `articles.json` — archived reporting-feed data, not used to publish the homepage
- `scripts/prepare_adsense_review.py` — one-time, safely repeatable legacy cleanup
- `privacy.html`, `terms.html`, `editorial-policy.html` — reader and publishing policies

## Local preview

Run `python3 -m http.server 5000 --bind 0.0.0.0`, then open
`http://localhost:5000/`.

## Deployment

The repository deploys as a static site with the repository root as the publish
directory. Review changes on a branch, validate links and metadata, then merge to
`main`. Content is published only through reviewed repository changes.

## GitHub credentials

The stored fine-grained token needs repository Contents and Workflows write access.
The weekly token-expiry check creates an issue when renewal is approaching. Rotate
the secret in the hosting workspace, then test a non-destructive branch push.

---
title: HornUpdates
emoji: 🐢
colorFrom: pink
colorTo: green
sdk: static
sdk_version: 6.0.1
app_file: index.html
pinned: false
---
