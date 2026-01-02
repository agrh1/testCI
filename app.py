from __future__ import annotations

import logging
import os
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any

from flask import Flask, g, jsonify, request

app = Flask(__name__)

ALLOWED_ENVIRONMENTS = {"staging", "prod", "local"}

REQUIRED_ENV_VARS = [
    "SERVICEDESK_BASE_URL",
    "SERVICEDESK_API_TOKEN",
]


def get_git_sha() -> str:
    return os.getenv("GIT_SHA", "unknown")


def get_environment() -> str:
    return os.getenv("ENVIRONMENT", "unknown")


def is_strict_readiness() -> bool:
    return os.getenv("STRICT_READINESS", "0").strip() == "1"


# -----------------------------
# Logging
# -----------------------------

class ContextAdapter(logging.LoggerAdapter):
    """Добавляет в каждый лог ENVIRONMENT и GIT_SHA."""
    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        extra = kwargs.get("extra", {})
        extra.setdefault("environment", get_environment())
        extra.setdefault("git_sha", get_git_sha())
        kwargs["extra"] = extra
        return msg, kwargs


def setup_logging() -> ContextAdapter:
    """
    Настраивает логирование в формате key=value (удобно для grep и будущего парсинга).
    Не используем JSON, чтобы не усложнять сейчас, но формат уже “структурный”.
    """
    logger = logging.getLogger("testci.web")
    if logger.handlers:
        return ContextAdapter(logger, {})  # уже настроено (например, при reload)

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()

    formatter = logging.Formatter(
        fmt=(
            "ts=%(asctime)s level=%(levelname)s service=web "
            "env=%(environment)s sha=%(git_sha)s "
            "msg=%(message)s"
        )
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    return ContextAdapter(logger, {})


log = setup_logging()


def _get_request_id() -> str:
    rid = request.headers.get("X-Request-ID")
    if rid and rid.strip():
        return rid.strip()
    return uuid.uuid4().hex


@app.before_request
def before_request() -> None:
    """
    Перед запросом:
    - генерим request_id
    - запоминаем start_time
    """
    g.request_id = _get_request_id()
    g.start_time = time.perf_counter()


@app.after_request
def after_request(response: Any) -> Any:
    """
    После запроса:
    - добавляем X-Request-ID
    - пишем одну строку access log
    """
    try:
        duration_ms = int((time.perf_counter() - g.start_time) * 1000)
    except Exception:
        duration_ms = -1

    response.headers["X-Request-ID"] = getattr(g, "request_id", "unknown")

    log.info(
        "request method=%s path=%s status=%s duration_ms=%s request_id=%s remote=%s",
        request.method,
        request.path,
        getattr(response, "status_code", "unknown"),
        duration_ms,
        getattr(g, "request_id", "unknown"),
        request.headers.get("X-Forwarded-For", request.remote_addr),
    )
    return response


# -----------------------------
# Readiness checks
# -----------------------------

@dataclass(frozen=True)
class ReadyCheck:
    name: str
    ok: bool
    detail: str


def _missing_required_env() -> list[str]:
    missing: list[str] = []
    for key in REQUIRED_ENV_VARS:
        value = os.getenv(key)
        if value is None or value.strip() == "":
            missing.append(key)
    return missing


def _check_environment(strict: bool) -> ReadyCheck:
    env = get_environment()

    if strict:
        ok = env in ALLOWED_ENVIRONMENTS
        detail = (
            f"ENVIRONMENT={env} (ожидается одно из: {', '.join(sorted(ALLOWED_ENVIRONMENTS))})"
            if not ok
            else f"ENVIRONMENT={env}"
        )
        return ReadyCheck(name="env.environment", ok=ok, detail=detail)

    if env not in ALLOWED_ENVIRONMENTS:
        return ReadyCheck(
            name="env.environment",
            ok=True,
            detail=(
                f"ENVIRONMENT={env} (предупреждение: рекомендуется одно из "
                f"{', '.join(sorted(ALLOWED_ENVIRONMENTS))}; строгий режим включается STRICT_READINESS=1)"
            ),
        )
    return ReadyCheck(name="env.environment", ok=True, detail=f"ENVIRONMENT={env}")


def _check_required_env(strict: bool) -> ReadyCheck:
    missing = _missing_required_env()

    if strict:
        ok = len(missing) == 0
        detail = "Все обязательные переменные заданы" if ok else f"Не заданы: {', '.join(missing)}"
        return ReadyCheck(name="config.required_env", ok=ok, detail=detail)

    if missing:
        return ReadyCheck(
            name="config.required_env",
            ok=True,
            detail=(
                f"Предупреждение: не заданы {', '.join(missing)} "
                f"(в строгом режиме STRICT_READINESS=1 это будет not ready)"
            ),
        )
    return ReadyCheck(name="config.required_env", ok=True, detail="Все обязательные переменные заданы")


def build_readiness_checks() -> list[ReadyCheck]:
    strict = is_strict_readiness()
    return [
        _check_environment(strict),
        _check_required_env(strict),
    ]


# -----------------------------
# Routes
# -----------------------------

@app.get("/")
def index() -> tuple[str, int]:
    return "testCI service is running", 200


@app.get("/health")
def health() -> tuple[Any, int]:
    return jsonify({"status": "ok"}), 200


@app.get("/ready")
def ready() -> tuple[Any, int]:
    checks = build_readiness_checks()
    all_ok = all(c.ok for c in checks)

    payload = {
        "status": "ok" if all_ok else "not_ready",
        "ready": all_ok,
        "strict": is_strict_readiness(),
        "checks": [asdict(c) for c in checks],
    }
    return jsonify(payload), 200 if all_ok else 503


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
