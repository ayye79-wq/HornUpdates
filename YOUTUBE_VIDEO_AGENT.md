# HornUpdates AI YouTube agent

This workflow converts the newest unpublished **verified** story in
`data/ai-news.json` into a vertical English YouTube Short and publishes it to
the HornUpdates AI channel.

It creates a five-part source-backed script, English neural narration, branded
1080×1920 slides, and an H.264/AAC MP4. The upload includes both the complete
HornUpdates article URL and primary source URL. Synthetic narration is disclosed
in the description and through YouTube's `containsSyntheticMedia` field. The
state file prevents duplicate videos.

The scheduled workflow runs daily at 17:12 UTC and publishes publicly. A manual
workflow run can instead use `private` or `unlisted` visibility for testing.

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
