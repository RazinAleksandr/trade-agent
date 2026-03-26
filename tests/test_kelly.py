"""Tests for Kelly criterion, edge calculation, and position sizing."""

import pytest

from lib.strategy import calculate_edge, calculate_position_size, kelly_criterion


class TestKellyCriterion:
    """Tests for kelly_criterion() function."""

    def test_positive_edge(self):
        """kelly_criterion with positive edge returns positive fraction."""
        result = kelly_criterion(0.60, 0.50, fraction=1.0)
        assert result > 0

    def test_no_edge(self):
        """kelly_criterion with no edge (prob == price) returns 0."""
        result = kelly_criterion(0.50, 0.50, fraction=1.0)
        assert result == 0.0

    def test_negative_edge_clamped(self):
        """kelly_criterion with negative edge returns 0 (clamped)."""
        result = kelly_criterion(0.40, 0.50, fraction=1.0)
        assert result == 0.0

    def test_fraction_scales_linearly(self):
        """Quarter-Kelly equals full Kelly times 0.25."""
        full = kelly_criterion(0.60, 0.50, fraction=1.0)
        quarter = kelly_criterion(0.60, 0.50, fraction=0.25)
        assert quarter == pytest.approx(full * 0.25)

    def test_boundary_zero_price(self):
        """kelly_criterion returns 0 when price is 0."""
        result = kelly_criterion(0.60, 0.0)
        assert result == 0.0

    def test_boundary_price_at_one(self):
        """kelly_criterion returns 0 when price is 1.0."""
        result = kelly_criterion(0.60, 1.0)
        assert result == 0.0

    def test_quarter_kelly_default(self):
        """Default fraction is 0.25 (quarter Kelly)."""
        default_result = kelly_criterion(0.60, 0.50)
        explicit_result = kelly_criterion(0.60, 0.50, fraction=0.25)
        assert default_result == explicit_result

    def test_full_kelly_math(self):
        """Verify the exact Kelly math: (b*p - q) / b where b=(1-price)/price."""
        prob = 0.70
        price = 0.50
        b = (1 - price) / price  # net odds = 1.0
        q = 1 - prob  # 0.30
        expected = (b * prob - q) / b  # (0.70 - 0.30) / 1.0 = 0.40
        result = kelly_criterion(prob, price, fraction=1.0)
        assert result == pytest.approx(expected)


class TestCalculateEdge:
    """Tests for calculate_edge() function."""

    def test_edge_positive(self):
        """Positive edge when estimated prob > market price."""
        result = calculate_edge(0.65, 0.50)
        assert result == pytest.approx(0.15)

    def test_edge_negative(self):
        """Negative edge when estimated prob < market price."""
        result = calculate_edge(0.40, 0.50)
        assert result == pytest.approx(-0.10)

    def test_edge_zero(self):
        """Zero edge when estimated prob == market price."""
        result = calculate_edge(0.50, 0.50)
        assert result == pytest.approx(0.0)

    def test_edge_precision(self):
        """Edge is rounded to avoid floating point noise."""
        # 0.333333 - 0.166666 should not have excessive decimals
        result = calculate_edge(0.333333, 0.166666)
        # Should be clean without trailing noise
        assert result == pytest.approx(0.166667, abs=1e-5)


class TestCalculatePositionSize:
    """Tests for calculate_position_size() function."""

    def test_positive_size(self):
        """Returns positive size when there is positive edge."""
        result = calculate_position_size(0.65, 0.50, bankroll=200.0)
        assert result["size_usdc"] > 0
        assert result["num_shares"] > 0
        assert result["kelly_raw"] > 0
        assert result["kelly_adjusted"] > 0

    def test_no_edge_zero_size(self):
        """Returns zero size when there is no edge."""
        result = calculate_position_size(0.50, 0.50, bankroll=200.0)
        assert result["size_usdc"] == 0.0
        assert result["num_shares"] == 0.0

    def test_position_size_capped(self):
        """Position size respects max_position_usdc cap."""
        # Large bankroll with high Kelly fraction should still be capped
        result = calculate_position_size(
            0.80, 0.50, bankroll=1000.0,
            kelly_fraction=1.0, max_position_usdc=50.0,
        )
        assert result["size_usdc"] <= 50.0

    def test_position_size_below_minimum(self):
        """Returns zero when notional is below order_min_size (5 USDC)."""
        # Very small edge with small bankroll -> tiny Kelly -> below 5 USDC
        result = calculate_position_size(
            0.52, 0.50, bankroll=20.0,
            kelly_fraction=0.25, max_position_usdc=50.0, order_min_size=5.0,
        )
        assert result["size_usdc"] == 0.0

    def test_position_size_shares_rounded(self):
        """num_shares has at most 2 decimal places."""
        result = calculate_position_size(
            0.70, 0.50, bankroll=200.0,
            kelly_fraction=0.25, max_position_usdc=50.0,
        )
        if result["num_shares"] > 0:
            # Check that rounding to 2 decimal places is exact
            assert result["num_shares"] == round(result["num_shares"], 2)

    def test_position_size_respects_bankroll(self):
        """Position size does not exceed available bankroll."""
        result = calculate_position_size(
            0.90, 0.50, bankroll=30.0,
            kelly_fraction=1.0, max_position_usdc=100.0,
        )
        assert result["size_usdc"] <= 30.0

    def test_position_size_returns_all_keys(self):
        """Return dict contains all expected keys."""
        result = calculate_position_size(0.65, 0.50, bankroll=200.0)
        assert "size_usdc" in result
        assert "num_shares" in result
        assert "kelly_raw" in result
        assert "kelly_adjusted" in result
