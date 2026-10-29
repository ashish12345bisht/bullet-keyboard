#!/usr/bin/env bash
# Builds dist/BulletKeyboard.exe from Linux using Windows Python under Wine (Docker).
set -e
cd "$(dirname "$0")/.."
docker run --rm -v "$PWD":/src -w /src -e OWNER="$(id -u):$(id -g)" tobix/pywine:3.12 bash -c '
  wine python -m pip install -q -r packaging/requirements.txt &&
  wine pyinstaller --noconfirm --clean --onefile --windowed --noupx --name BulletKeyboard \
    --hidden-import pynput.keyboard._win32 --hidden-import pynput.mouse._win32 --paths . \
    --distpath dist --workpath build --specpath build packaging/app.py &&
  BULLET_KEYBOARD_SELFTEST=1 wine dist/BulletKeyboard.exe
  status=$?
  chown -R "$OWNER" dist build 2>/dev/null
  exit $status'
