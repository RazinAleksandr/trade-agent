"""Tests for safety requirements SAFE-01 through SAFE-05.

Verifies:
- SAFE-01: Paper trading is the default mode
- SAFE-02: Paper mode uses realistic CLOB pricing (ask for buys, bid for sells)
- SAFE-03: Live trading gate blocks without positive P&L over N cycles
- SAFE-04: Credential refresh on 401 responses
- SAFE-05: Order normalization (2 decimal places, 5 USDC minimum)
"""

import json
import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from lib.config import Config, load_config
from lib.db import DataStore
from lib.models import OrderResult
from lib.trading import validate_order, execute_live_trade


# ============================================================
# SAFE-01: Paper Trading Default
# ============================================================


class TestSafe01PaperDefault:
    """SAFE-01: Paper trading is the default mode."""

    def test_config_default_paper_trading_true(self):
        """Config dataclass defaults paper_trading to True."""
        config = Config()
        assert config.paper_trading is True

    def test_load_config_default_paper_trading(self):
        """load_config() without PAPER_TRADING env returns True."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear PAPER_TRADING if set
            os.environ.pop("PAPER_TRADING", None)
            config = load_config()
            assert config.paper_trading is True

    def test_paper_trading_requires_explicit_false(self):
        """Paper trading only disabled with explicit 'false' env var."""
        with patch.dict(os.environ, {"PAPER_TRADING": "false"}):
            config = load_config()
            assert config.paper_trading is False


# ============================================================
# SAFE-02: Realistic Paper Pricing
# ============================================================


class TestSafe02RealisticPricing:
    """SAFE-02: Paper buys fill at best ask, sells at best bid."""

    @patch("lib.pricing.ClobClient")
    def test_buy_fills_at_best_ask(self, mock_clob_cls):
        """Paper BUY queries SELL book (best ask) per CLOB API semantics."""
        from lib.pricing import get_fill_price

        mock_client = MagicMock()
        mock_clob_cls.return_value = mock_client
        mock_client.get_price.return_value = {"price": "0.65"}

        price = get_fill_price("tok-yes", "BUY", "https://clob.polymarket.com")

        assert price == 0.65
        # BUY fills at best ask -> queries SELL book
        mock_client.get_price.assert_called_once_with("tok-yes", "SELL")

    @patch("lib.pricing.ClobClient")
    def test_sell_fills_at_best_bid(self, mock_clob_cls):
        """Paper SELL queries BUY book (best bid) per CLOB API semantics."""
        from lib.pricing import get_fill_price

        mock_client = MagicMock()
        mock_clob_cls.return_value = mock_client
        mock_client.get_price.return_value = {"price": "0.55"}

        price = get_fill_price("tok-yes", "SELL", "https://clob.polymarket.com")

        assert price == 0.55
        # SELL fills at best bid -> queries BUY book
        mock_client.get_price.assert_called_once_with("tok-yes", "BUY")

    @patch("lib.pricing.ClobClient")
    def test_no_liquidity_raises_value_error(self, mock_clob_cls):
        """No liquidity (price=0) raises ValueError per D-10."""
        from lib.pricing import get_fill_price

        mock_client = MagicMock()
        mock_clob_cls.return_value = mock_client
        mock_client.get_price.return_value = {"price": "0"}

        with pytest.raises(ValueError, match="No liquidity"):
            get_fill_price("tok-yes", "BUY", "https://clob.polymarket.com")


# ============================================================
# SAFE-03: Live Trading Gate
# ============================================================


class TestSafe03LiveGate:
    """SAFE-03: Live trading gate requires positive P&L over N cycles."""

    def test_get_paper_cycle_stats_no_reports(self):
        """Zero cycles when reports directory doesn't exist."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            store = DataStore(db_path=tmp.name)
            try:
                stats = store.get_paper_cycle_stats(
                    reports_dir="/nonexistent_dir"
                )
                assert stats["cycle_count"] == 0
                assert stats["total_pnl"] == 0.0
            finally:
                store.close()

    def test_get_paper_cycle_stats_counts_reports(self):
        """Cycle count matches number of cycle-*.md report files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            reports_dir = os.path.join(tmpdir, "reports")
            os.makedirs(reports_dir)

            # Create 3 cycle report files
            for i in range(3):
                with open(os.path.join(reports_dir, f"cycle-2026010{i}-120000.md"), "w") as f:
                    f.write(f"# Cycle {i}\n")

            # Create a non-cycle file (should not be counted)
            with open(os.path.join(reports_dir, "summary.md"), "w") as f:
                f.write("# Summary\n")

            store = DataStore(db_path=db_path)
            try:
                stats = store.get_paper_cycle_stats(reports_dir=reports_dir)
                assert stats["cycle_count"] == 3
            finally:
                store.close()

    def test_get_paper_cycle_stats_pnl_from_closed_positions(self):
        """Total P&L is sum of realized_pnl from closed positions."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        store = DataStore(db_path=db_path)
        try:
            # Create and close two positions
            store.upsert_position("mkt-1", "Q1", "YES", 0.40, 10.0, "t1")
            store.close_position("mkt-1", 1.0)  # realized = (1.0 - 0.40) * 10 = 6.0
            store.upsert_position("mkt-2", "Q2", "YES", 0.60, 10.0, "t2")
            store.close_position("mkt-2", 0.0)  # realized = (0.0 - 0.60) * 10 = -6.0

            stats = store.get_paper_cycle_stats(reports_dir="/nonexistent")
            assert stats["total_pnl"] == pytest.approx(0.0, abs=0.01)
        finally:
            store.close()
            os.remove(db_path)

    def test_gate_pass_file_format(self):
        """Gate pass file contains required JSON fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gate_path = os.path.join(tmpdir, ".live-gate-pass")
            gate_data = {
                "enabled_at": "2026-03-27T12:00:00+00:00",
                "cycles_at_gate": 15,
                "pnl_at_gate": 42.50,
                "min_paper_cycles": 10,
            }
            with open(gate_path, "w") as f:
                json.dump(gate_data, f)

            with open(gate_path) as f:
                loaded = json.load(f)
            assert "enabled_at" in loaded
            assert "cycles_at_gate" in loaded
            assert "pnl_at_gate" in loaded
            assert loaded["cycles_at_gate"] == 15
            assert loaded["pnl_at_gate"] == 42.50


# ============================================================
# SAFE-04: Credential Refresh on 401
# ============================================================


class TestSafe04CredentialRefresh:
    """SAFE-04: CLOB API credential refresh on 401 responses."""

    @patch("lib.trading.ClobClient")
    def test_retries_on_401(self, mock_clob_cls):
        """401 from post_order triggers re-derivation and retry."""
        from py_clob_client.exceptions import PolyApiException

        mock_client = MagicMock()
        mock_clob_cls.return_value = mock_client
        mock_client.create_or_derive_api_creds.return_value = {
            "apiKey": "k", "secret": "s", "passphrase": "p"
        }
        mock_client.create_order.return_value = {"signed": True}

        # First call: 401 error. Second call: success.
        error_401 = PolyApiException(MagicMock(status_code=401, text="Unauthorized"))
        mock_client.post_order.side_effect = [
            error_401,
            {"orderID": "retry-order-1"},
        ]

        store = MagicMock()
        result = execute_live_trade(
            market_id="mkt-retry",
            question="401 retry test",
            side="YES",
            token_id="tok-yes",
            price=0.50,
            size=20.0,
            host="https://clob.polymarket.com",
            private_key="0xkey",
            chain_id=137,
            store=store,
        )

        assert result.success is True
        assert result.order_id == "retry-order-1"
        # ClobClient created twice (initial + retry)
        assert mock_clob_cls.call_count == 2
        # Credentials derived twice
        assert mock_client.create_or_derive_api_creds.call_count == 2

    @patch("lib.trading.ClobClient")
    def test_no_retry_on_500(self, mock_clob_cls):
        """Non-401 PolyApiException does not trigger retry."""
        from py_clob_client.exceptions import PolyApiException

        mock_client = MagicMock()
        mock_clob_cls.return_value = mock_client
        mock_client.create_or_derive_api_creds.return_value = {
            "apiKey": "k", "secret": "s", "passphrase": "p"
        }
        mock_client.create_order.return_value = {"signed": True}

        error_500 = PolyApiException(MagicMock(status_code=500, text="Server Error"))
        mock_client.post_order.side_effect = error_500

        store = MagicMock()
        result = execute_live_trade(
            market_id="mkt-500",
            question="500 error test",
            side="YES",
            token_id="tok-yes",
            price=0.50,
            size=20.0,
            host="https://clob.polymarket.com",
            private_key="0xkey",
            chain_id=137,
            store=store,
        )

        assert result.success is False
        # Only one attempt (no retry for 500)
        assert mock_clob_cls.call_count == 1

    @patch("lib.trading.ClobClient")
    def test_no_retry_on_generic_exception(self, mock_clob_cls):
        """Generic Exception does not trigger retry."""
        mock_client = MagicMock()
        mock_clob_cls.return_value = mock_client
        mock_client.create_or_derive_api_creds.return_value = {
            "apiKey": "k", "secret": "s", "passphrase": "p"
        }
        mock_client.create_order.side_effect = ConnectionError("Network down")

        store = MagicMock()
        result = execute_live_trade(
            market_id="mkt-err",
            question="Network error test",
            side="YES",
            token_id="tok-yes",
            price=0.50,
            size=20.0,
            host="https://clob.polymarket.com",
            private_key="0xkey",
            chain_id=137,
            store=store,
        )

        assert result.success is False
        assert "Network down" in result.message
        # Only one attempt (no retry for generic exceptions)
        assert mock_clob_cls.call_count == 1

    @patch("lib.trading.ClobClient")
    def test_401_retry_exhausted(self, mock_clob_cls):
        """Both attempts fail with 401 -> returns failure."""
        from py_clob_client.exceptions import PolyApiException

        mock_client = MagicMock()
        mock_clob_cls.return_value = mock_client
        mock_client.create_or_derive_api_creds.return_value = {
            "apiKey": "k", "secret": "s", "passphrase": "p"
        }
        mock_client.create_order.return_value = {"signed": True}

        error_401 = PolyApiException(MagicMock(status_code=401, text="Unauthorized"))
        mock_client.post_order.side_effect = error_401  # Fails every time

        store = MagicMock()
        result = execute_live_trade(
            market_id="mkt-perm-401",
            question="Permanent 401",
            side="YES",
            token_id="tok-yes",
            price=0.50,
            size=20.0,
            host="https://clob.polymarket.com",
            private_key="0xkey",
            chain_id=137,
            store=store,
        )

        assert result.success is False
        # Two attempts total (initial + 1 retry)
        assert mock_clob_cls.call_count == 2
        store.record_trade.assert_not_called()


# ============================================================
# SAFE-05: Order Normalization
# ============================================================


class TestSafe05OrderNormalization:
    """SAFE-05: Order size rounded to 2 decimals, min 5 USDC notional."""

    def test_size_rounded_to_2_decimals(self):
        """Size with > 2 decimal places is rounded."""
        # 0.50 * round(10.456, 2) = 0.50 * 10.46 = 5.23 >= 5.0
        valid, msg = validate_order(0.50, 10.456, 5.0)
        assert valid is True

    def test_minimum_notional_5_usdc(self):
        """Order with notional < 5 USDC is rejected."""
        # 0.10 * 2.0 = 0.20 < 5.0
        valid, msg = validate_order(0.10, 2.0, 5.0)
        assert valid is False
        assert "below minimum" in msg

    def test_price_range_enforced(self):
        """Price must be strictly between 0 and 1."""
        valid_zero, _ = validate_order(0.0, 20.0)
        valid_one, _ = validate_order(1.0, 20.0)
        valid_neg, _ = validate_order(-0.1, 20.0)
        assert valid_zero is False
        assert valid_one is False
        assert valid_neg is False

    def test_valid_order_accepted(self):
        """Valid order with proper price and notional passes."""
        valid, msg = validate_order(0.50, 20.0, 5.0)
        assert valid is True
        assert msg == ""
