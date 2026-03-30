from __future__ import annotations

import ctypes

from PySide6.QtCore import QAbstractNativeEventFilter

from d3ahk.models import HotkeyConfig


user32 = ctypes.windll.user32

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004

TOGGLE_HOTKEY_ID = 1


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_size_t),
        ("lParam", ctypes.c_size_t),
        ("time", ctypes.c_ulong),
        ("pt_x", ctypes.c_long),
        ("pt_y", ctypes.c_long),
        ("lPrivate", ctypes.c_ulong),
    ]


class GlobalHotkeyManager(QAbstractNativeEventFilter):
    def __init__(self, app, on_toggle) -> None:
        super().__init__()
        self._app = app
        self._on_toggle = on_toggle
        self._registered = False
        self._app.installNativeEventFilter(self)

    def nativeEventFilter(self, event_type, message):
        if event_type not in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            return False, 0

        msg = MSG.from_address(int(message))
        if msg.message != WM_HOTKEY:
            return False, 0

        if msg.wParam == TOGGLE_HOTKEY_ID:
            self._on_toggle()
            return True, 0

        return False, 0

    def register(self, hotkey: HotkeyConfig) -> None:
        self.unregister()
        modifiers = 0
        if hotkey.alt:
            modifiers |= MOD_ALT
        if hotkey.ctrl:
            modifiers |= MOD_CONTROL
        if hotkey.shift:
            modifiers |= MOD_SHIFT

        if modifiers == 0:
            raise RuntimeError("At least one modifier key is required.")

        if not user32.RegisterHotKey(None, TOGGLE_HOTKEY_ID, modifiers, ord(hotkey.normalized_letter())):
            raise RuntimeError("Unable to register the toggle hotkey.")

        self._registered = True

    def unregister(self) -> None:
        if not self._registered:
            return
        user32.UnregisterHotKey(None, TOGGLE_HOTKEY_ID)
        self._registered = False
