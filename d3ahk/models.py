from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class ActionType(str, Enum):
    PRESS = "press"
    RELEASE = "release"
    CLICK = "click"


@dataclass(slots=True)
class TriggerConfig:
    input_code: str = ""
    action: ActionType = ActionType.CLICK
    interval_ms: int = 1000

    def __post_init__(self) -> None:
        self.action = self.normalize_action(self.action)

    @property
    def enabled(self) -> bool:
        return bool(self.input_code)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["action"] = self.normalize_action(self.action).value
        return data

    @staticmethod
    def normalize_action(action: ActionType | str) -> ActionType:
        if isinstance(action, ActionType):
            return action
        try:
            return ActionType(str(action))
        except ValueError:
            return ActionType.CLICK

    @classmethod
    def from_dict(cls, payload: dict) -> "TriggerConfig":
        action_value = payload.get("action", ActionType.CLICK.value)
        action = cls.normalize_action(action_value)

        interval_ms = int(payload.get("interval_ms", 1000) or 1000)
        if interval_ms < 1:
            interval_ms = 1

        return cls(
            input_code=str(payload.get("input_code", "") or ""),
            action=action,
            interval_ms=interval_ms,
        )


@dataclass(slots=True)
class HotkeyConfig:
    ctrl: bool = True
    shift: bool = True
    alt: bool = True
    letter: str = "S"

    def normalized_letter(self) -> str:
        letter = (self.letter or "S").strip().upper()
        if len(letter) != 1 or not letter.isalpha():
            return "S"
        return letter

    def has_modifier(self) -> bool:
        return self.ctrl or self.shift or self.alt

    def display(self) -> str:
        parts: list[str] = []
        if self.ctrl:
            parts.append("Ctrl")
        if self.shift:
            parts.append("Shift")
        if self.alt:
            parts.append("Alt")
        parts.append(self.normalized_letter())
        return "+".join(parts)

    def to_dict(self) -> dict:
        return {
            "ctrl": bool(self.ctrl),
            "shift": bool(self.shift),
            "alt": bool(self.alt),
            "letter": self.normalized_letter(),
        }

    @classmethod
    def from_dict(cls, payload: dict, default_letter: str) -> "HotkeyConfig":
        return cls(
            ctrl=bool(payload.get("ctrl", True)),
            shift=bool(payload.get("shift", True)),
            alt=bool(payload.get("alt", True)),
            letter=str(payload.get("letter", default_letter) or default_letter),
        )


@dataclass(slots=True)
class AppConfig:
    name: str
    toggle_hotkey: HotkeyConfig = field(default_factory=lambda: HotkeyConfig(letter="S"))
    triggers: list[TriggerConfig] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.ensure_slot_count()

    def ensure_slot_count(self) -> None:
        while len(self.triggers) < 10:
            self.triggers.append(TriggerConfig())
        if len(self.triggers) > 10:
            self.triggers = self.triggers[:10]

    def active_triggers(self) -> list[TriggerConfig]:
        return [trigger for trigger in self.triggers if trigger.enabled]

    def to_dict(self) -> dict:
        self.ensure_slot_count()
        return {
            "name": self.name,
            "toggle_hotkey": self.toggle_hotkey.to_dict(),
            "triggers": [trigger.to_dict() for trigger in self.triggers],
        }

    @classmethod
    def default(cls, name: str) -> "AppConfig":
        return cls(name=name)

    @classmethod
    def from_dict(cls, payload: dict) -> "AppConfig":
        triggers = [TriggerConfig.from_dict(item) for item in payload.get("triggers", [])]

        toggle_payload = payload.get("toggle_hotkey")
        if not isinstance(toggle_payload, dict):
            # Backward compatibility for previously saved start/stop hotkeys.
            toggle_payload = payload.get("start_hotkey", {})

        config = cls(
            name=str(payload.get("name", "default") or "default"),
            toggle_hotkey=HotkeyConfig.from_dict(toggle_payload, "S"),
            triggers=triggers,
        )
        config.ensure_slot_count()
        return config
