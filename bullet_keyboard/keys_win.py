"""Windows global key listener (pynput low-level keyboard hook)."""

from pynput import keyboard

VK_B, VK_N = 0x42, 0x4E
HOTKEY_LABEL = "Ctrl+Alt"


def _modifier(key):
    name = getattr(key, "name", "")
    if name.startswith("ctrl"):
        return "CTRL"
    if name.startswith("alt"):
        return "ALT"
    return None


def start(on_key):
    """Call on_key(vk, repeat, hotkey_mods) for every key press. Returns True once listening."""
    mods, held = set(), set()

    def on_press(key):
        mod = _modifier(key)
        if mod:
            mods.add(mod)
            return
        vk = getattr(key, "vk", None)
        ident = vk if vk is not None else key
        repeat = ident in held  # Windows auto-repeats presses without a release in between
        held.add(ident)
        on_key(vk, repeat, mods >= {"CTRL", "ALT"})

    def on_release(key):
        mod = _modifier(key)
        if mod:
            mods.discard(mod)
            return
        vk = getattr(key, "vk", None)
        held.discard(vk if vk is not None else key)

    keyboard.Listener(on_press=on_press, on_release=on_release).start()
    return True


def permission_help():
    return ""
