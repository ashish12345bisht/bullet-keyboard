"""Desktop front-end for Windows and macOS: a small window plus a global key listener."""

import random
import sys
import time
import tkinter as tk

from .audio import StreamMixer
from .sounds import GUNS, render_all

if sys.platform == "darwin":
    from . import keys_mac as keys
    FONT = "Helvetica Neue"
else:
    from . import keys_win as keys
    FONT = "Segoe UI"

GUN_NAMES = list(GUNS)
BG, FG, ACCENT, MUTED, PANEL = "#1e1f22", "#e8e8e8", "#e5533d", "#8a8d93", "#2b2d31"


def _button(parent, command, **kw):
    # Labels instead of tk.Button: macOS ignores button background colours.
    b = tk.Label(parent, cursor="hand2", **kw)
    b.bind("<Button-1>", lambda e: command())
    return b


class GuiApp:
    def __init__(self):
        self.bank = render_all()
        self.mixer = StreamMixer(0.7)
        self.gun = GUN_NAMES[0]
        self.enabled = True
        self.last_auto = 0.0
        self.dirty = False  # set from the listener thread, picked up by the Tk loop
        self._build()

    # --- actions -----------------------------------------------------------
    def fire(self):
        self.mixer.play(random.choice(self.bank[self.gun]))

    def set_gun(self, name):
        self.gun = name
        self.fire()
        self.dirty = True

    def cycle_gun(self):
        self.set_gun(GUN_NAMES[(GUN_NAMES.index(self.gun) + 1) % len(GUN_NAMES)])

    def toggle(self):
        self.enabled = not self.enabled
        self.dirty = True

    # --- global key listener (runs on its own thread) ----------------------
    def on_key(self, vk, repeat, hotkey_mods):
        if hotkey_mods and not repeat:
            if vk == keys.VK_B:
                return self.toggle()
            if vk == keys.VK_N:
                return self.cycle_gun()
        if not self.enabled:
            return
        if not repeat:
            self.fire()
        elif GUNS[self.gun][1]:  # key held: automatic weapons keep firing
            now = time.monotonic()
            if now - self.last_auto > 0.07:
                self.last_auto = now
                self.fire()

    # --- window ------------------------------------------------------------
    def _build(self):
        root = self.root = tk.Tk()
        root.title("Bullet Keyboard")
        root.configure(bg=BG, padx=18, pady=14)
        root.resizable(False, False)

        tk.Label(root, text="BULLET KEYBOARD", font=(FONT, 16, "bold"),
                 bg=BG, fg=ACCENT).pack(anchor="w")
        tk.Label(root, text="Every key you press, in any app, fires a shot.",
                 font=(FONT, 9), bg=BG, fg=MUTED).pack(anchor="w", pady=(0, 10))

        self.power = _button(root, self.toggle, font=(FONT, 12, "bold"), pady=6)
        self.power.pack(fill="x")

        grid = tk.Frame(root, bg=BG)
        grid.pack(pady=12)
        self.gun_buttons = {}
        for i, name in enumerate(GUN_NAMES):
            label = name.upper() if len(name) <= 3 else name.title()
            b = _button(grid, lambda n=name: self.set_gun(n), text=label, width=10, pady=4,
                        font=(FONT, 10))
            b.grid(row=i // 4, column=i % 4, padx=3, pady=3)
            self.gun_buttons[name] = b

        row = tk.Frame(root, bg=BG)
        row.pack(fill="x")
        tk.Label(row, text="Volume", bg=BG, fg=FG, font=(FONT, 10)).pack(side="left")
        vol = tk.Scale(row, from_=0, to=150, orient="horizontal", showvalue=False,
                       bg=BG, fg=FG, troughcolor="#3a3c41", highlightthickness=0, bd=0,
                       activebackground=ACCENT, length=260,
                       command=lambda v: setattr(self.mixer, "volume", int(v) / 100))
        vol.set(int(self.mixer.volume * 100))
        vol.pack(side="left", padx=8)

        self.notice = tk.Label(root, font=(FONT, 10, "bold"), bg=BG, fg="#f0b429", justify="left")
        tk.Label(root, text=f"{keys.HOTKEY_LABEL}+B  on/off      {keys.HOTKEY_LABEL}+N  next gun\n"
                            "Close this window to stop.",
                 font=(FONT, 9), bg=BG, fg=MUTED, justify="left").pack(anchor="w", pady=(10, 0))
        self.refresh()

    def refresh(self):
        self.dirty = False
        if self.enabled:
            self.power.config(text="ON  — click to mute", bg=ACCENT, fg="white")
        else:
            self.power.config(text="OFF  — click to arm", bg="#3a3c41", fg=FG)
        for name, b in self.gun_buttons.items():
            on = name == self.gun
            b.config(bg=FG if on else PANEL, fg=BG if on else FG)

    def _poll(self):
        if self.dirty:
            self.refresh()
        self.root.after(100, self._poll)

    def run(self):
        if not keys.start(self.on_key):
            self.notice.config(text=keys.permission_help())
            self.notice.pack(anchor="w", pady=(10, 0))
        self._poll()
        try:
            self.root.mainloop()
        finally:
            self.mixer.close()


def main():
    try:
        app = GuiApp()
    except Exception as e:  # most likely no audio output device
        from tkinter import messagebox

        tk.Tk().withdraw()
        messagebox.showerror("Bullet Keyboard", f"Couldn't start audio output.\n\n{e}\n\n"
                             "Check that speakers or headphones are connected.")
        return
    app.run()
