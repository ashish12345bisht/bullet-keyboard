import os
import sys

if os.environ.get("BULLET_KEYBOARD_SELFTEST"):
    # Used by the build: check every bundled module imports, without opening audio or a window.
    import sounddevice  # noqa: F401
    from bullet_keyboard import gui, sounds  # noqa: F401
    sounds.render_all()
    sys.exit(0)

from bullet_keyboard.gui import main

main()
