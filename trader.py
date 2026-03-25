import uuid
from dataclasses import dataclass
from typing import Optional

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL

import config
from strategy import TradeSignal
from market_discovery import Market
from data_store import DataStore
from logger_setup import get_logger, log_decision

log = get_logger("trader")


@dataclass
class OrderResult:
    order_id: str
    success: bool
    message: str
    is_paper: bool


class Trader:
    def __init__(self, store: DataStore):
        self.store = store
        self.paper_mode = config.PAPER_TRADING
        self.client: Optional[ClobClient] = None

        if not self.paper_mode:
            self._init_live_client()

    def _init_live_client(self):
        """Initialize the py-clob-client for live trading."""
        if not config.PRIVATE_KEY:
            log.error("No PRIVATE_KEY set — cannot initialize live trading")
            self.paper_mode = True
            return

        try:
            self.client = ClobClient(
                config.POLYMARKET_HOST,
                key=config.PRIVATE_KEY,
                chain_id=config.CHAIN_ID,
                signature_type=0,  # 0=EOA, 1=Magic/email, 2=browser proxy
            )
            # Derive or create API credentials (L2 auth)
            creds = self.client.create_or_derive_api_creds()
            self.client.set_api_creds(creds)
            log.info("Live trading client initialized successfully")
        except Exception as e:
            log.error(f"Failed to init live client: {e}")
            self.paper_mode = True

    def execute_signal(self, signal: TradeSignal, market: Market) -> OrderResult:
        """Execute a trade signal (paper or live)."""
        # Resolve token ID from market
        if signal.side == "YES":
            token_id = market.yes_token_id
        else:
            token_id = market.no_token_id

        if self.paper_mode:
            return self._paper_trade(signal, market, token_id)
        else:
            return self._live_trade(signal, market, token_id)

    def _paper_trade(self, signal: TradeSignal, market: Market, token_id: str) -> OrderResult:
        """Simulate trade execution for paper trading."""
        order_id = f"paper-{uuid.uuid4().hex[:12]}"

        # Record the trade
        self.store.record_trade(
            market_id=signal.market_id,
            question=signal.question,
            side=signal.side,
            price=signal.price,
            size=signal.size,
            token_id=token_id,
            condition_id=market.condition_id,
            order_id=order_id,
            is_paper=True,
            estimated_prob=signal.confidence,
            edge=signal.edge,
            reasoning=signal.reasoning,
        )

        # Update position
        self.store.upsert_position(
            market_id=signal.market_id,
            question=signal.question,
            side=signal.side,
            price=signal.price,
            size=signal.size,
            token_id=token_id,
        )

        log.info(
            f"[PAPER] {signal.side} {signal.size:.1f} shares @ ${signal.price:.3f} "
            f"on '{signal.question[:50]}' (edge: {signal.edge:+.2%})"
        )

        log_decision(log, "paper_trade", {
            "order_id": order_id,
            "market_id": signal.market_id,
            "side": signal.side,
            "price": signal.price,
            "size": signal.size,
            "cost": signal.cost_usdc,
            "edge": signal.edge,
        })

        return OrderResult(
            order_id=order_id,
            success=True,
            message="Paper trade executed",
            is_paper=True,
        )

    def _live_trade(self, signal: TradeSignal, market: Market, token_id: str) -> OrderResult:
        """Execute a real trade via py-clob-client."""
        if not self.client:
            return OrderResult("", False, "No live client available", False)

        try:
            side = BUY  # We always BUY the side we believe in (YES or NO token)

            order_args = OrderArgs(
                token_id=token_id,
                price=signal.price,
                size=signal.size,
                side=side,
            )

            signed_order = self.client.create_order(order_args)
            result = self.client.post_order(signed_order, OrderType.GTC)

            order_id = result.get("orderID", result.get("id", "unknown"))
            success = result.get("success", True)

            if success:
                self.store.record_trade(
                    market_id=signal.market_id,
                    question=signal.question,
                    side=signal.side,
                    price=signal.price,
                    size=signal.size,
                    token_id=token_id,
                    condition_id=market.condition_id,
                    order_id=order_id,
                    is_paper=False,
                    estimated_prob=signal.confidence,
                    edge=signal.edge,
                    reasoning=signal.reasoning,
                )

                self.store.upsert_position(
                    market_id=signal.market_id,
                    question=signal.question,
                    side=signal.side,
                    price=signal.price,
                    size=signal.size,
                    token_id=token_id,
                )

                log.info(
                    f"[LIVE] {signal.side} {signal.size:.1f} shares @ ${signal.price:.3f} "
                    f"on '{signal.question[:50]}' — order: {order_id}"
                )

            return OrderResult(
                order_id=order_id,
                success=success,
                message=str(result),
                is_paper=False,
            )

        except Exception as e:
            log.error(f"Live trade failed: {e}")
            return OrderResult("", False, str(e), False)

    def get_open_orders(self) -> list[dict]:
        """Get open orders from CLOB (live mode only)."""
        if self.paper_mode or not self.client:
            return []
        try:
            return self.client.get_orders() or []
        except Exception as e:
            log.error(f"Failed to get orders: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order (live mode only)."""
        if self.paper_mode or not self.client:
            return False
        try:
            self.client.cancel(order_id)
            log.info(f"Cancelled order {order_id}")
            return True
        except Exception as e:
            log.error(f"Failed to cancel order {order_id}: {e}")
            return False

    def get_live_positions(self) -> list[dict]:
        """Get positions from CLOB API (live mode only)."""
        if self.paper_mode or not self.client:
            return []
        try:
            return self.client.get_positions() or []
        except Exception as e:
            log.error(f"Failed to get positions: {e}")
            return []

    def get_orderbook_price(self, token_id: str) -> float:
        """Get midpoint price from CLOB orderbook."""
        try:
            from py_clob_client.client import ClobClient
            reader = ClobClient(config.POLYMARKET_HOST)
            mid = reader.get_midpoint(token_id)
            return float(mid) if mid else 0
        except Exception as e:
            log.error(f"Failed to get orderbook price: {e}")
            return 0
