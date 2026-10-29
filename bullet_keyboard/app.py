"""Terminal front-end: listens to every keyboard via evdev and fires gunshots."""

import argparse
import glob
import os
import random
import selectors
import sys
import termios
import time
import tty

from .audio import Mixer
from .sounds import GUNS, render_all

GUN_NAMES = list(GUNS)
HELP = (
    "Global hotkeys (work in any window):\n"
    "  Ctrl+Alt+B   turn on/off\n"
    "  Ctrl+Alt+N   next gun\n"
    "\n"
    "In this terminal:\n"
    "  1-{n}  pick gun   space  on/off   +/-  volume   p  preview   q  quit\n"
)


def find_keyboards():
    import evdev
    from evdev import ecodes

    kbds, denied = [], 0
    # list_devices() hides unreadable devices, so glob ourselves to detect permission problems.
    for path in sorted(glob.glob("/dev/input/event*")):
        try:
            dev = evdev.InputDevice(path)
        except PermissionError:
            denied += 1
            continue
        keys = dev.capabilities().get(ecodes.EV_KEY, [])
        if ecodes.KEY_A in keys and ecodes.KEY_SPACE in keys:
            kbds.append(dev)
        else:
            dev.close()
    return kbds, denied


def permission_help():
    print(
        "Can't read any keyboard devices from /dev/input.\n\n"
        "On Wayland, apps can't see global keystrokes, so this app reads the keyboard\n"
        "device directly. Add yourself to the 'input' group once:\n\n"
        "    sudo usermod -aG input $USER\n\n"
        "then log out and back in (or run `newgrp input` in this terminal to try it now).",
        file=sys.stderr,
    )


class App:
    def __init__(self, gun, volume):
        print("Loading guns...", end="", flush=True)
        self.bank = render_all()
        print(" done.")
        self.gun = gun
        self.enabled = True
        self.mixer = Mixer(volume)
        self.mods = set()
        self.last_auto = 0.0

    # --- actions -----------------------------------------------------------
    def fire(self, gun=None):
        self.mixer.play(random.choice(self.bank[gun or self.gun]))

    def set_gun(self, name):
        self.gun = name
        self.fire()
        self.status()

    def cycle_gun(self):
        self.set_gun(GUN_NAMES[(GUN_NAMES.index(self.gun) + 1) % len(GUN_NAMES)])

    def toggle(self):
        self.enabled = not self.enabled
        self.status()

    def volume(self, delta):
        self.mixer.volume = min(1.5, max(0.0, round(self.mixer.volume + delta, 2)))
        self.status()

    def preview(self):
        for name in GUN_NAMES:
            self.gun = name
            self.status()
            self.fire()
            time.sleep(0.9)
        self.status()

    def status(self):
        state = "\033[32mON \033[0m" if self.enabled else "\033[31mOFF\033[0m"
        guns = "  ".join(
            f"\033[7m{i + 1}:{n}\033[0m" if n == self.gun else f"{i + 1}:{n}"
            for i, n in enumerate(GUN_NAMES)
        )
        sys.stdout.write(f"\r\033[K[{state}] vol {int(self.mixer.volume * 100):3d}%  {guns}")
        sys.stdout.flush()

    # --- input -------------------------------------------------------------
    def on_key(self, code, value):
        from evdev import ecodes

        name = ecodes.KEY.get(code, "")
        if isinstance(name, list):
            name = name[0]
        if "CTRL" in name or "ALT" in name:
            (self.mods.add if value else self.mods.discard)("CTRL" if "CTRL" in name else "ALT")
            return
        if value == 0:
            return
        if value == 1 and self.mods >= {"CTRL", "ALT"}:
            if code == ecodes.KEY_B:
                return self.toggle()
            if code == ecodes.KEY_N:
                return self.cycle_gun()
        if not self.enabled:
            return
        if value == 1:
            self.fire()
        elif value == 2 and GUNS[self.gun][1]:  # key held: automatic weapons keep firing
            now = time.monotonic()
            if now - self.last_auto > 0.07:
                self.last_auto = now
                self.fire()

    def on_tty(self, ch):
        if ch in ("q", "\x03"):
            raise KeyboardInterrupt
        if ch == " ":
            self.toggle()
        elif ch in "+=":
            self.volume(0.1)
        elif ch in "-_":
            self.volume(-0.1)
        elif ch == "p":
            self.preview()
        elif ch.isdigit() and 1 <= int(ch) <= len(GUN_NAMES):
            self.set_gun(GUN_NAMES[int(ch) - 1])

    def run(self, keyboards):
        sel = selectors.DefaultSelector()
        for dev in keyboards:
            sel.register(dev, selectors.EVENT_READ, "kbd")
        interactive = sys.stdin.isatty()
        old_tty = None
        if interactive:
            old_tty = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin)
            sel.register(sys.stdin, selectors.EVENT_READ, "tty")
        print("Listening on: " + ", ".join(d.name for d in keyboards))
        print(HELP.format(n=len(GUN_NAMES)))
        self.status()
        try:
            while True:
                for key, _ in sel.select():
                    if key.data == "tty":
                        self.on_tty(os.read(sys.stdin.fileno(), 1).decode(errors="ignore"))
                        continue
                    try:
                        events = list(key.fileobj.read())
                    except OSError:  # device unplugged
                        sel.unregister(key.fileobj)
                        continue
                    for ev in events:
                        if ev.type == 1:  # EV_KEY
                            self.on_key(ev.code, ev.value)
        except KeyboardInterrupt:
            pass
        finally:
            if old_tty:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
            print()
            self.mixer.close()


def main():
    p = argparse.ArgumentParser(description="Make your keyboard sound like gunshots.")
    p.add_argument("-g", "--gun", choices=GUN_NAMES, default="pistol")
    p.add_argument("-v", "--volume", type=float, default=0.7, help="0.0 - 1.5 (default 0.7)")
    p.add_argument("--off", action="store_true", help="start disabled")
    p.add_argument("--preview", action="store_true", help="play every gun once and exit")
    args = p.parse_args()

    if args.preview:
        app = App(args.gun, args.volume)
        app.preview()
        time.sleep(1.5)
        print()
        app.mixer.close()
        return

    keyboards, denied = find_keyboards()
    if not keyboards:
        permission_help() if denied else print("No keyboard found.", file=sys.stderr)
        sys.exit(1)
    app = App(args.gun, args.volume)
    app.enabled = not args.off
    app.run(keyboards)


if __name__ == "__main__":
    main()
