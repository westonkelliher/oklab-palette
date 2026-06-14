#!/usr/bin/env bash
# Regenerate the palette and open it in the browser.
set -e
cd "$(dirname "$0")"
python3 oklab_gen.py
google-chrome index.html >/dev/null 2>&1 &
