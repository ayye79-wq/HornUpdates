# HornUpdates AI YouTube agent

This workflow converts the newest unpublished **verified** story in
`data/ai-news.json` into a vertical English YouTube Short and publishes it to
the HornUpdates AI channel.

It creates a five-part source-backed script, English neural narration, branded
1080×1920 slides, and an H.264/AAC MP4. The upload includes both the complete
HornUpdates article URL and primary source URL. Synthetic narration is disclosed
in the description and through YouTube's `containsSyntheticMedia` field. The
state file prevents duplicate videos.

The scheduled workflow runs daily at 17:12 UTC, but public uploads stay blocked
until the repository variable `YOUTUBE_PUBLIC_PUBLISHING_ENABLED` is set to
`true`. Manual runs default to `unlisted`; test runs leave `record_state` off so
the selected story remains eligible for the later public launch.

## Required GitHub Actions secrets

- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

Create an OAuth client in Google Cloud, enable YouTube Data API v3, authorize the
HornUpdates channel with the `youtube.upload` scope, and add the resulting values
as repository Actions secrets. Never commit credentials or token files.

After downloading the OAuth desktop-client JSON, run the included one-time helper:

```bash
python scripts/youtube_oauth_setup.py client_secret_....json
```

## Safe local test

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-video.txt
python scripts/youtube_video_agent.py --dry-run
```

The MP4 is written under `build/youtube/`. A dry run never uploads and does not
change publishing state.

## Safe first GitHub Actions test

1. Add the three repository Actions secrets listed above.
2. Merge this pull request into the default branch.
3. Open **Actions → Publish HornUpdates AI Short → Run workflow**.
4. Choose `unlisted` and leave **record_state** off.
5. Run the workflow, review its uploaded artifact and the unlisted YouTube video,
   and confirm narration, facts, links, cropping, and channel ownership.
6. Only after approval, create the repository Actions variable
   `YOUTUBE_PUBLIC_PUBLISHING_ENABLED=true`. Scheduled runs will then upload
   publicly and record their story IDs. Public manual runs are blocked by the
   same variable.

If a test must permanently consume a story, enable **record_state** for that
manual run. Otherwise keep it off to avoid preventing the public version.
