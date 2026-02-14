# utils/state.py
import json
import os
from threading import Lock

_STATE_FILE = os.path.join(os.path.dirname(__file__), "state.json")
_lock = Lock()

_DEFAULT = {
    "peak_enabled": False,
    "silent_enabled": False,
    "silent_start": "23:00",
    "silent_end": "07:00",
}

def _load():
    if not os.path.exists(_STATE_FILE):
        return dict(_DEFAULT)
    try:
        with open(_STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # merge defaults
        merged = dict(_DEFAULT)
        merged.update(data or {})
        return merged
    except Exception:
        return dict(_DEFAULT)

def _save(data: dict):
    os.makedirs(os.path.dirname(_STATE_FILE), exist_ok=True)
    with open(_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_peak_enabled() -> bool:
    with _lock:
        return bool(_load().get("peak_enabled", False))

def toggle_peak_enabled() -> bool:
    with _lock:
        data = _load()
        data["peak_enabled"] = not bool(data.get("peak_enabled", False))
        _save(data)
        return bool(data["peak_enabled"])

def is_silent_enabled() -> bool:
    with _lock:
        return bool(_load().get("silent_enabled", False))

def toggle_silent_enabled() -> bool:
    with _lock:
        data = _load()
        data["silent_enabled"] = not bool(data.get("silent_enabled", False))
        _save(data)
        return bool(data["silent_enabled"])

def get_silent_window():
    with _lock:
        data = _load()
        return str(data.get("silent_start", "23:00")), str(data.get("silent_end", "07:00"))