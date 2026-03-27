"""Tests for lib/portfolio.py -- portfolio tracking, P&L, and resolved detection."""

from unittest.mock import patch

from lib.models import Market
from lib.portfolio import check_resolved_markets, check_risk_limits, get_portfolio_summary


def _make_market(
    market_id: str = "mkt1",
    yes_price: float = 0.50,
    no_price: float = 0.50,
    closed: bool = False,
) -> Market:
    """Create a Market fixture with sensible defaults."""
    return Market(
        id=market_id,
        condition_id=f"cond-{market_id}",
        question=f"Will {market_id} resolve?",
        description="Test market",
        yes_token_id=f"yes-{market_id}",
        no_token_id=f"no-{market_id}",
        yes_price=yes_price,
        no_price=no_price,
        best_bid=0.48,
        best_ask=0.52,
        volume_24h=5000.0,
        liquidity=2000.0,
        end_date="2026-12-31",
        category="test",
        active=not closed,
        closed=closed,
        neg_risk=False,
        order_min_size=5.0,
        tick_size=0.01,
    )


def _upsert_position(store, market_id="mkt1", question="Will mkt1 resolve?",
                      side="YES", price=0.50, size=10.0, token_id="tok1"):
    """Helper to insert a position into the store."""
    store.upsert_position(
        market_id=market_id,
        question=question,
        side=side,
        price=price,
        size=size,
        token_id=token_id,
    )


class TestGetPortfolioSummary:
    """Tests for get_portfolio_summary."""

    @patch("lib.portfolio.fetch_market_by_id")
    def test_portfolio_summary_empty(self, mock_fetch, store):
        """No positions returns zero counts."""
        result = get_portfolio_summary(store, "https://gamma-api.polymarket.com")
        assert result["open_positions"] == 0
        assert result["total_exposure_usdc"] == 0

    @patch("lib.portfolio.fetch_market_by_id")
    def test_portfolio_summary_with_positions(self, mock_fetch, store):
        """Two positions are counted and prices updated."""
        _upsert_position(store, market_id="mkt1", price=0.50, size=10.0)
        _upsert_position(store, market_id="mkt2", question="Will mkt2 resolve?",
                         price=0.40, size=5.0, token_id="tok2")

        mock_fetch.return_value = _make_market(yes_price=0.70, no_price=0.30)

        result = get_portfolio_summary(store, "https://gamma-api.polymarket.com")
        assert result["open_positions"] == 2
        # Both positions should have updated unrealized_pnl
        for pos in result["positions"]:
            assert "unrealized_pnl" in pos

    @patch("lib.portfolio.fetch_market_by_id")
    def test_portfolio_unrealized_pnl_calculation(self, mock_fetch, store):
        """Unrealized P&L = (current_price - exit_fee - avg_price) * size.

        Exit fee is estimated conservatively (assumes CLOB exit).
        Category 'test' falls back to 'other' (fee_rate=0.2, exponent=2).
        At p=0.70: fee_per_share = 0.70 * 0.2 * (0.70 * 0.30)^2 = 0.0062
        """
        from lib.fees import calculate_fee_per_share

        _upsert_position(store, market_id="mkt1", side="YES", price=0.50, size=10.0)

        mock_fetch.return_value = _make_market(yes_price=0.70, no_price=0.30)

        result = get_portfolio_summary(store, "https://gamma-api.polymarket.com")
        pos = result["positions"][0]
        # P&L includes exit fee deduction for conservative estimate
        exit_fee = calculate_fee_per_share(0.70, "test")  # falls back to "other"
        expected_pnl = (0.70 - exit_fee - 0.50) * 10.0
        assert abs(pos["unrealized_pnl"] - expected_pnl) < 0.001


class TestCheckResolvedMarkets:
    """Tests for check_resolved_markets."""

    @patch("lib.portfolio.fetch_market_by_id")
    def test_check_resolved_markets(self, mock_fetch, store):
        """Resolved market detected and PnL calculated."""
        _upsert_position(store, market_id="mkt1", side="YES", price=0.50, size=10.0)

        mock_fetch.return_value = _make_market(yes_price=1.0, no_price=0.0, closed=True)

        resolved = check_resolved_markets(store, "https://gamma-api.polymarket.com")
        assert len(resolved) == 1
        # realized_pnl = (1.0 - 0.50) * 10.0 = 5.0
        assert resolved[0]["realized_pnl"] == 5.0
        assert resolved[0]["exit_price"] == 1.0

    @patch("lib.portfolio.fetch_market_by_id")
    def test_check_resolved_no_resolved(self, mock_fetch, store):
        """No resolved markets returns empty list."""
        _upsert_position(store, market_id="mkt1", side="YES", price=0.50, size=10.0)

        mock_fetch.return_value = _make_market(yes_price=0.60, no_price=0.40, closed=False)

        resolved = check_resolved_markets(store, "https://gamma-api.polymarket.com")
        assert len(resolved) == 0

    @patch("lib.portfolio.fetch_market_by_id")
    def test_check_resolved_updates_db(self, mock_fetch, store):
        """After resolution, position is closed in database."""
        _upsert_position(store, market_id="mkt1", side="YES", price=0.50, size=10.0)

        mock_fetch.return_value = _make_market(yes_price=1.0, no_price=0.0, closed=True)

        check_resolved_markets(store, "https://gamma-api.polymarket.com")
        # Position should no longer be open
        assert len(store.get_open_positions()) == 0


class TestCheckRiskLimits:
    """Tests for check_risk_limits."""

    def test_risk_limits_safe(self, store):
        """Exposure below 90% threshold produces no warnings."""
        # total exposure = 5.0, max = 200.0 -- well under 90%
        _upsert_position(store, market_id="mkt1", price=0.50, size=10.0)

        result = check_risk_limits(store, max_total_exposure_usdc=200.0,
                                   max_position_size_usdc=50.0)
        assert len(result["warnings"]) == 0

    def test_risk_limits_near_max(self, store):
        """Exposure above 90% of max triggers a total-exposure warning."""
        # Insert positions totaling > 90% of max (> 180 for max=200)
        _upsert_position(store, market_id="mkt1", price=10.0, size=10.0)  # cost=100
        _upsert_position(store, market_id="mkt2", question="Will mkt2 resolve?",
                         price=10.0, size=10.0, token_id="tok2")  # cost=100 -> total=200

        result = check_risk_limits(store, max_total_exposure_usdc=200.0,
                                   max_position_size_usdc=200.0)
        assert len(result["warnings"]) > 0
        assert any("Total exposure" in w for w in result["warnings"])

    def test_risk_limits_position_near_max(self, store):
        """Single position cost above 90% of max triggers a position warning."""
        # cost_basis = 46.0, max_position = 50.0 -> 92% utilization
        _upsert_position(store, market_id="mkt1", price=4.6, size=10.0)

        result = check_risk_limits(store, max_total_exposure_usdc=1000.0,
                                   max_position_size_usdc=50.0)
        assert len(result["warnings"]) > 0
        assert any("Position" in w for w in result["warnings"])
