import json
import logging
import sys
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """Format log records as JSON for machine parsing."""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def get_logger(name: str, config=None) -> logging.Logger:
    """Create a dual-output logger (stderr console + JSON file).

    Args:
        name: Logger name (typically module name).
        config: Optional Config object. Uses defaults if None.

    Returns:
        Configured logger with console (stderr) and file (JSON) handlers.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    log_level = "INFO"
    log_file = "trading.log"
    if config is not None:
        log_level = config.log_level
        log_file = config.log_file

    logger.setLevel(getattr(logging, log_level))

    # Console handler -- human-readable to stderr (stdout reserved for JSON output per D-02)
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(console)

    # File handler -- JSON for machine parsing
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(JsonFormatter())
    logger.addHandler(file_handler)

    return logger


def log_decision(logger: logging.Logger, decision_type: str, data: dict):
    """Log a structured decision record.

    Args:
        logger: Logger instance to use.
        decision_type: Type of decision (e.g. "trade_signal", "paper_trade").
        data: Decision data to include in the log record.
    """
    record = logger.makeRecord(
        logger.name, logging.INFO, "", 0,
        f"DECISION: {decision_type}", (), None
    )
    record.extra_data = data
    logger.handle(record)
