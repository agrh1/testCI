"""
Работа с Postgres для хранения конфигурации бота.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional, Tuple

from sqlalchemy import Column, Integer, Text, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class BotConfig(Base):
    __tablename__ = "bot_config"

    id = Column(Integer, primary_key=True)
    version = Column(Integer, nullable=False)
    config_json = Column(Text, nullable=False)


def _database_url() -> str:
    return os.getenv("DATABASE_URL", "").strip()


def db_enabled() -> bool:
    return bool(_database_url())


def create_db_engine() -> Engine:
    return create_engine(_database_url(), pool_pre_ping=True, future=True)


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine, future=True)
    with Session() as s:
        row = s.get(BotConfig, 1)
        if row is None:
            s.add(
                BotConfig(
                    id=1,
                    version=1,
                    config_json=json.dumps(
                        {
                            "routing": {"rules": [], "default_dest": {}},
                            "escalation": {"enabled": False},
                        },
                        ensure_ascii=False,
                    ),
                )
            )
            s.commit()


def read_config(engine: Engine) -> Tuple[Optional[dict[str, Any]], Optional[str]]:
    try:
        Session = sessionmaker(bind=engine, future=True)
        with Session() as s:
            row = s.get(BotConfig, 1)
            if not row:
                return None, "config not found"

            data = json.loads(row.config_json)
            data["version"] = row.version
            return data, None
    except Exception as e:
        return None, str(e)


def write_config(engine: Engine, cfg: dict[str, Any]) -> int:
    Session = sessionmaker(bind=engine, future=True)
    with Session() as s:
        row = s.get(BotConfig, 1)
        if not row:
            raise RuntimeError("config row missing")

        row.version += 1
        row.config_json = json.dumps(cfg, ensure_ascii=False)
        s.commit()
        return row.version
