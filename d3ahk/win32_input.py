from __future__ import annotations

import ctypes
import time

from d3ahk.models import ActionType, TriggerConfig


user32 = ctypes.windll.user32

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

KEYEVENTF_KEYUP = 0x0002

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800

WHEEL_DELTA = 120

VK_CODES: dict[str, int] = {chr(code): code for code in range(ord("A"), ord("Z") + 1)}
VK_CODES.update({str(number): ord(str(number)) for number in range(0, 10)})
VK_CODES.update({f"F{index}": 0x6F + index for index in range(1, 13)})
VK_CODES.update(
    {
        "SPACE": 0x20,
        "ENTER": 0x0D,
        "ESC": 0x1B,
        "TAB": 0x09,
        "UP": 0x26,
        "DOWN": 0x28,
        "LEFT": 0x25,
        "RIGHT": 0x27,
    }
)


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong), ("wParamL", ctypes.c_short), ("wParamH", ctypes.c_ushort)]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("union", INPUT_UNION)]


def _send_keyboard(vk_code: int, key_up: bool) -> None:
    event = INPUT(
        type=INPUT_KEYBOARD,
        union=INPUT_UNION(
            ki=KEYBDINPUT(
                wVk=vk_code,
                wScan=0,
                dwFlags=KEYEVENTF_KEYUP if key_up else 0,
                time=0,
                dwExtraInfo=None,
            )
        ),
    )
    user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))


def _send_mouse(flags: int, data: int = 0) -> None:
    event = INPUT(
        type=INPUT_MOUSE,
        union=INPUT_UNION(
            mi=MOUSEINPUT(
                dx=0,
                dy=0,
                mouseData=data,
                dwFlags=flags,
                time=0,
                dwExtraInfo=None,
            )
        ),
    )
    user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))


def _execute_keyboard(trigger: TriggerConfig) -> None:
    vk_code = VK_CODES.get(trigger.input_code)
    if not vk_code:
        return

    if trigger.action is ActionType.PRESS:
        _send_keyboard(vk_code, key_up=False)
        return

    if trigger.action is ActionType.RELEASE:
        _send_keyboard(vk_code, key_up=True)
        return

    _send_keyboard(vk_code, key_up=False)
    time.sleep(0.002)
    _send_keyboard(vk_code, key_up=True)


def _execute_mouse_button(trigger: TriggerConfig) -> None:
    if trigger.input_code == "MOUSE_LEFT":
        down_flag = MOUSEEVENTF_LEFTDOWN
        up_flag = MOUSEEVENTF_LEFTUP
    else:
        down_flag = MOUSEEVENTF_RIGHTDOWN
        up_flag = MOUSEEVENTF_RIGHTUP

    if trigger.action is ActionType.PRESS:
        _send_mouse(down_flag)
        return

    if trigger.action is ActionType.RELEASE:
        _send_mouse(up_flag)
        return

    _send_mouse(down_flag)
    time.sleep(0.002)
    _send_mouse(up_flag)


def _execute_wheel(trigger: TriggerConfig) -> None:
    direction = WHEEL_DELTA if trigger.input_code == "WHEEL_UP" else -WHEEL_DELTA
    _send_mouse(MOUSEEVENTF_WHEEL, direction)


def execute_trigger(trigger: TriggerConfig) -> None:
    if not trigger.enabled:
        return

    if trigger.input_code in {"MOUSE_LEFT", "MOUSE_RIGHT"}:
        _execute_mouse_button(trigger)
        return

    if trigger.input_code in {"WHEEL_UP", "WHEEL_DOWN"}:
        _execute_wheel(trigger)
        return

    _execute_keyboard(trigger)
