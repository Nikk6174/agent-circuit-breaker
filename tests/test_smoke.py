"""Smoke tests: the package imports and the real settings file loads."""

import pytest

import breaker
from breaker.config import ConfigError, load_settings


def test_package_imports():
    assert breaker.__doc__


def test_settings_file_loads():
    settings = load_settings(env={})
    assert settings.limits.max_steps_per_run > 0
    assert settings.rule_enabled("budget")


def test_env_overrides_yaml():
    settings = load_settings(
        env={"BREAKER_LIMITS__MAX_STEPS_PER_RUN": "7", "BREAKER_RULES__BUDGET": "false"}
    )
    assert settings.limits.max_steps_per_run == 7
    assert not settings.rule_enabled("budget")


def test_misspelled_override_is_rejected():
    with pytest.raises(ConfigError):
        load_settings(env={"BREAKER_LIMITS__MAX_STEP": "7"})
