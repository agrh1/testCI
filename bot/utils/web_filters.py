# bot/utils/web_filters.py
"""
Фильтры aiogram v3 для web-зависимых команд.

Идея:
- web-зависимые хендлеры регистрируем с WebReadyFilter(...)
- фильтр сам проверяет web.health/web.ready через WebGuard
- если web не готов — отвечает пользователю и НЕ пускает в хендлер
"""

from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import Message

from .web_guard import WebGuard


class WebReadyFilter(BaseFilter):
    """
    Фильтр для web-зависимых команд.

    Пример:
        dp.message.register(cmd_needs_web, Command("needs_web"), WebReadyFilter("/needs_web"))
    """

    def __init__(self, friendly_name: str | None = None) -> None:
        self.friendly_name = friendly_name

    async def __call__(self, message: Message, web_guard: WebGuard) -> bool:
        # web_guard будет подставлен aiogram'ом из dp.workflow_data["web_guard"]
        return await web_guard.require_web(message, friendly_name=self.friendly_name)
