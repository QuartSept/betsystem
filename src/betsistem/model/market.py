"""Piyasa olasılıkları: oranlardan marjı çıkarılmış 1-X-2 olasılıkları.

Faz 2 kuralı: olasılık = 1/oran, toplamı 1'i aşan kısım (marj) oransal olarak çıkarılır:
p_i = (1/o_i) / Σ(1/o). Model bu olasılıklarla karşılaştırılır.
"""

import sqlite3

import pandas as pd

OUTCOMES = ("H", "D", "A")


def remove_margin(prices: pd.DataFrame) -> pd.DataFrame:
    """H/D/A oran sütunlarından marjsız olasılıklar ve overround (Σ 1/o)."""
    inv = 1.0 / prices[list(OUTCOMES)]
    out = inv.div(inv.sum(axis=1), axis=0)
    out["overround"] = inv.sum(axis=1)
    return out


def market_prices(conn: sqlite3.Connection, bookmaker: str) -> pd.DataFrame:
    """match_id, season, timing ve H/D/A oranları; üç sonucu tam olmayan maçlar atlanır."""
    df = pd.read_sql(
        "SELECT o.match_id, m.season, o.timing, o.outcome, o.price FROM odds o JOIN matches m ON m.id = o.match_id"
        " WHERE o.market = '1X2' AND o.bookmaker = ?",
        conn,
        params=(bookmaker,),
    )
    wide = df.pivot_table(index=["match_id", "season", "timing"], columns="outcome", values="price")
    return wide.reindex(columns=list(OUTCOMES)).dropna()


def fair_probabilities(conn: sqlite3.Connection, bookmaker: str) -> pd.DataFrame:
    return remove_margin(market_prices(conn, bookmaker)).reset_index()
