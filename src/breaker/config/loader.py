"""Load settings from YAML, then let BREAKER_* environment variables override them."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ENV_PREFIX = "BREAKER_"
CONFIG_PATH_ENV = "BREAKER_CONFIG"
# src/breaker/config/loader.py -> project root is three folders up from this package.
DEFAULT_PATH = Path(__file__).resolve().parents[3] / "config" / "settings.yaml"


class ConfigError(ValueError):
    """Raised when the settings file or an override is missing, misspelled or the wrong type."""


@dataclass(frozen=True)
class Limits:
    """Per-run limits that the rules enforce."""

    max_steps_per_run: int
    budget_per_run_usd: float
    repeat_call_limit: int


@dataclass(frozen=True)
class Pricing:
    """Token prices used to turn token counts into dollars."""

    input_per_1k_tokens_usd: float
    output_per_1k_tokens_usd: float


@dataclass(frozen=True)
class Settings:
    """All settings for one process; frozen so nothing changes them mid-run."""

    limits: Limits
    pricing: Pricing
    rules: dict[str, bool]

    def rule_enabled(self, name: str) -> bool:
        return self.rules.get(name, False)


def load_settings(path: str | Path | None = None, env: dict[str, str] | None = None) -> Settings:
    env = dict(os.environ) if env is None else env
    path = Path(path or env.get(CONFIG_PATH_ENV) or DEFAULT_PATH)
    if not path.is_file():
        raise ConfigError(f"Settings file not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    _apply_env_overrides(raw, env)

    try:
        return Settings(
            limits=Limits(**raw["limits"]),
            pricing=Pricing(**raw["pricing"]),
            rules={name: bool(on) for name, on in raw["rules"].items()},
        )
    except (KeyError, TypeError) as exc:
        raise ConfigError(f"Settings file {path} is missing or has unexpected keys: {exc}") from exc


def _apply_env_overrides(raw: dict[str, Any], env: dict[str, str]) -> None:
    for name, value in env.items():
        if not name.startswith(ENV_PREFIX) or name == CONFIG_PATH_ENV:
            continue
        section, sep, key = name[len(ENV_PREFIX) :].lower().partition("__")
        # Fail loudly on typos: a silently ignored override is worse than a crash.
        if not sep or section not in raw or key not in raw[section]:
            raise ConfigError(f"{name} does not match any setting in the settings file")
        raw[section][key] = _coerce(value, like=raw[section][key], name=name)


def _coerce(value: str, like: Any, name: str) -> Any:
    # Env vars are always text, so convert to the type the YAML file used.
    if isinstance(like, bool):  # check bool before int: bool is a subclass of int
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
        raise ConfigError(f"{name}={value!r} is not a true/false value")
    try:
        if isinstance(like, int):
            return int(value)
        if isinstance(like, float):
            return float(value)
    except ValueError as exc:
        raise ConfigError(f"{name}={value!r} is not a valid {type(like).__name__}") from exc
    return value
