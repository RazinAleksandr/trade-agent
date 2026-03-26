import json
import sys

EXIT_INVALID_ARG = 2
EXIT_API_ERROR = 3
EXIT_CONFIG_ERROR = 4
EXIT_TRADE_FAILED = 5


def error_exit(message: str, code: str, exit_code: int = 1):
    """Write a structured JSON error to stderr and exit.

    Args:
        message: Human-readable error description.
        code: Machine-readable error code (e.g. "INVALID_ARG").
        exit_code: Process exit code (default 1).
    """
    json.dump({"error": message, "code": code}, sys.stderr)
    sys.stderr.write("\n")
    sys.exit(exit_code)
