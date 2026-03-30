from __future__ import annotations

from d3ahk.models import ActionType


ACTION_OPTIONS: list[tuple[str, ActionType]] = [
    ("按下", ActionType.PRESS),
    ("释放", ActionType.RELEASE),
    ("点击", ActionType.CLICK),
]

HOTKEY_LETTERS = [chr(code) for code in range(ord("A"), ord("Z") + 1)]

INPUT_OPTIONS: list[tuple[str, str]] = [("", "未设置")]
INPUT_OPTIONS.extend((letter, letter) for letter in HOTKEY_LETTERS)
INPUT_OPTIONS.extend((str(number), str(number)) for number in range(0, 10))
INPUT_OPTIONS.extend((f"F{index}", f"F{index}") for index in range(1, 13))
INPUT_OPTIONS.extend(
    [
        ("SPACE", "Space"),
        ("ENTER", "Enter"),
        ("ESC", "Esc"),
        ("TAB", "Tab"),
        ("UP", "Arrow Up"),
        ("DOWN", "Arrow Down"),
        ("LEFT", "Arrow Left"),
        ("RIGHT", "Arrow Right"),
        ("MOUSE_LEFT", "Mouse Left"),
        ("MOUSE_RIGHT", "Mouse Right"),
        ("WHEEL_UP", "Wheel Up"),
        ("WHEEL_DOWN", "Wheel Down"),
    ]
)

INPUT_LABELS = {code: label for code, label in INPUT_OPTIONS}


def input_label(input_code: str) -> str:
    return INPUT_LABELS.get(input_code, input_code or "未设置")
