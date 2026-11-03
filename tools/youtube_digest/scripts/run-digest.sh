#!/bin/zsh
# manual use only — launchd must NOT use this wrapper (TCC blocks /bin/zsh from
# reading files under ~/Desktop when launchd calls it directly; see for-opus/questions.md Q29)
# Runs the daily digest. Invoked manually (no shell profile/PATH loaded),
# so set a safe PATH explicitly and use absolute paths throughout.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 digest.py
