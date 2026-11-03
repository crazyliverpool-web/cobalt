#!/bin/zsh
PLIST_LABEL="com.alonsi.youtube-digest"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_LABEL.plist"

launchctl unload "$PLIST_DEST" 2>/dev/null || true
rm -f "$PLIST_DEST"

echo "Uninstalled LaunchAgent. .env, state.json, OAuth tokens, logs, and Sheet data left intact."
