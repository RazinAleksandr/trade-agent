import argparse
import json
import os

from lib.config import Config, load_config
from lib.logging_setup import get_logger


def test_config_defaults(monkeypatch):
    """load_config() without args returns correct defaults when env is clean."""
    # Clear all config-related env vars to test pure defaults
    for env_var in [
        "PAPER_TRADING", "MIN_VOLUME_24H", "MIN_LIQUIDITY",
        "MAX_MARKETS_PER_CYCLE", "MIN_EDGE_THRESHOLD", "KELLY_FRACTION",
        "MAX_POSITION_SIZE_USDC", "MAX_TOTAL_EXPOSURE_USDC", "DB_PATH",
        "LOG_LEVEL", "LOG_FILE", "POLYMARKET_HOST", "GAMMA_API_URL",
        "CHAIN_ID", "PRIVATE_KEY",
    ]:
        monkeypatch.delenv(env_var, raising=False)

    config = load_config()
    assert config.paper_trading is True
    assert config.kelly_fraction == 0.25
    assert config.min_edge_threshold == 0.10
    assert config.max_position_size_usdc == 50.0
    assert config.polymarket_host == "https://clob.polymarket.com"
    assert config.gamma_api_url == "https://gamma-api.polymarket.com"
    assert config.chain_id == 137
    assert config.db_path == "trading.db"
    assert config.log_level == "INFO"
    assert config.log_file == "trading.log"
    assert config.max_total_exposure_usdc == 200.0
    assert config.min_volume_24h == 1000.0
    assert config.min_liquidity == 500.0
    assert config.max_markets_per_cycle == 10
    assert config.private_key == ""


def test_config_env_override(monkeypatch):
    """Environment variables override defaults."""
    monkeypatch.setenv("KELLY_FRACTION", "0.5")
    config = load_config()
    assert config.kelly_fraction == 0.5


def test_config_cli_override():
    """CLI args (argparse Namespace) override defaults."""
    args = argparse.Namespace(kelly_fraction=0.75)
    config = load_config(args)
    assert config.kelly_fraction == 0.75


def test_config_cli_overrides_env(monkeypatch):
    """CLI args take precedence over environment variables."""
    monkeypatch.setenv("KELLY_FRACTION", "0.5")
    args = argparse.Namespace(kelly_fraction=0.75)
    config = load_config(args)
    assert config.kelly_fraction == 0.75


def test_logging_dual_output(test_config):
    """Logger writes human-readable to stderr and JSON to file."""
    # Use a unique logger name to avoid handler duplication across tests
    logger = get_logger("test_dual_output", test_config)
    logger.info("Test log message")

    # Verify the log file was created and contains JSON
    assert os.path.exists(test_config.log_file)
    with open(test_config.log_file) as f:
        content = f.read().strip()
    assert content  # not empty

    log_entry = json.loads(content)
    assert "level" in log_entry
    assert log_entry["level"] == "INFO"
    assert "message" in log_entry
    assert "Test log message" in log_entry["message"]

    # Verify it has both handlers (stderr console + file)
    assert len(logger.handlers) == 2
