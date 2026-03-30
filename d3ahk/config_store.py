from __future__ import annotations

import json
import re
from pathlib import Path

from d3ahk.models import AppConfig


CONFIG_DIR = Path.home() / ".d3ahk"
STATE_FILE = CONFIG_DIR / "state.json"


def sanitize_config_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "_", (name or "").strip())
    return cleaned[:64] or "default"


def ensure_config_dir() -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def list_config_names() -> list[str]:
    if not CONFIG_DIR.exists():
        return []
    return sorted(path.stem for path in CONFIG_DIR.glob("*.json") if path.is_file() and path.name != STATE_FILE.name)


def config_path(name: str) -> Path:
    return ensure_config_dir() / f"{sanitize_config_name(name)}.json"


def save_config(config: AppConfig) -> Path:
    config.ensure_slot_count()
    target = config_path(config.name)
    target.write_text(json.dumps(config.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    write_last_used(config.name)
    return target


def load_config(name: str) -> AppConfig:
    path = config_path(name)
    payload = json.loads(path.read_text(encoding="utf-8"))
    config = AppConfig.from_dict(payload)
    write_last_used(config.name)
    return config


def read_last_used() -> str | None:
    if not STATE_FILE.exists():
        return None
    try:
        payload = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = sanitize_config_name(str(payload.get("last_used", "") or ""))
    return value or None


def write_last_used(name: str) -> None:
    ensure_config_dir()
    STATE_FILE.write_text(
        json.dumps({"last_used": sanitize_config_name(name)}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_last_or_default() -> AppConfig | None:
    last_used = read_last_used()
    names = list_config_names()
    if last_used and last_used in names:
        return load_config(last_used)
    if names:
        return load_config(names[0])
    return None
