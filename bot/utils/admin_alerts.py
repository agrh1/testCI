"""
Алерты для админов/дежурных.

Содержит:
- парсинг destination из env;
- сборку текста алерта "нет destination".
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from bot.utils.env_helpers import EnvDestination, parse_dest_from_env


@dataclass(frozen=True)
class AdminAlertDestination:
    """
    Куда слать алерты админам/дежурным.

    chat_id — обязательный
    thread_id — опциональный (если чат с темами)
    """
    chat_id: int
    thread_id: Optional[int] = None


def parse_admin_alert_dest_from_env() -> Optional[AdminAlertDestination]:
    """
    Приоритет:
    1) ADMIN_ALERT_CHAT_ID / ADMIN_ALERT_THREAD_ID
    2) ALERT_CHAT_ID / ALERT_THREAD_ID (fallback, если используешь общий алерт-канал)
    """
    # Сначала пробуем отдельные переменные для admin-алертов.
    dest = parse_dest_from_env("ADMIN_ALERT")
    if dest is None:
        # Иначе используем общий алерт-канал (если задан).
        dest = parse_dest_from_env("ALERT")
        if dest is None:
            return None

    return _convert_env_dest(dest)


def _convert_env_dest(dest: EnvDestination) -> AdminAlertDestination:
    # Явно конвертируем тип: AdminAlertDestination локален для этого модуля.
    return AdminAlertDestination(chat_id=dest.chat_id, thread_id=dest.thread_id)


def fmt_ts(ts: Optional[float]) -> str:
    if ts is None:
        return "—"
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


def build_no_destination_alert_text(
    *,
    ticket: Optional[dict],
    rules_count: int,
    default_dest_present: bool,
    service_id_field: str,
    customer_id_field: str,
    config_version: Optional[int] = None,
    config_source: Optional[str] = None,
) -> str:
    """
    Текст алерта для ситуации "тикет пришёл, а destination не найден".

    Важно:
    - Не делаем слишком много данных (чтобы не утекало лишнее в админ-чат),
      но даём достаточно для диагностики.
    """
    tid = ticket.get("Id") if isinstance(ticket, dict) else None
    name = ticket.get("Name") if isinstance(ticket, dict) else None
    sid = ticket.get(service_id_field) if isinstance(ticket, dict) else None
    cid = ticket.get(customer_id_field) if isinstance(ticket, dict) else None

    lines = [
        "⚠️ Ticket without destination",
        "",
        "Ticket:",
        f"- id: {tid if tid is not None else '—'}",
        f"- name: {name if name is not None else '—'}",
        f"- {service_id_field}: {sid if sid is not None else '—'}",
        f"- {customer_id_field}: {cid if cid is not None else '—'}",
        "",
        "Routing:",
        f"- rules_count: {rules_count}",
        f"- default_dest_present: {'yes' if default_dest_present else 'no'}",
    ]

    if config_version is not None:
        lines.append(f"- config_version: {config_version}")
    if config_source:
        lines.append(f"- config_source: {config_source}")

    lines += [
        "",
        "Action: проверь routing-конфиг (rules/default_dest).",
    ]
    return "\n".join(lines)


def build_web_degraded_alert_text(*, health_ok: bool, ready_ok: bool, health_status: object, ready_status: object) -> str:
    """
    Алерт при деградации web (/health или /ready).
    """
    lines = [
        "⚠️ Web деградировал",
        "",
        f"- health: {'ok' if health_ok else 'fail'} (status={health_status})",
        f"- ready: {'ok' if ready_ok else 'fail'} (status={ready_status})",
        "",
        "Action: проверь web /health и /ready.",
    ]
    return "\n".join(lines)


def build_redis_degraded_alert_text(*, error: str, last_ok_ts: Optional[float]) -> str:
    """
    Алерт при деградации Redis/StateStore.
    """
    lines = [
        "⚠️ Redis деградировал",
        "",
        f"- last_ok: {fmt_ts(last_ok_ts)}",
        f"- error: {error or '—'}",
        "",
        "Action: проверь Redis и сеть.",
    ]
    return "\n".join(lines)


def build_rollbacks_alert_text(*, count: int, window_s: int, last_at: Optional[str]) -> str:
    """
    Алерт при частых rollback конфига.
    """
    lines = [
        "⚠️ Частые rollback конфигурации",
        "",
        f"- window_s: {window_s}",
        f"- count: {count}",
        f"- last_rollback_at: {last_at or '—'}",
        "",
        "Action: проверь /config/history и причины откатов.",
    ]
    return "\n".join(lines)
