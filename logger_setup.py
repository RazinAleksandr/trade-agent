import logging
import json
import sys
from datetime import datetime, timezone
import config


class JsonFormatter(logging.Formatter):
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


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, config.LOG_LEVEL))

    # Console handler — human readable
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(console)

    # File handler — JSON for machine parsing
    file_handler = logging.FileHandler(config.LOG_FILE)
    file_handler.setFormatter(JsonFormatter())
    logger.addHandler(file_handler)

    return logger


def log_decision(logger: logging.Logger, decision_type: str, data: dict):
    record = logger.makeRecord(
        logger.name, logging.INFO, "", 0,
        f"DECISION: {decision_type}", (), None
    )
    record.extra_data = data
    logger.handle(record)
