#!/bin/bash
# push_to_github.sh — Sync Replit changes to GitHub without conflicts
#
# Run this script (or follow these steps manually) whenever you want to push
# Replit edits up to GitHub.
#
# Usage:
#   bash push_to_github.sh
#
# Requirements:
#   - Git remote "origin" must point to the GitHub repo
#   - The Replit GitHub integration must be connected (handles auth)

set -e

echo "==> Fetching latest changes from GitHub..."
git fetch origin

echo "==> Rebasing local commits on top of GitHub's latest..."
if ! git pull --rebase origin main; then
  echo ""
  echo "REBASE CONFLICT: Automatic rebase failed due to conflicting changes."
  echo "Run: git rebase --abort"
  echo "Then resolve conflicts manually, or ask the Replit agent to help."
  exit 1
fi

echo "==> Pushing to GitHub..."
git push origin main

echo "==> Done. Replit and GitHub are now in sync."

# -----------------------------------------------------------------------
# NOTE: The Replit GitHub OAuth token does NOT have the "workflow" scope.
# Pushes that include changes to .github/workflows/ files will be rejected.
#
# Options for updating workflow files:
#
#   Option A (simplest): Edit them directly on github.com in the browser.
#
#   Option B: Use the Replit agent to push via the GitHub API (file-by-file),
#             which bypasses the workflow scope restriction.
#
#   Option C: Use a Personal Access Token (PAT) stored via git credential helper:
#             1. Generate a PAT at: github.com → Settings → Developer Settings
#                → Personal Access Tokens → Fine-grained tokens
#                → Permissions: Contents (write) + Workflows (write)
#             2. Store it safely (never in plain URL):
#                git credential approve <<EOF
#                protocol=https
#                host=github.com
#                username=ayye79-wq
#                password=<YOUR_PAT>
#                EOF
#             3. Now regular "git push origin main" will use the PAT.
# -----------------------------------------------------------------------
