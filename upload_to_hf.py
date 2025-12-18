#!/usr/bin/env python3
"""
upload_to_hf.py

Uploads the local articles.json to your Hugging Face Space:
  repo_id = "KalidFan/HornUpdates"
"""

from pathlib import Path
from huggingface_hub import HfApi

TOKEN_PATH = Path("hf_token.txt")
SPACE_ID = "KalidFan/HornUpdates"
LOCAL_JSON = Path("articles.json")


def main():
    if not TOKEN_PATH.exists():
        print("[ERROR] hf_token.txt not found. Create it with your HF API token.")
        return

    token = TOKEN_PATH.read_text(encoding="utf-8").strip()
    if not token:
        print("[ERROR] hf_token.txt is empty.")
        return

    if not LOCAL_JSON.exists():
        print(f"[ERROR] {LOCAL_JSON} not found. Run update_articles.py first.")
        return

    print("[INFO] Uploading articles.json to Hugging Face Space:", SPACE_ID)
    api = HfApi(token=token)

    api.upload_file(
        path_or_fileobj=str(LOCAL_JSON),
        path_in_repo="articles.json",   # overwrite this file in the repo
        repo_id=SPACE_ID,
        repo_type="space",
    )

    print("[INFO] Upload complete.")


if __name__ == "__main__":
    main()
