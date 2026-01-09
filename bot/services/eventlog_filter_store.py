"""
Хранилище фильтров eventlog в Postgres.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Iterable

import psycopg2
import psycopg2.extras


@dataclass(frozen=True)
class EventlogFilter:
    filter_id: int
    field: str
    pattern: str
    match_mode: str
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
                    field TEXT NOT NULL,
                    pattern TEXT NOT NULL,
                    match_mode TEXT NOT NULL DEFAULT 'contains',
                    enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    hits BIGINT NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )

    def _row_to_filter(self, row) -> EventlogFilter:
        return EventlogFilter(
            filter_id=int(row["id"]),
            field=str(row["field"] or ""),
            pattern=str(row["pattern"] or ""),
            match_mode=str(row["match_mode"] or "contains"),
            enabled=bool(row["enabled"]),
            hits=int(row["hits"] or 0),
        )

    def _list_enabled_sync(self) -> list[EventlogFilter]:
        with self._connect() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                SELECT id, field, pattern, match_mode, enabled, hits
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
    match_mode поддерживает только 'contains' (как в старом боте).
    """
    if flt.match_mode != "contains":
        return False
    field = flt.field.strip().lower()
    pattern = flt.pattern
    if not pattern:
        return False

    if field in {"any", "*"}:
        target = " ".join(v for v in message.values() if isinstance(v, str))
    else:
        target = message.get(flt.field, "")

    return pattern in target

