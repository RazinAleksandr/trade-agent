import os
import tempfile

import pytest

from lib.config import Config
from lib.db import DataStore


@pytest.fixture
def tmp_db_path():
    """Provide a temporary database file path, cleaned up after test."""
    path = tempfile.mktemp(suffix=".db")
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def tmp_log_path():
    """Provide a temporary log file path, cleaned up after test."""
    path = tempfile.mktemp(suffix=".log")
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def test_config(tmp_db_path, tmp_log_path):
    """Create a Config with temporary file paths for testing."""
    return Config(db_path=tmp_db_path, log_file=tmp_log_path, paper_trading=True)


@pytest.fixture
def store(tmp_db_path):
    """Create a DataStore with a temporary database, closed after test."""
    ds = DataStore(db_path=tmp_db_path)
    yield ds
    ds.close()
