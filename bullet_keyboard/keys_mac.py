"""macOS global key listener: a listen-only Quartz event tap on its own run loop.

pynput's macOS listener calls keyboard-layout (TIS) APIs off the main thread, which
recent macOS versions abort on. We only need key codes, so we tap events directly.
"""

import threading

import CoreFoundation as CF
import Quartz as Q

VK_B, VK_N = 11, 45
HOTKEY_LABEL = "Ctrl+Option"
_HOTKEY_FLAGS = Q.kCGEventFlagMaskControl | Q.kCGEventFlagMaskAlternate
_TAP_DISABLED = (Q.kCGEventTapDisabledByTimeout, Q.kCGEventTapDisabledByUserInput)


def start(on_key):
    """Call on_key(vk, repeat, hotkey_mods) for every key press.

    Returns False if the app hasn't been allowed Input Monitoring yet.
    """
    if not Q.CGPreflightListenEventAccess():
        Q.CGRequestListenEventAccess()  # adds the app to the list in System Settings
        return False

    tap = None

    def callback(proxy, etype, event, refcon):
        if etype in _TAP_DISABLED:
            Q.CGEventTapEnable(tap, True)
        elif etype == Q.kCGEventKeyDown:
            vk = Q.CGEventGetIntegerValueField(event, Q.kCGKeyboardEventKeycode)
            repeat = Q.CGEventGetIntegerValueField(event, Q.kCGKeyboardEventAutorepeat) != 0
            flags = Q.CGEventGetFlags(event)
            on_key(vk, repeat, flags & _HOTKEY_FLAGS == _HOTKEY_FLAGS)
        return event

    tap = Q.CGEventTapCreate(
        Q.kCGSessionEventTap, Q.kCGHeadInsertEventTap, Q.kCGEventTapOptionListenOnly,
        Q.CGEventMaskBit(Q.kCGEventKeyDown), callback, None,
    )
    if tap is None:
        return False

    def run():
        source = CF.CFMachPortCreateRunLoopSource(None, tap, 0)
        CF.CFRunLoopAddSource(CF.CFRunLoopGetCurrent(), source, CF.kCFRunLoopCommonModes)
        Q.CGEventTapEnable(tap, True)
        CF.CFRunLoopRun()

    threading.Thread(target=run, daemon=True).start()
    return True


def permission_help():
    return ("Keys can't be heard yet. Open System Settings → Privacy & Security →\n"
            "Input Monitoring, turn on Bullet Keyboard, then quit and reopen it.")
