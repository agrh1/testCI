"""
Хранилище фильтров eventlog в Postgres.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Iterable

import psycopg2
import psycopg2.extras


@dataclass(frozen=True)
class EventlogFilter:
    filter_id: int
    field: str
    pattern: str
    match_type: str
    enabled: bool
    hits: int


class EventlogFilterStore:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self):
        return psycopg2.connect(self._database_url)

    async def init_schema(self) -> None:
        await asyncio.to_thread(self._init_schema_sync)

    async def list_enabled(self) -> list[EventlogFilter]:
        return await asyncio.to_thread(self._list_enabled_sync)

    async def increment_hits(self, filter_ids: Iterable[int]) -> None:
        await asyncio.to_thread(self._increment_hits_sync, list(filter_ids))

    def _init_schema_sync(self) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS eventlog_filters (
                    id SERIAL PRIMARY KEY,
                    enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    match_type TEXT NOT NULL DEFAULT 'contains',
                    field TEXT NOT NULL,
                    pattern TEXT NOT NULL,
                    comment TEXT,
                    hits BIGINT NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute("ALTER TABLE eventlog_filters ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT TRUE")
            cur.execute("ALTER TABLE eventlog_filters ADD COLUMN IF NOT EXISTS match_type TEXT NOT NULL DEFAULT 'contains'")
            cur.execute("ALTER TABLE eventlog_filters ADD COLUMN IF NOT EXISTS field TEXT NOT NULL DEFAULT ''")
            cur.execute("ALTER TABLE eventlog_filters ADD COLUMN IF NOT EXISTS pattern TEXT NOT NULL DEFAULT ''")
            cur.execute("ALTER TABLE eventlog_filters ADD COLUMN IF NOT EXISTS comment TEXT")
            cur.execute("ALTER TABLE eventlog_filters ADD COLUMN IF NOT EXISTS hits BIGINT NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE eventlog_filters ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now()")
            cur.execute("ALTER TABLE eventlog_filters ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now()")

    def _row_to_filter(self, row) -> EventlogFilter:
        return EventlogFilter(
            filter_id=int(row["id"]),
            field=str(row["field"] or ""),
            pattern=str(row["pattern"] or ""),
            match_type=str(row["match_type"] or "contains"),
            enabled=bool(row["enabled"]),
            hits=int(row["hits"] or 0),
        )

    def _list_enabled_sync(self) -> list[EventlogFilter]:
        with self._connect() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                SELECT id, field, pattern, match_type, enabled, hits
                FROM eventlog_filters
                WHERE enabled = TRUE
                ORDER BY id ASC
                """
            )
            rows = cur.fetchall()
            return [self._row_to_filter(r) for r in rows]

    def _increment_hits_sync(self, filter_ids: list[int]) -> None:
        if not filter_ids:
            return
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE eventlog_filters
                SET hits = hits + 1, updated_at = now()
                WHERE id = ANY(%s)
                """,
                (filter_ids,),
            )


def match_eventlog_filter(flt: EventlogFilter, message: dict[str, str]) -> bool:
    """
    Проверяет, сработал ли фильтр.
    match_type поддерживает 'contains' и 'regex'.
    """
    match_type = flt.match_type.strip().lower()
    raw_field = flt.field.strip()
    field = raw_field.lower()
    pattern = flt.pattern
    if not pattern:
        return False
    target = _resolve_target(field, raw_field, message)
    if match_type == "contains":
        return pattern in target
    if match_type == "regex":
        try:
            return re.search(pattern, target) is not None
        except re.error:
            return False
    return False


def _resolve_target(field: str, raw_field: str, message: dict[str, str]) -> str:
    mapping = {
        "description": "Описание",
        "type": "Тип",
        "name": "Название",
        "date": "Дата",
    }
    if field in {"any", "*"}:
        return " ".join(v for v in message.values() if isinstance(v, str))
    if field in mapping:
        return message.get(mapping[field], "")
    if raw_field in message:
        return message.get(raw_field, "")
    return message.get(field, "")
