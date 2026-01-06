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
    # Prefer dedicated admin alert envs.
    dest = parse_dest_from_env("ADMIN_ALERT")
    if dest is None:
        # Fallback to the general ALERT destination, if configured.
        dest = parse_dest_from_env("ALERT")
        if dest is None:
            return None

    return _convert_env_dest(dest)


def _convert_env_dest(dest: EnvDestination) -> AdminAlertDestination:
    # Keep types explicit; AdminAlertDestination is local to this module.
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
