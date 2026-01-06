"""
Простой diff для JSON-конфигов.

Возвращает список изменений с путём и значениями до/после.
"""

from __future__ import annotations

from typing import Any


def diff_dicts(a: Any, b: Any, path: str = "") -> list[dict[str, Any]]:
    """
    Рекурсивный diff для dict/list/scalar.
    """
    changes: list[dict[str, Any]] = []

    if isinstance(a, dict) and isinstance(b, dict):
        keys = sorted(set(a.keys()) | set(b.keys()))
        for k in keys:
            new_path = f"{path}.{k}" if path else str(k)
            changes.extend(diff_dicts(a.get(k), b.get(k), new_path))
        return changes

    if isinstance(a, list) and isinstance(b, list):
        if a == b:
            return changes
        changes.append({"path": path, "from": a, "to": b})
        return changes

    if a != b:
        changes.append({"path": path, "from": a, "to": b})

    return changes
