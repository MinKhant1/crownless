#!/usr/bin/env bash
# Build dist/Crownless.app (and dist/Crownless-mac.zip). Run on a Mac from the project folder:
#   bash build_mac.sh
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
fi
.venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt pyinstaller
.venv/bin/python -m PyInstaller --noconfirm --clean crownless.spec
# ditto keeps the bundle's symlinks and permissions intact, which plain zip can break
ditto -c -k --keepParent dist/Crownless.app dist/Crownless-mac.zip
echo "Done: dist/Crownless.app and dist/Crownless-mac.zip"
