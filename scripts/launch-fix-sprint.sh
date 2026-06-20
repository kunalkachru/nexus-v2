#!/bin/bash
# NEXUS Parallel Fix Sprint Launcher
# Run this once to start all three tracks simultaneously
# Usage: bash scripts/launch-fix-sprint.sh

REPO="/Users/kunalkachru/Documents/nexus-v3"
DOCS="$REPO/docs/fix-sprint"

echo "=== NEXUS Parallel Fix Sprint ==="
echo "Launching 3 Claude Code sessions simultaneously..."
echo ""

# Create the prompt files inside the repo so Claude Code can read them
mkdir -p "$DOCS"

# Copy the track prompts into the repo (they need to be accessible from the repo directory)
# These files should already exist from the download — if not, run this script after downloading them

if [ ! -f "$HOME/Downloads/TRACK_A_BACKEND.md" ] && [ ! -f "$DOCS/TRACK_A_BACKEND.md" ]; then
  echo "❌ Track prompt files not found."
  echo "Download TRACK_A_BACKEND.md, TRACK_B_FRONTEND.md, TRACK_C_INFRA.md"
  echo "and place them in $HOME/Downloads/ or $DOCS/"
  exit 1
fi

# Copy from Downloads if not already in repo
for track in TRACK_A_BACKEND TRACK_B_FRONTEND TRACK_C_INFRA; do
  if [ -f "$HOME/Downloads/$track.md" ] && [ ! -f "$DOCS/$track.md" ]; then
    cp "$HOME/Downloads/$track.md" "$DOCS/$track.md"
    echo "✓ Copied $track.md to repo"
  fi
done

echo ""
echo "Opening 3 Terminal tabs..."
echo ""

# Launch all three sessions in separate Terminal tabs on macOS
osascript << 'APPLESCRIPT'
tell application "Terminal"
  -- Track A: Backend
  do script "cd /Users/kunalkachru/Documents/nexus-v3 && echo '=== TRACK A: BACKEND ===' && export CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=50 && claude --max-turns 50 --dangerously-skip-permissions < docs/fix-sprint/TRACK_A_BACKEND.md"
  
  -- Track B: Frontend (new tab)
  tell application "System Events" to keystroke "t" using command down
  delay 1
  do script "cd /Users/kunalkachru/Documents/nexus-v3 && echo '=== TRACK B: FRONTEND ===' && export CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=50 && claude --max-turns 50 --dangerously-skip-permissions < docs/fix-sprint/TRACK_B_FRONTEND.md" in front window
  
  -- Track C: Infrastructure (new tab)
  tell application "System Events" to keystroke "t" using command down
  delay 1
  do script "cd /Users/kunalkachru/Documents/nexus-v3 && echo '=== TRACK C: INFRA ===' && export CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=50 && claude --max-turns 50 --dangerously-skip-permissions < docs/fix-sprint/TRACK_C_INFRA.md" in front window
end tell
APPLESCRIPT

echo ""
echo "✅ All 3 tracks launched in Terminal tabs"
echo ""
echo "While they run, do these manually:"
echo "  1. Buy a domain at namecheap.com and point A record to 92.5.47.239"
echo "  2. Open port 443 in Oracle Cloud console (same steps as port 7860)"
echo "  3. Once domain DNS propagates, tell Track C terminal:"
echo "     'Domain is ready: YOUR_DOMAIN — proceed with C1'"
echo ""
echo "When all tracks complete, run the release gate:"
echo "  bash scripts/run-release-gate.sh"
