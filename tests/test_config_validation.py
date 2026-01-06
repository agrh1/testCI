"""
Unit-тесты валидации конфигурации web.
"""

from __future__ import annotations

import pytest

from web.config_validation import ConfigValidationError, validate_config


def test_validate_config_ok() -> None:
    cfg = {
        "routing": {
            "rules": [
                {"dest": {"chat_id": 1, "thread_id": None}, "enabled": True},
            ],
            "default_dest": {"chat_id": 2, "thread_id": None},
        },
        "escalation": {"enabled": False},
    }
    validate_config(cfg)


def test_validate_config_missing_fields() -> None:
    with pytest.raises(ConfigValidationError):
        validate_config({})


def test_validate_config_invalid_dest() -> None:
    cfg = {
        "routing": {"rules": [{"dest": {"chat_id": "x"}}], "default_dest": {}},
        "escalation": {"enabled": False},
    }
    with pytest.raises(ConfigValidationError):
        validate_config(cfg)
