"""
Пакет bot.

Тесты (legacy/контракт проекта) ожидают, что из `bot` экспортируются:
- ping_reply_text()
- HEALTH_URL (формируется из WEB_BASE_URL и заканчивается на /health)
При появлении пакета bot/ импорт `bot` стал ссылаться на пакет, поэтому
мы поддерживаем обратную совместимость здесь.
"""

from __future__ import annotations

import os


def _normalize_base_url(url: str) -> str:
    """
    Убираем завершающий '/', чтобы потом корректно склеивать пути:
    "http://web:8000" и "http://web:8000/" -> "http://web:8000"
    """
    return url.rstrip("/")


# Базовый URL web-сервиса берём из окружения (как и раньше).
WEB_BASE_URL: str = os.getenv("WEB_BASE_URL", "http://web:8000")
WEB_BASE_URL = _normalize_base_url(WEB_BASE_URL)

# Legacy-константа: тесты ожидают именно HEALTH_URL
HEALTH_URL: str = f"{WEB_BASE_URL}/health"


def ping_reply_text() -> str:
    """
    Текст ответа на команду /ping.

    Сделано максимально стабильным для тестов.
    """
    return "pong ✅"


__all__ = [
    "WEB_BASE_URL",
    "HEALTH_URL",
    "ping_reply_text",
]
