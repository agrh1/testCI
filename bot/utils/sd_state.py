"""Утилиты для нормализации данных ServiceDesk и вычисления снэпшотов."""

# bot/utils/sd_state.py
from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Optional


def _to_int(value: object) -> Optional[int]:
    try:
        return int(value)
    except Exception:
        return None


def normalize_tasks_for_message(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Нормализация для отображения пользователю:
    - сортируем по Id
    - берём Id, Name, Creator (строка) и ссылку на заявку
    """
    base_url = (os.getenv("SERVICEDESK_BASE_URL", "").strip())
    normalized: list[dict[str, Any]] = []
    for t in items:
        tid = _to_int(t.get("Id"))
        if tid is None or tid <= 0:
            continue
        normalized.append(
            {
                "Id": tid,
                "Name": str(t.get("Name", "")),
                "Creator": str(t.get("Creator", "")),
                "Url": f"{base_url}/task/view/{tid}",
            }
        )

    return sorted(normalized, key=lambda x: x["Id"])


def make_ids_snapshot_hash(items: list[dict[str, Any]]) -> tuple[str, list[int]]:
    """
    Снэпшот ТОЛЬКО по составу очереди:
    - берём только Id
    - сортируем
    - считаем sha256

    Возвращаем:
    - hash
    - ids (отсортированный список) — полезно для диагностики
    """
    ids_set: set[int] = set()
    for t in items:
        tid = _to_int(t.get("Id"))
        if tid is None or tid <= 0:
            continue
        ids_set.add(tid)

    ids = sorted(ids_set)
    payload = json.dumps(ids, ensure_ascii=False, separators=(",", ":"))
    h = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return h, ids
