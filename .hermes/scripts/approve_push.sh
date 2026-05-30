#!/bin/bash
# Usage: ./approve_push.sh <commit-sha>
# Called by the Verification agent after approving changes
# Writes an approval token that the pre-push hook checks

COMMIT_SHA="$1"
APPROVAL_FILE="/Users/oq/Documents/trading-signals-saas/.hermes/.last_verification"

if [ -z "$COMMIT_SHA" ]; then
  echo "Usage: $0 <commit-sha>"
  echo "Example: $0 a1b2c3d4"
  exit 1
fi

mkdir -p "$(dirname "$APPROVAL_FILE")"
echo "$COMMIT_SHA $(date '+%Y-%m-%d %H:%M:%S') verification-agent" > "$APPROVAL_FILE"
echo "✅ Push approved for commit $COMMIT_SHA"
