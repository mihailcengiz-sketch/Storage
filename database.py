import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).parent / "portfolio.db"


def init_db(db_path=None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _create_tables(conn)
    return conn


def _create_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            coin_symbol TEXT    NOT NULL,
            coin_id     TEXT    NOT NULL,
            tx_type     TEXT    NOT NULL CHECK(tx_type IN ('buy','sell')),
            quantity    REAL    NOT NULL CHECK(quantity > 0),
            price_usd   REAL    NOT NULL CHECK(price_usd >= 0),
            tx_date     TEXT    NOT NULL,
            notes       TEXT    DEFAULT '',
            created_at  TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date   TEXT    NOT NULL,
            total_value_usd REAL    NOT NULL,
            total_cost_usd  REAL    NOT NULL,
            created_at      TEXT    DEFAULT (datetime('now')),
            UNIQUE(snapshot_date)
        );
    """)
    conn.commit()


def add_transaction(conn, coin_symbol: str, coin_id: str, tx_type: str,
                    quantity: float, price_usd: float, tx_date: str,
                    notes: str = "") -> int:
    cur = conn.execute(
        """INSERT INTO transactions
           (coin_symbol, coin_id, tx_type, quantity, price_usd, tx_date, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (coin_symbol.upper(), coin_id, tx_type, quantity, price_usd, tx_date, notes)
    )
    conn.commit()
    return cur.lastrowid


def delete_transaction(conn, tx_id: int):
    conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    conn.commit()


def get_all_transactions(conn) -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT * FROM transactions ORDER BY tx_date DESC, created_at DESC",
        conn
    )
    return df


def get_current_holdings(conn) -> pd.DataFrame:
    query = """
        SELECT
            coin_symbol,
            coin_id,
            SUM(CASE WHEN tx_type='buy'  THEN quantity          ELSE -quantity          END) AS net_quantity,
            SUM(CASE WHEN tx_type='buy'  THEN quantity*price_usd ELSE -quantity*price_usd END) AS total_cost_usd,
            SUM(CASE WHEN tx_type='buy'  THEN quantity*price_usd ELSE -quantity*price_usd END) /
                NULLIF(SUM(CASE WHEN tx_type='buy' THEN quantity ELSE -quantity END), 0) AS avg_buy_price
        FROM transactions
        GROUP BY coin_symbol, coin_id
        HAVING net_quantity > 0.000001
        ORDER BY total_cost_usd DESC
    """
    df = pd.read_sql_query(query, conn)
    return df


def save_snapshot(conn, snapshot_date: str, total_value_usd: float, total_cost_usd: float):
    conn.execute(
        """INSERT INTO portfolio_snapshots (snapshot_date, total_value_usd, total_cost_usd)
           VALUES (?, ?, ?)
           ON CONFLICT(snapshot_date) DO UPDATE SET
               total_value_usd = excluded.total_value_usd,
               total_cost_usd  = excluded.total_cost_usd""",
        (snapshot_date, total_value_usd, total_cost_usd)
    )
    conn.commit()


def get_snapshots(conn, days: int = 90) -> pd.DataFrame:
    df = pd.read_sql_query(
        """SELECT snapshot_date, total_value_usd, total_cost_usd
           FROM portfolio_snapshots
           ORDER BY snapshot_date ASC
           LIMIT ?""",
        conn,
        params=(days,)
    )
    if not df.empty:
        df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
    return df


def get_realized_pnl(conn) -> float:
    result = conn.execute("""
        SELECT
            SUM(CASE WHEN tx_type='sell' THEN quantity*price_usd ELSE 0 END) -
            SUM(CASE WHEN tx_type='sell' THEN
                quantity * (
                    SELECT SUM(CASE WHEN t2.tx_type='buy' THEN t2.quantity*t2.price_usd ELSE 0 END) /
                           NULLIF(SUM(CASE WHEN t2.tx_type='buy' THEN t2.quantity ELSE 0 END), 0)
                    FROM transactions t2
                    WHERE t2.coin_symbol = transactions.coin_symbol
                      AND t2.tx_date <= transactions.tx_date
                      AND t2.tx_type = 'buy'
                )
            ELSE 0 END)
        FROM transactions
    """).fetchone()[0]
    return result or 0.0
