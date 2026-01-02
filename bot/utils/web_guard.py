# bot/utils/web_guard.py
"""
"Заслонка" для web-зависимых команд.

Использование:
- В хендлере web-зависимой команды делаем:
    ok = await guard.require_web(message)
    if not ok:
        return
  и дальше выполняем команду.

Важно:
- /status НЕ должен блокироваться (он как раз показывает состояние)
- bot НЕ падает при проблемах web
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from aiogram import types

from .web_client import WebCheckResult, WebClient


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    reason: str
    health: WebCheckResult
    ready: WebCheckResult


class WebGuard:
    def __init__(self, client: WebClient) -> None:
        self.client = client

    async def decide(self) -> GuardDecision:
        health, ready = await self.client.check_health_ready()

        if not health.ok:
            return GuardDecision(
                allowed=False,
                reason="WEB_UNAVAILABLE",
                health=health,
                ready=ready,
            )

        if not ready.ok:
            return GuardDecision(
                allowed=False,
                reason="WEB_NOT_READY",
                health=health,
                ready=ready,
            )

        return GuardDecision(
            allowed=True,
            reason="OK",
            health=health,
            ready=ready,
        )

    async def require_web(self, message: types.Message, friendly_name: Optional[str] = None) -> bool:
        """
        Возвращает True если можно продолжать.
        Если нельзя — отправляет пользователю понятное сообщение и возвращает False.
        """
        d = await self.decide()

        if d.allowed:
            return True

        # Сообщения пользователю — специально "не технические"
        if d.reason == "WEB_UNAVAILABLE":
            text = "Сервис временно недоступен (web не отвечает). Попробуйте позже."
        else:
            # WEB_NOT_READY
            text = "Сервис временно недоступен (web ещё не готов). Попробуйте позже."

        if friendly_name:
            text = f"Команда «{friendly_name}» сейчас недоступна. {text}"

        await message.answer(text)

        # Логировать лучше там, где у тебя уже настроен logger.
        # Но даже без логгера — поведение корректное.
        return False
