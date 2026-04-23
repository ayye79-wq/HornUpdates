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
#   - Either GITHUB_PAT secret (preferred) or the Replit GitHub integration must be connected

set -e

# If a Personal Access Token is available, configure git to use it for this push.
# The PAT must have "Contents" (write) and "Workflows" (write) permissions.
# This allows pushing changes to .github/workflows/ files, which the Replit
# OAuth token cannot do (it lacks the "workflow" scope).
CLEAN_URL=""
if [ -n "$GITHUB_PAT" ]; then
  REPO_URL=$(git remote get-url origin)

  # Only apply PAT rewrite for HTTPS remotes
  if [[ "$REPO_URL" == https://* ]]; then
    # Strip any existing credentials from the URL
    CLEAN_URL=$(echo "$REPO_URL" | sed 's|https://[^@]*@|https://|')
    HOST=$(echo "$CLEAN_URL" | sed 's|https://||' | cut -d'/' -f1)
    REPO_PATH=$(echo "$CLEAN_URL" | sed "s|https://$HOST/||")
    AUTH_URL="https://x-access-token:${GITHUB_PAT}@${HOST}/${REPO_PATH}"
    git remote set-url origin "$AUTH_URL"
    echo "==> Using GitHub PAT for authentication (workflow scope enabled)."

    # Guarantee the clean URL is restored on exit, error, or interrupt
    trap 'git remote set-url origin "$CLEAN_URL"' EXIT
  else
    echo "==> Warning: remote is not HTTPS; PAT rewrite skipped. Falling back to default auth."
  fi
else
  echo "==> No GITHUB_PAT found; using default Replit GitHub auth."
fi

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
# The EXIT trap above restores the clean remote URL automatically.

# -----------------------------------------------------------------------
# NOTE: The Replit GitHub OAuth token does NOT have the "workflow" scope.
# Pushes that include changes to .github/workflows/ files will be rejected
# unless GITHUB_PAT is set (see above).
#
# To set up the PAT:
#   1. Go to: github.com → Settings → Developer Settings
#      → Personal Access Tokens → Fine-grained tokens
#      → Permissions: Contents (write) + Workflows (write)
#   2. Copy the token value
#   3. Add it as a Replit secret named GITHUB_PAT
#      (Replit sidebar → Secrets → + Add a secret)
# -----------------------------------------------------------------------
