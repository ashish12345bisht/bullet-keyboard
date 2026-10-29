#!/usr/bin/env bash
# Native build. On a Mac: dist/BulletKeyboard.app + a zip to share.
# On Windows (Git Bash): dist/BulletKeyboard.exe.
# Needs Python 3.12 with Tk (python.org installer; Homebrew needs `brew install python-tk@3.12`).
set -e
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python3}"
"$PYTHON" -m venv build/venv
if [ -d build/venv/Scripts ]; then BIN=build/venv/Scripts; else BIN=build/venv/bin; fi
"$BIN/python" -m pip install -q -r packaging/requirements.txt

ARGS=(--noconfirm --clean --windowed --name BulletKeyboard --paths .
      --distpath dist --workpath build --specpath build)
case "$(uname -s)" in
  Darwin)
    "$BIN/pyinstaller" "${ARGS[@]}" --osx-bundle-identifier com.bulletkeyboard.app packaging/app.py
    BULLET_KEYBOARD_SELFTEST=1 dist/BulletKeyboard.app/Contents/MacOS/BulletKeyboard
    ditto -c -k --keepParent dist/BulletKeyboard.app "dist/BulletKeyboard-mac-$(uname -m).zip"
    ;;
  *)
    "$BIN/pyinstaller" "${ARGS[@]}" --onefile \
      --hidden-import pynput.keyboard._win32 --hidden-import pynput.mouse._win32 packaging/app.py
    BULLET_KEYBOARD_SELFTEST=1 dist/BulletKeyboard.exe
    ;;
esac
ls -la dist
