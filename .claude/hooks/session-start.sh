#!/bin/bash
# Installiert die Abhängigkeiten des Vorlagenmanagers, damit Prüfung und
# Generierung sofort laufen. Nur in Claude Code on the web nötig - lokal
# regelt das die eigene Umgebung.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"
pip install --quiet --disable-pip-version-check -r requirements.txt
