"""
Telegram-бот (aiogram v3).

Шаг 12:
- /status показывает ENVIRONMENT и GIT_SHA.

Шаг 13:
- /status дополнительно показывает, доступен ли web (/health).
  Это НЕ влияет на работоспособность бота: bot и web условно зависимые.

Контракты проекта:
- TELEGRAM_BOT_TOKEN — основной env ключ токена
- ping_reply_text() возвращает "pong ✅"
- HEALTH_URL — атрибут модуля, строится из WEB_BASE_URL и оканчивается на /health
"""

from __future__ import annotations

import asyncio
import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message


def _build_health_url(web_base_url: str) -> str:
    base = (web_base_url or "").strip()
    if not base:
        # Если WEB_BASE_URL не задан, оставляем относительный путь.
        return "/health"
    return base.rstrip("/") + "/health"


WEB_BASE_URL = os.getenv("WEB_BASE_URL", "")
HEALTH_URL = _build_health_url(WEB_BASE_URL)


# -----------------------------
# Pure-функции для unit-тестов
# -----------------------------

def ping_reply_text() -> str:
    return "pong ✅"


def start_reply_text() -> str:
    return (
        "Привет! Я бот сервиса.\n"
        "Команды:\n"
        "/ping — проверка связи\n"
        "/status — окружение, версия и доступность web\n"
    )


def unknown_reply_text() -> str:
    return "Не понял команду. Используй /start."


@dataclass(frozen=True)
class AppInfo:
    environment: str
    git_sha: str


def get_app_info() -> AppInfo:
    return AppInfo(
        environment=os.getenv("ENVIRONMENT", "unknown"),
        git_sha=os.getenv("GIT_SHA", "unknown"),
    )


@dataclass(frozen=True)
class WebCheck:
    """
    Результат проверки web.

    ok:
      - True  -> web доступен и ответил корректно
      - False -> web недоступен или ответ некорректный

    http_status: HTTP статус, если удалось получить
    error: текст ошибки, если была
    """
    url: str
    ok: bool
    http_status: int | None = None
    error: str | None = None


def format_status_text(app_info: AppInfo, web_check: WebCheck) -> str:
    lines = [
        "Статус: ok",
        f"ENVIRONMENT: {app_info.environment}",
        f"GIT_SHA: {app_info.git_sha}",
        "",
        "WEB:",
        f"- url: {web_check.url}",
        f"- reachable: {'yes' if web_check.ok else 'no'}",
    ]
    if web_check.http_status is not None:
        lines.append(f"- http_status: {web_check.http_status}")
    if web_check.error:
        lines.append(f"- error: {web_check.error}")
    return "\n".join(lines)


def _sync_fetch_json(url: str, timeout_seconds: float) -> tuple[int, Any]:
    """
    Синхронный HTTP GET, вынесен в отдельную функцию.
    Будем вызывать через asyncio.to_thread, чтобы не блокировать event loop.
    """
    req = urllib.request.Request(url, headers={"User-Agent": "testci-bot/1.0"})
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        status = int(resp.status)
        body = resp.read().decode("utf-8")
        return status, json.loads(body)


async def check_web_health(timeout_seconds: float = 1.5) -> WebCheck:
    """
    Проверяет web по HEALTH_URL.

    Важно:
    - не бросает исключения наружу
    - таймаут маленький
    - если HEALTH_URL относительный ("/health"), то сеть не проверяем
      (иначе это зависит от окружения запуска).
    """
    url = HEALTH_URL

    # Если нет WEB_BASE_URL, то HEALTH_URL будет относительным.
    # В этом случае не делаем сетевой вызов и честно показываем, что URL не настроен.
    if url.startswith("/"):
        return WebCheck(url=url, ok=False, error="WEB_BASE_URL не задан (HEALTH_URL относительный)")

    try:
        http_status, data = await asyncio.to_thread(_sync_fetch_json, url, timeout_seconds)
        # ожидаем {"status":"ok"} как контракт /health
        ok = isinstance(data, dict) and data.get("status") == "ok" and http_status == 200
        return WebCheck(url=url, ok=ok, http_status=http_status, error=None if ok else "Некорректный ответ /health")
    except Exception as e:
        return WebCheck(url=url, ok=False, error=str(e))


def get_telegram_token() -> str:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Не задана переменная окружения TELEGRAM_BOT_TOKEN")
    return token


# -----------------------------
# Aiogram wiring
# -----------------------------

dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(start_reply_text())


@dp.message(Command("ping"))
async def cmd_ping(message: Message) -> None:
    await message.answer(ping_reply_text())


@dp.message(Command("status"))
async def cmd_status(message: Message) -> None:
    info = get_app_info()
    web_check = await check_web_health()
    await message.answer(format_status_text(info, web_check))


@dp.message(F.text)
async def fallback(message: Message) -> None:
    await message.answer(unknown_reply_text())


async def main() -> None:
    bot = Bot(token=get_telegram_token())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
