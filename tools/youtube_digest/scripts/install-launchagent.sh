#!/bin/zsh
set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_LABEL="com.alonsi.youtube-digest"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_LABEL.plist"

chmod +x "$REPO_ROOT/scripts/run-digest.sh"

sed "s|__REPO_ROOT__|$REPO_ROOT|g" "$REPO_ROOT/scripts/$PLIST_LABEL.plist.example" > "$PLIST_DEST"

launchctl unload "$PLIST_DEST" 2>/dev/null || true
launchctl load "$PLIST_DEST"

echo "Installed LaunchAgent: $PLIST_DEST"
echo "Runs daily at 08:00 local time."
echo ""
echo "Verify with:"
echo "  launchctl list | grep youtube-digest"
echo "Run it manually right now with:"
echo "  launchctl start $PLIST_LABEL"
echo "Watch logs with:"
echo "  tail -f $REPO_ROOT/logs/launchd.out.log"
echo "  tail -f $REPO_ROOT/logs/launchd.err.log"
