"""
web/db.py — работа с Postgres для хранения конфигурации бота.

Зачем модуль:
- На шаге 26 уходим от конфигов в .env (ROUTES_RULES/ESCALATION_*) и переносим правила в Postgres.
- Web-сервис становится "источником правды" и отдаёт конфиг по HTTP (бот БД не трогает напрямую).

Подход:
- Без Alembic (пока), чтобы проще накатывать начинающему специалисту.
- Таблица создаётся автоматически при старте web.
- В дальнейшем можно заменить на полноценные миграции.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional, Tuple

from sqlalchemy import Column, Integer, Text, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class BotConfig(Base):
    """
    Одна строка с конфигурацией бота.

    Идея:
    - хранить всё одним JSON (routing + escalation),
    - версионировать через version (монотонно растёт),
    - обновлять атомарно (UPDATE одной строки).
    """
    __tablename__ = "bot_config"

    id = Column(Integer, primary_key=True)  # всегда 1
    version = Column(Integer, nullable=False, default=1)
    config_json = Column(Text, nullable=False)  # JSON строкой


def _database_url() -> str:
    return os.getenv("DATABASE_URL", "").strip()


def db_enabled() -> bool:
    return bool(_database_url())


def create_db_engine() -> Engine:
    # pool_pre_ping помогает переживать "протухшие" коннекты после сетевых глитчей/рестартов
    return create_engine(_database_url(), pool_pre_ping=True, future=True)


def init_db(engine: Engine) -> None:
    """
    Создаём таблицу и дефолтную запись (id=1), если её нет.

    Важно:
    - вызываем безопасно: повторный вызов не ломает систему,
    - делаем "сид" пустым конфигом, чтобы /config всегда мог работать.
    """
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    with Session() as session:
        row = session.get(BotConfig, 1)
        if row is None:
            default_config = {
                "routing": {
                    "rules": [],
                    "default_dest": {"chat_id": None, "thread_id": None},
                    "service_id_field": os.getenv("ROUTES_SERVICE_ID_FIELD", "ServiceId"),
                    "customer_id_field": os.getenv("ROUTES_CUSTOMER_ID_FIELD", "CustomerId"),
                },
                "escalation": {
                    "enabled": False,
                    "after_s": 600,
                    "dest": {"chat_id": None, "thread_id": None},
                    "mention": "@duty_engineer",
                    "service_id_field": os.getenv("ESCALATION_SERVICE_ID_FIELD", os.getenv("ROUTES_SERVICE_ID_FIELD", "ServiceId")),
                    "customer_id_field": os.getenv("ESCALATION_CUSTOMER_ID_FIELD", os.getenv("ROUTES_CUSTOMER_ID_FIELD", "CustomerId")),
                    "filter": {},
                },
            }
            session.add(BotConfig(id=1, version=1, config_json=json.dumps(default_config, ensure_ascii=False)))
            session.commit()


def read_config(engine: Engine) -> Tuple[Optional[dict[str, Any]], Optional[str]]:
    """
    Читаем конфиг из БД.

    Возвращает:
    - (config_dict, None) при успехе
    - (None, "описание ошибки") при проблеме
    """
    try:
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
        with Session() as session:
            row = session.get(BotConfig, 1)
            if row is None:
                return None, "bot_config row id=1 not found"
            try:
                data = json.loads(row.config_json)
            except Exception as e:
                return None, f"config_json parse error: {e}"
            data["version"] = int(row.version)
            return data, None
    except SQLAlchemyError as e:
        return None, f"db error: {e}"
