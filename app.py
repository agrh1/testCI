"""
Web-сервис (Flask).

Шаг 12:
- /status показывает ENVIRONMENT и GIT_SHA.

Шаг 13:
- /health = liveness (процесс жив, НЕ проверяем внешние зависимости)
- /ready  = readiness (сервис готов обслуживать запросы)

Существующие контракты проекта:
- "/" должен возвращать 200 и непустой текст (есть тест)
- "/health" уже используется Docker healthcheck'ом (не ломаем)
"""

from __future__ import annotations

import os
from typing import Any

from flask import Flask, jsonify

app = Flask(__name__)


def get_git_sha() -> str:
    return os.getenv("GIT_SHA", "unknown")


def get_environment() -> str:
    # Ожидаемые значения: staging | prod | local
    return os.getenv("ENVIRONMENT", "unknown")


@app.get("/")
def index() -> tuple[str, int]:
    return "testCI service is running", 200


@app.get("/health")
def health() -> tuple[Any, int]:
    """
    Liveness: отвечает на вопрос "процесс жив?".

    Здесь нельзя делать сетевые запросы и проверять внешние зависимости,
    чтобы не устроить рестарт-шторм при сбоях вокруг.
    """
    return jsonify({"status": "ok"}), 200


@app.get("/ready")
def ready() -> tuple[Any, int]:
    """
    Readiness: отвечает на вопрос "сервис готов выполнять работу?".

    Сейчас у web нет обязательных внешних зависимостей (БД/очередь),
    поэтому /ready == ok.

    В будущем сюда добавятся проверки именно обязательных зависимостей
    (например, доступность БД), а /health останется простым.
    """
    return jsonify({"status": "ok"}), 200


@app.get("/status")
def status() -> tuple[Any, int]:
    payload = {
        "status": "ok",
        "environment": get_environment(),
        "git_sha": get_git_sha(),
    }
    return jsonify(payload), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
