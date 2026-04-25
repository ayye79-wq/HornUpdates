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

ASKPASS_SCRIPT=""

# If a Personal Access Token is available, configure git to use it for this push.
# The PAT must have "Contents" (write) and "Workflows" (write) permissions.
# This allows pushing changes to .github/workflows/ files, which the Replit
# OAuth token cannot do (it lacks the "workflow" scope).
#
# Replit sets GIT_ASKPASS=replit-git-askpass which overrides URL-embedded credentials.
# We bypass this by writing a temporary askpass helper that returns the PAT directly.
if [ -n "$GITHUB_PAT" ]; then
  REPO_URL=$(git remote get-url origin)
  if [[ "$REPO_URL" == https://* ]]; then
    echo "==> Using GitHub PAT for authentication (workflow scope enabled)."

    # Write a temporary askpass script that outputs the PAT as the password
    ASKPASS_SCRIPT=$(mktemp /tmp/git-askpass-XXXXXX.sh)
    chmod +x "$ASKPASS_SCRIPT"
    printf '#!/bin/sh\necho "%s"\n' "$GITHUB_PAT" > "$ASKPASS_SCRIPT"

    # Override Replit's askpass with our PAT-returning script
    export GIT_ASKPASS="$ASKPASS_SCRIPT"
    export GIT_USERNAME="x-access-token"

    # Guarantee cleanup on exit, error, or interrupt
    trap 'rm -f "$ASKPASS_SCRIPT"; git remote set-url origin "$(git remote get-url origin | sed '"'"'s|https://[^@]*@|https://|'"'"')" 2>/dev/null || true' EXIT

    # Embed credentials in the URL so git knows which username to use
    CLEAN_URL=$(echo "$REPO_URL" | sed 's|https://[^@]*@|https://|')
    HOST=$(echo "$CLEAN_URL" | sed 's|https://||' | cut -d'/' -f1)
    REPO_PATH=$(echo "$CLEAN_URL" | sed "s|https://$HOST/||")
    AUTH_URL="https://x-access-token:${GITHUB_PAT}@${HOST}/${REPO_PATH}"
    git remote set-url origin "$AUTH_URL"
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
# The EXIT trap above cleans up the askpass script and restores the clean remote URL.

# -----------------------------------------------------------------------
# NOTE: The Replit GitHub OAuth token does NOT have the "workflow" scope.
# Pushes that include changes to .github/workflows/ files will be rejected
# unless GITHUB_PAT is set (see above).
#
# To set up the PAT:
#   1. Go to: github.com → Settings → Developer Settings
#      → Personal Access Tokens → Fine-grained tokens
#      → Repository access: Only select repositories → HornUpdates
#      → Permissions: Contents (write) + Workflows (write)
#   2. Copy the token value
#   3. Add it as a Replit secret named GITHUB_PAT
#      (Replit sidebar → Secrets → + Add a secret)
# -----------------------------------------------------------------------
