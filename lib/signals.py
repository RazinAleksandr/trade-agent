import signal

_shutdown_requested = False


def _signal_handler(sig, frame):
    """Handle SIGINT/SIGTERM by setting the shutdown flag."""
    global _shutdown_requested
    _shutdown_requested = True


def register_shutdown_handler():
    """Register SIGINT and SIGTERM handlers for graceful shutdown."""
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)


def is_shutdown_requested() -> bool:
    """Check whether a shutdown signal has been received."""
    return _shutdown_requested
