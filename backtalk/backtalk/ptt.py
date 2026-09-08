# Zero Voice Engine // backtalk
# Licensed under AGPL-3.0
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Hold-to-talk — a global key listener.

HOLD the key -> mic opens. RELEASE -> mic closes and the utterance is
processed. The button IS the voice-activity detector, which is why this
mode is speaker-safe with no headphones: the mic simply isn't open while
the assistant talks, unless you press the key — and pressing while it
talks interrupts it.

THE KEY-REPEAT TRAP (the bug that kills every naive build): the OS fires
on_press events CONTINUOUSLY while a key is held. Without the held-state
filter below, every repeat reads as a fresh press and keeps cancelling
the reply before it can speak.

AND THE HALF THAT TRAP HIDES: some keyboards send auto-repeat as full
DOWN/UP PAIRS rather than the repeated DOWN-only stream. Filtering the
presses and trusting every release then breaks the OTHER way -- a single
hold is chopped into dozens of ~50ms recordings, each too short to
transcribe, and the whole thing is SILENT. No exception, no log line,
nothing to search for; it simply reads as "the microphone does not work".
Measured in the field on a Logitech MX Mechanical through a Bolt
receiver: one 2.6-second hold produced 186 key events and about fifty
recordings. So a release is never trusted on sight -- see is_held().

macOS needs Input Monitoring permission for the hosting terminal
(System Settings -> Privacy & Security -> Input Monitoring). Windows
works out of the box; some Linux desktops need the user in the `input`
group or an X11 session.
"""
import threading
import time

from pynput import keyboard


import ctypes
import sys
import threading
import time

from pynput import keyboard

VK_SHIFT = 0x10
VK_LSHIFT = 0xA0
VK_RSHIFT = 0xA1
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt


def resolve_key(name: str):
    """'shift' / 'home' / 'f13' / 'right_alt' / any single character -> pynput key(s)."""
    name = (name or "shift").strip().lower()
    if len(name) == 1:
        return {keyboard.KeyCode.from_char(name)}

    # Shift aliases: group all shift variants together so Left/Right Shift always match
    if name in ("shift", "left_shift", "right_shift", "shift_l", "shift_r"):
        keys = {keyboard.Key.shift}
        if hasattr(keyboard.Key, "shift_l"):
            keys.add(keyboard.Key.shift_l)
        if hasattr(keyboard.Key, "shift_r"):
            keys.add(keyboard.Key.shift_r)
        return keys

    if name in ("ctrl", "control", "left_ctrl", "right_ctrl", "ctrl_l", "ctrl_r"):
        keys = {keyboard.Key.ctrl}
        if hasattr(keyboard.Key, "ctrl_l"):
            keys.add(keyboard.Key.ctrl_l)
        if hasattr(keyboard.Key, "ctrl_r"):
            keys.add(keyboard.Key.ctrl_r)
        return keys

    if name in ("alt", "left_alt", "right_alt", "alt_l", "alt_r", "option", "left_option", "right_option"):
        keys = {keyboard.Key.alt}
        if hasattr(keyboard.Key, "alt_l"):
            keys.add(keyboard.Key.alt_l)
        if hasattr(keyboard.Key, "alt_r"):
            keys.add(keyboard.Key.alt_r)
        return keys

    aliases = {
        "right_cmd": "cmd_r", "left_cmd": "cmd_l",
    }
    name = aliases.get(name, name)
    try:
        return {getattr(keyboard.Key, name)}
    except AttributeError:
        print(f"[ptt] unknown key {name!r} — falling back to 'shift'",
              flush=True)
        return {keyboard.Key.shift}


class PTTListener:
    # Debounce grace window to absorb keyboard auto-repeat bounce
    RELEASE_GRACE = 0.12

    def __init__(self, key="shift"):
        if isinstance(key, (set, list, tuple)):
            self._keys = set(key)
        else:
            self._keys = resolve_key(key) if isinstance(key, str) else {key}

        self._is_shift = any("shift" in getattr(k, "name", "").lower() for k in self._keys)
        self._held = False
        self._release_t = None          # a release awaiting confirmation
        self._press_evt = threading.Event()
        self._listener = keyboard.Listener(on_press=self._on_press,
                                           on_release=self._on_release)
        self._listener.daemon = True
        self._listener.start()

    def _matches(self, k) -> bool:
        if k in self._keys:
            return True
        # If looking for shift, match any shift event
        if self._is_shift and getattr(k, "name", "").startswith("shift"):
            return True
        return False

    def _on_press(self, k):
        if not self._matches(k):
            return
        self._release_t = None
        if not self._held:                      # filter key-repeat
            self._held = True
            self._press_evt.set()

    def _on_release(self, k):
        if self._matches(k):
            # PROVISIONAL. Believed only if no press follows; see _settle().
            self._release_t = time.monotonic()

    def _settle(self):
        """Commit a release that has stood unchallenged for the grace window."""
        # On Windows, check physical hardware state via Win32 API for zero-lag accuracy
        if sys.platform == "win32" and self._is_shift:
            physically_down = bool(ctypes.windll.user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)
            if physically_down:
                self._held = True
                self._release_t = None
                return
            elif self._held and self._release_t is None:
                self._release_t = time.monotonic()

        r = self._release_t
        if self._held and r is not None and \
                time.monotonic() - r >= self.RELEASE_GRACE:
            self._held = False
            self._release_t = None

    def wait_press(self):
        """Block until the key goes DOWN (one event per physical press)."""
        while True:
            self._settle()
            # If on Windows and physically held, set event immediately
            if sys.platform == "win32" and self._is_shift:
                if bool(ctypes.windll.user32.GetAsyncKeyState(VK_SHIFT) & 0x8000):
                    self._held = True
                    self._release_t = None
                    return
            if self._press_evt.wait(timeout=self.RELEASE_GRACE):
                self._press_evt.clear()
                return

    def is_held(self) -> bool:
        self._settle()
        if sys.platform == "win32" and self._is_shift:
            return bool(ctypes.windll.user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)
        return self._held

