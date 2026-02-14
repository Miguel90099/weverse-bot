# utils/premium.py
import json
import os
from threading import Lock

_PREMIUM_FILE = os.path.join(os.path.dirname(__file__), "premium.json")
_lock = Lock()

_DEFAULT = {
    "premium_user_ids": []
}

def _load():
    if not os.path.exists(_PREMIUM_FILE):
        return dict(_DEFAULT)
    try:
        with open(_PREMIUM_FILE, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        merged = dict(_DEFAULT)
        merged.update(data)
        # normaliza a int
        merged["premium_user_ids"] = [int(x) for x in merged.get("premium_user_ids", [])]
        return merged
    except Exception:
        return dict(_DEFAULT)

def _save(data: dict):
    os.makedirs(os.path.dirname(_PREMIUM_FILE), exist_ok=True)
    with open(_PREMIUM_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_premium(user_id: int) -> bool:
    with _lock:
        data = _load()
        return int(user_id) in set(data.get("premium_user_ids", []))

def add_premium(user_id: int) -> bool:
    """Devuelve True si lo agregó, False si ya estaba."""
    with _lock:
        data = _load()
        ids = set(data.get("premium_user_ids", []))
        before = len(ids)
        ids.add(int(user_id))
        data["premium_user_ids"] = sorted(ids)
        _save(data)
        return len(ids) != before

def remove_premium(user_id: int) -> bool:
    """Devuelve True si lo quitó, False si no existía."""
    with _lock:
        data = _load()
        ids = set(data.get("premium_user_ids", []))
        if int(user_id) not in ids:
            return False
        ids.remove(int(user_id))
        data["premium_user_ids"] = sorted(ids)
        _save(data)
        return True

def list_premium() -> list[int]:
    with _lock:
        return _load().get("premium_user_ids", [])