#!/usr/bin/env python3
"""Render and publish one verified HornUpdates AI story as a YouTube Short."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import edge_tts
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
NEWS_FILE = ROOT / "data" / "ai-news.json"
STATE_FILE = ROOT / "data" / "youtube-video-state.json"
OUTPUT_DIR = ROOT / "build" / "youtube"
WIDTH, HEIGHT, FPS = 1080, 1920, 30


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def require_binary(name: str) -> None:
    if not shutil.which(name):
        raise RuntimeError(f"Required binary not found: {name}")


def media_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        check=True, capture_output=True, text=True,
    )
    return max(1.0, float(result.stdout.strip()))


def load_json(path: Path, default: dict | None = None) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if default is not None:
            return default
        raise


def choose_story() -> dict | None:
    feed = load_json(NEWS_FILE)
    state = load_json(STATE_FILE, {"published_story_ids": []})
    used = set(state.get("published_story_ids", []))
    stories = [s for s in feed.get("stories", []) if s.get("status") == "verified" and s.get("id") not in used]
    stories.sort(key=lambda s: (s.get("published", ""), s.get("id", "")), reverse=True)
    return stories[0] if stories else None


def short_title(title: str) -> str:
    title = title.strip()
    return title if len(title) <= 88 else title[:85].rsplit(" ", 1)[0] + "…"


def sections(story: dict) -> list[tuple[str, str]]:
    return [
        ("AI NEWS", f"Here is today's AI update. {story['title'].rstrip('.')}."),
        ("WHAT HAPPENED", story["summary"]),
        ("WHY IT MATTERS", story["why_it_matters"]),
        ("THE SIGNAL", f"This development comes from {story['source']}. Watch how quickly it moves from announcement to real-world use."),
        ("READ THE FULL STORY", "For the full source-backed explanation, visit HornUpdates dot com. AI news, without the noise."),
    ]


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    style = "Bold" if bold else "Regular"
    candidates = [
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans-{style}.ttf",
        f"/usr/share/fonts/truetype/liberation2/LiberationSans-{style}.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def wrap(draw: ImageDraw.ImageDraw, value: str, face: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in value.split():
        trial = f"{current} {word}".strip()
        if draw.textbbox((0, 0), trial, font=face)[2] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def make_slide(path: Path, label: str, body: str, story: dict, index: int, total: int) -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#07111f")
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        blue = int(31 + 28 * (1 - y / HEIGHT))
        draw.line((0, y, WIDTH, y), fill=(7, 17, min(78, blue)))
    draw.ellipse((610, -180, 1240, 450), fill="#103a62")
    draw.rectangle((74, 102, 92, 310), fill="#42d3ff")

    brand = get_font(54, True)
    kicker = get_font(36, True)
    body_font = get_font(70 if index == 0 else 58, True)
    meta = get_font(32)
    small = get_font(28)
    draw.text((118, 104), "HORNUPDATES AI", font=brand, fill="#ffffff")
    draw.text((118, 180), "AI news. Without the noise.", font=small, fill="#a9bfd4")
    draw.text((80, 430), label, font=kicker, fill="#42d3ff")

    y = 530
    for line in wrap(draw, body, body_font, 920)[:9]:
        draw.text((80, y), line, font=body_font, fill="#ffffff")
        y += int(body_font.size * 1.24)

    draw.line((80, 1685, 1000, 1685), fill="#29465f", width=3)
    draw.text((80, 1725), f"SOURCE  {story['source'].upper()}", font=meta, fill="#a9bfd4")
    draw.text((80, 1780), "hornupdates.com", font=meta, fill="#ffffff")
    draw.text((930, 1780), f"{index + 1}/{total}", font=small, fill="#42d3ff", anchor="ra")
    progress = int(920 * ((index + 1) / total))
    draw.rounded_rectangle((80, 1845, 1000, 1861), radius=8, fill="#29465f")
    draw.rounded_rectangle((80, 1845, 80 + progress, 1861), radius=8, fill="#42d3ff")
    image.save(path, quality=95)


async def speak(text: str, output: Path) -> None:
    if os.environ.get("HORNUDATES_TEST_TONE") == "1":
        seconds = max(2.5, len(text.split()) / 2.7)
        run(
            "ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
            "sine=frequency=220:sample_rate=44100", "-filter:a", "volume=0.03",
            "-t", f"{seconds:.3f}", str(output),
        )
        return
    voice = os.environ.get("HORNUDATES_VOICE", "en-US-AvaNeural")
    await edge_tts.Communicate(text, voice=voice, rate="+4%", pitch="-2Hz").save(str(output))


def render(story: dict) -> Path:
    require_binary("ffmpeg")
    require_binary("ffprobe")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    work = OUTPUT_DIR / story["id"]
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    script = sections(story)
    clips: list[Path] = []
    for index, (label, spoken) in enumerate(script):
        image = work / f"slide-{index}.png"
        audio = work / f"voice-{index}.mp3"
        clip = work / f"clip-{index}.mp4"
        make_slide(image, label, spoken, story, index, len(script))
        asyncio.run(speak(spoken, audio))
        seconds = media_duration(audio) + 0.35
        frames = max(FPS, round(seconds * FPS))
        fade_out = max(0.0, seconds - 0.30)
        run(
            "ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(image), "-i", str(audio),
            "-vf", f"zoompan=z='min(zoom+0.00018,1.035)':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS},format=yuv420p",
            "-af", f"afade=t=in:st=0:d=0.12,afade=t=out:st={fade_out:.3f}:d=0.25",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k",
            "-t", f"{seconds:.3f}", "-shortest", str(clip),
        )
        clips.append(clip)

    concat_file = work / "clips.txt"
    concat_file.write_text("\n".join(f"file '{p.resolve()}'" for p in clips) + "\n", encoding="utf-8")
    output = OUTPUT_DIR / f"{story['id']}.mp4"
    run("ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(output))
    return output


def upload(video: Path, story: dict) -> str:
    required = ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError("Missing YouTube credentials: " + ", ".join(missing))
    credentials = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    site_url = "https://hornupdates.com" + story["internal_url"]
    description = (
        f"{story['summary']}\n\nWhy it matters: {story['why_it_matters']}\n\n"
        f"Read the full story: {site_url}\nPrimary source: {story['source_url']}\n\n"
        "Synthetic narration and animated editorial graphics are used in this video. "
        "Facts come from the linked primary source and verified HornUpdates article.\n\n"
        "#AI #ArtificialIntelligence #AINews #HornUpdates"
    )
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": short_title(story["title"] + " #Shorts"),
                "description": description,
                "tags": ["AI news", "artificial intelligence", "HornUpdates", story["source"], "Shorts"],
                "categoryId": "28",
                "defaultLanguage": "en",
            },
            "status": {
                "privacyStatus": os.environ.get("YOUTUBE_PRIVACY_STATUS", "public"),
                "selfDeclaredMadeForKids": False,
                "containsSyntheticMedia": True,
            },
        },
        media_body=MediaFileUpload(str(video), mimetype="video/mp4", resumable=True),
    )
    response = None
    while response is None:
        _, response = request.next_chunk()
    return response["id"]


def save_state(story: dict, video_id: str) -> None:
    state = load_json(STATE_FILE, {"published_story_ids": []})
    state.setdefault("published_story_ids", []).append(story["id"])
    state["last_run_at"] = datetime.now(timezone.utc).isoformat()
    state["last_video_id"] = video_id
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Render without uploading or changing state")
    args = parser.parse_args()
    story = choose_story()
    if not story:
        print("No unpublished verified HornUpdates AI story is available.")
        return 0
    print(f"Selected: {story['id']}")
    video = render(story)
    print(f"Rendered: {video}")
    if args.dry_run:
        print("Dry run complete; YouTube upload skipped.")
        return 0
    video_id = upload(video, story)
    save_state(story, video_id)
    print(f"Published: https://youtu.be/{video_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
