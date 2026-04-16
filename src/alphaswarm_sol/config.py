"""Configuration for True VKG."""

from __future__ import annotations

import logging
import os

import structlog
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from env or defaults."""

    model_config = SettingsConfigDict(env_prefix="TRUE_VKG_", env_file=".env", extra="ignore")

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    anthropic_api_key: str | None = None
    log_level: str = "INFO"


def load_settings() -> Settings:
    """Load settings from environment or defaults."""

    return Settings()


def configure_logging(log_level: str | None = None) -> None:
    """Configure structlog + stdlib logging."""

    level_name = (log_level or os.getenv("TRUE_VKG_LOG_LEVEL") or "INFO").upper()
    level_value = logging.getLevelName(level_name)
    if isinstance(level_value, str):
        level_value = logging.INFO
    logging.basicConfig(level=level_value, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level_value),
        cache_logger_on_first_use=True,
    )


# Metrics configuration (Phase 8)
METRICS_CONFIG = {
    "storage_path": ".vrs/metrics",
    "history_retention_days": 90,
    "collection_interval": "daily",
    "alert_on_critical": True,
    "alert_on_warning": False,
}


# Context budget configuration (Phase 7.1.3)
# Per-role token budgets (max tokens per agent type)
CONTEXT_BUDGET_CONFIG = {
    "default_max_tokens": 6000,  # Per CLAUDE.md
    "hard_cap": 8000,            # Absolute maximum per CLAUDE.md
    "role_budgets": {
        "classifier": 2000,
        "attacker": 6000,
        "defender": 5000,
        "verifier": 4000,
        "validator": 3000,
    },
    "pool_budgets": {
        "triage": 2000,
        "investigation": 6000,
        "verification": 4000,
    },
    "stage_fractions": {
        "summary": 0.15,
        "evidence": 0.50,
        "raw": 1.0,
    },
    "enable_progressive_disclosure": True,
    "preserve_evidence_ids": True,
}


def get_budget_for_role(role: str) -> int:
    """Get context budget for a role.

    Args:
        role: Agent role name

    Returns:
        Token budget for the role
    """
    budgets = CONTEXT_BUDGET_CONFIG.get("role_budgets", {})
    default = CONTEXT_BUDGET_CONFIG.get("default_max_tokens", 6000)
    return budgets.get(role, default)


def get_budget_for_pool(pool: str) -> int:
    """Get context budget for a pool.

    Args:
        pool: Pool name

    Returns:
        Token budget for the pool
    """
    budgets = CONTEXT_BUDGET_CONFIG.get("pool_budgets", {})
    default = CONTEXT_BUDGET_CONFIG.get("default_max_tokens", 6000)
    return budgets.get(pool, default)


settings = load_settings()
