import json
import sqlite3
from datetime import datetime, timezone

from lib.logging_setup import get_logger

log = get_logger("data_store")


class DataStore:
    """SQLite persistence for trades, positions, decisions, snapshots, and metrics."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                market_id TEXT NOT NULL,
                condition_id TEXT,
                token_id TEXT,
                question TEXT,
                side TEXT NOT NULL,
                price REAL NOT NULL,
                size REAL NOT NULL,
                cost_usdc REAL NOT NULL,
                order_id TEXT,
                status TEXT DEFAULT 'pending',
                is_paper INTEGER DEFAULT 1,
                estimated_prob REAL,
                edge REAL,
                reasoning TEXT,
                neg_risk INTEGER DEFAULT 0,
                fill_price REAL
            );

            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT NOT NULL UNIQUE,
                token_id TEXT,
                question TEXT,
                side TEXT NOT NULL,
                avg_price REAL NOT NULL,
                size REAL NOT NULL,
                cost_basis REAL NOT NULL,
                current_price REAL,
                unrealized_pnl REAL DEFAULT 0,
                realized_pnl REAL DEFAULT 0,
                status TEXT DEFAULT 'open',
                opened_at TEXT NOT NULL,
                closed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                market_id TEXT,
                question TEXT,
                decision_type TEXT NOT NULL,
                market_price REAL,
                estimated_prob REAL,
                edge REAL,
                kelly_size REAL,
                action TEXT NOT NULL,
                reasoning TEXT,
                metadata TEXT
            );

            CREATE TABLE IF NOT EXISTS market_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                market_id TEXT NOT NULL,
                question TEXT,
                yes_price REAL,
                no_price REAL,
                volume_24h REAL,
                liquidity REAL,
                end_date TEXT
            );

            CREATE TABLE IF NOT EXISTS strategy_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                total_trades INTEGER,
                win_rate REAL,
                total_pnl REAL,
                avg_edge REAL,
                sharpe_ratio REAL,
                metadata TEXT
            );
        """)
        self.conn.commit()

        # Schema migration: add 'action' column to trades table
        try:
            self.conn.execute("ALTER TABLE trades ADD COLUMN action TEXT DEFAULT 'BUY'")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Schema migration: add 'fee_amount' column to trades table
        try:
            self.conn.execute("ALTER TABLE trades ADD COLUMN fee_amount REAL DEFAULT 0")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists

    def record_trade(self, market_id: str, question: str, side: str,
                     price: float, size: float, token_id: str = "",
                     condition_id: str = "", order_id: str = "",
                     is_paper: bool = True, estimated_prob: float = 0,
                     edge: float = 0, reasoning: str = "",
                     neg_risk: bool = False, fill_price: float = 0,
                     action: str = "BUY", fee_amount: float = 0) -> int:
        """Record a trade execution. Returns the trade ID."""
        now = datetime.now(timezone.utc).isoformat()
        cost = price * size
        cur = self.conn.execute(
            """INSERT INTO trades
               (timestamp, market_id, condition_id, token_id, question,
                side, price, size, cost_usdc, order_id, status, is_paper,
                estimated_prob, edge, reasoning, neg_risk, fill_price, action,
                fee_amount)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'filled', ?, ?, ?, ?, ?, ?, ?, ?)""",
            (now, market_id, condition_id, token_id, question,
             side, price, size, cost, order_id, int(is_paper),
             estimated_prob, edge, reasoning, int(neg_risk), fill_price, action,
             fee_amount)
        )
        self.conn.commit()
        log.info(f"Recorded trade: {action} {side} {size}@{price} on {question[:50]}")
        return cur.lastrowid

    def upsert_position(self, market_id: str, question: str, side: str,
                        price: float, size: float, token_id: str = ""):
        """Create or update a position. Sums size and recalculates avg price."""
        now = datetime.now(timezone.utc).isoformat()
        existing = self.conn.execute(
            "SELECT * FROM positions WHERE market_id = ? AND status = 'open'",
            (market_id,)
        ).fetchone()

        if existing:
            new_size = existing["size"] + size
            new_cost = existing["cost_basis"] + (price * size)
            new_avg = new_cost / new_size if new_size > 0 else 0
            self.conn.execute(
                """UPDATE positions SET size = ?, avg_price = ?,
                   cost_basis = ? WHERE id = ?""",
                (new_size, new_avg, new_cost, existing["id"])
            )
        else:
            self.conn.execute(
                """INSERT INTO positions
                   (market_id, token_id, question, side, avg_price,
                    size, cost_basis, opened_at, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open')""",
                (market_id, token_id, question, side, price,
                 size, price * size, now)
            )
        self.conn.commit()

    def get_open_positions(self) -> list[dict]:
        """Return all open positions as list of dicts."""
        rows = self.conn.execute(
            "SELECT * FROM positions WHERE status = 'open'"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_total_exposure(self) -> float:
        """Return sum of cost_basis for all open positions."""
        result = self.conn.execute(
            "SELECT COALESCE(SUM(cost_basis), 0) as total FROM positions WHERE status = 'open'"
        ).fetchone()
        return result["total"]

    def record_decision(self, market_id: str, question: str,
                        decision_type: str, market_price: float,
                        estimated_prob: float, edge: float,
                        kelly_size: float, action: str,
                        reasoning: str = "", metadata: dict = None):
        """Record a trading decision for audit trail."""
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """INSERT INTO decisions
               (timestamp, market_id, question, decision_type,
                market_price, estimated_prob, edge, kelly_size,
                action, reasoning, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (now, market_id, question, decision_type,
             market_price, estimated_prob, edge, kelly_size,
             action, reasoning, json.dumps(metadata) if metadata else None)
        )
        self.conn.commit()

    def record_market_snapshot(self, market_id: str, question: str,
                               yes_price: float, no_price: float,
                               volume_24h: float, liquidity: float,
                               end_date: str = ""):
        """Record a point-in-time market snapshot."""
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """INSERT INTO market_snapshots
               (timestamp, market_id, question, yes_price, no_price,
                volume_24h, liquidity, end_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (now, market_id, question, yes_price, no_price,
             volume_24h, liquidity, end_date)
        )
        self.conn.commit()

    def get_trade_history(self, limit: int = 100) -> list[dict]:
        """Return recent trades, newest first."""
        rows = self.conn.execute(
            "SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_strategy_stats(self) -> dict:
        """Compute aggregate trading statistics.

        Uses realized PnL from closed positions when available,
        falls back to edge-estimated PnL otherwise.
        """
        trades = self.conn.execute(
            "SELECT * FROM trades WHERE status = 'filled'"
        ).fetchall()
        if not trades:
            return {"total_trades": 0, "win_rate": 0, "total_pnl": 0, "avg_edge": 0}

        total = len(trades)
        avg_edge = sum(t["edge"] for t in trades) / total if total > 0 else 0

        # Use realized PnL from closed positions when available
        closed = self.conn.execute(
            "SELECT realized_pnl FROM positions WHERE status = 'closed'"
        ).fetchall()

        if closed:
            total_pnl = sum(c["realized_pnl"] for c in closed)
            wins = sum(1 for c in closed if c["realized_pnl"] > 0)
            win_rate = wins / len(closed) if closed else 0
        else:
            # Fall back to edge-estimated PnL when no positions resolved
            total_pnl = sum(t["edge"] * t["cost_usdc"] for t in trades)
            wins = sum(1 for t in trades if t["edge"] > 0)
            win_rate = wins / total if total > 0 else 0

        return {
            "total_trades": total,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "avg_edge": avg_edge,
        }

    def get_paper_cycle_stats(self, reports_dir: str = "state/reports") -> dict:
        """Get paper trading statistics for live gate verification.

        Counts completed cycle reports (not trade rows) per Pitfall 6.

        Args:
            reports_dir: Path to cycle reports directory.

        Returns:
            dict with cycle_count (int) and total_pnl (float).
        """
        import glob as _glob
        import os as _os

        # Count completed cycle report files (each represents one full cycle)
        if _os.path.isdir(reports_dir):
            cycle_count = len(_glob.glob(_os.path.join(reports_dir, "cycle-*.md")))
        else:
            cycle_count = 0

        # Aggregate realized P&L from closed positions
        result = self.conn.execute(
            "SELECT COALESCE(SUM(realized_pnl), 0) FROM positions WHERE status = 'closed'"
        ).fetchone()
        total_pnl = float(result[0])

        return {"cycle_count": cycle_count, "total_pnl": total_pnl}

    def close_position(self, market_id: str, exit_price: float):
        """Close a position and calculate realized PnL."""
        now = datetime.now(timezone.utc).isoformat()
        pos = self.conn.execute(
            "SELECT * FROM positions WHERE market_id = ? AND status = 'open'",
            (market_id,)
        ).fetchone()
        if not pos:
            return

        realized = (exit_price - pos["avg_price"]) * pos["size"]
        self.conn.execute(
            """UPDATE positions SET status = 'closed', closed_at = ?,
               realized_pnl = ?, current_price = ? WHERE id = ?""",
            (now, realized, exit_price, pos["id"])
        )
        self.conn.commit()
        log.info(f"Closed position on {pos['question'][:50]}: PnL={realized:.2f}")

    def reduce_position(self, market_id: str, sell_size: float,
                        sell_price: float) -> float:
        """Reduce (or fully close) a position. Returns realized PnL.

        For full sells (sell_size >= held size), closes the position.
        For partial sells, reduces size and cost_basis proportionally.

        Raises:
            ValueError: If no open position exists for market_id or sell_size > held.
        """
        pos = self.conn.execute(
            "SELECT * FROM positions WHERE market_id = ? AND status = 'open'",
            (market_id,)
        ).fetchone()
        if not pos:
            raise ValueError(f"No open position for market {market_id}")

        if sell_size > pos["size"] + 0.001:  # small tolerance for float rounding
            raise ValueError(
                f"Sell size {sell_size} exceeds held size {pos['size']}"
            )

        now = datetime.now(timezone.utc).isoformat()
        realized_pnl = (sell_price - pos["avg_price"]) * sell_size

        if sell_size >= pos["size"] - 0.001:
            # Full close
            self.conn.execute(
                """UPDATE positions SET status = 'closed', closed_at = ?,
                   realized_pnl = ?, current_price = ?, size = 0,
                   cost_basis = 0 WHERE id = ?""",
                (now, realized_pnl, sell_price, pos["id"])
            )
            log.info(
                f"Closed position on {pos['question'][:50]}: "
                f"PnL=${realized_pnl:.2f}"
            )
        else:
            # Partial close — reduce size and cost_basis proportionally
            new_size = pos["size"] - sell_size
            new_cost = pos["avg_price"] * new_size  # avg_price unchanged
            self.conn.execute(
                """UPDATE positions SET size = ?, cost_basis = ?
                   WHERE id = ?""",
                (new_size, new_cost, pos["id"])
            )
            log.info(
                f"Reduced position on {pos['question'][:50]} by {sell_size}: "
                f"PnL=${realized_pnl:.2f}, remaining={new_size:.2f}"
            )

        self.conn.commit()
        return realized_pnl

    def get_all_closed_positions(self) -> list[dict]:
        """Return all closed positions as list of dicts."""
        rows = self.conn.execute(
            "SELECT * FROM positions WHERE status = 'closed' ORDER BY closed_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_closed_positions_since(self, since_iso: str) -> list[dict]:
        """Return closed positions since a given ISO timestamp."""
        rows = self.conn.execute(
            "SELECT * FROM positions WHERE status = 'closed' AND closed_at >= ? "
            "ORDER BY closed_at DESC",
            (since_iso,)
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        """Close the database connection."""
        self.conn.close()
