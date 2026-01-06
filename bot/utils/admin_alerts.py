from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AdminAlertDestination:
    """
    Куда слать алерты админам/дежурным.

    chat_id — обязательный
    thread_id — опциональный (если чат с темами)
    """
    chat_id: int
    thread_id: Optional[int] = None


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
