# bullet-keyboard

Every key press fires a gunshot. Terminal app for Ubuntu (Wayland and X11).

Guns: pistol, revolver, rifle, smg, shotgun, sniper, silenced, laser.
Sounds are synthesized with numpy. There are no sample files.
Rifle, smg and laser keep firing while you hold a key down.

## Setup

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt
sudo usermod -aG input $USER   # one time, then log out/in
```

Wayland doesn't let apps see keys pressed in other windows, so the app reads
`/dev/input` directly. That's why it needs the `input` group.

## Usage

```bash
./bullet-keyboard                 # start with the pistol
./bullet-keyboard -g shotgun -v 1.0
./bullet-keyboard --preview       # hear every gun once
```

| Where | Key | Action |
|---|---|---|
| anywhere | Ctrl+Alt+B | on/off |
| anywhere | Ctrl+Alt+N | next gun |
| app terminal | 1–8 | pick gun |
| app terminal | space | on/off |
| app terminal | + / - | volume |
| app terminal | p | preview all guns |
| app terminal | q | quit |

## Windows and Mac app

A standalone desktop app with a small window: on/off button, gun picker, volume
slider. No Python needed. Hotkeys are Ctrl+Alt+B / Ctrl+Alt+N on Windows and
Ctrl+Option+B / Ctrl+Option+N on Mac.

**Windows** (`BulletKeyboard.exe`): unsigned, so SmartScreen says "Windows protected
your PC" on first run: click **More info → Run anyway**. To uninstall, delete the file.

**Mac** (`BulletKeyboard-mac-arm64.zip` for Apple Silicon, `-x86_64` for Intel):
unzip and drag `BulletKeyboard.app` to Applications. It's unsigned, so:

1. Open it once; macOS blocks it. Go to System Settings → Privacy & Security and
   click **Open Anyway**. (If it says the app "is damaged", run
   `xattr -dr com.apple.quarantine /Applications/BulletKeyboard.app`.)
2. Turn on Bullet Keyboard under Privacy & Security → **Input Monitoring**, then
   quit and reopen it.

To uninstall, drag it to the Trash.

### Building

```bash
./packaging/build-windows-on-linux.sh   # Windows .exe from Linux (Docker + Wine)
./packaging/build.sh                    # natively, on a Mac or Windows (Git Bash)
```

Pushing a `v*` tag to GitHub runs `.github/workflows/build.yml`, which builds the
Windows exe and both Mac zips on GitHub's machines and attaches them to a release.
