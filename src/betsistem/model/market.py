"""Piyasa olasılıkları: oranlardan marjı çıkarılmış 1-X-2 olasılıkları.

Faz 2 kuralı: olasılık = 1/oran, toplamı 1'i aşan kısım (marj) oransal olarak çıkarılır:
p_i = (1/o_i) / Σ(1/o). Model bu olasılıklarla karşılaştırılır.
"""

import sqlite3

import pandas as pd

from betsistem.config import MARKET_1X2, MARKET_OUTCOMES

OUTCOMES = ("H", "D", "A")


def remove_margin(prices: pd.DataFrame, outcomes=OUTCOMES) -> pd.DataFrame:
    """Oran sütunlarından (varsayılan H/D/A) marjsız olasılıklar ve overround (Σ 1/o)."""
    inv = 1.0 / prices[list(outcomes)]
    out = inv.div(inv.sum(axis=1), axis=0)
    out["overround"] = inv.sum(axis=1)
    return out


def market_prices(
    conn: sqlite3.Connection, bookmaker: str, league: str | None = "E0", market: str = MARKET_1X2
) -> pd.DataFrame:
    """match_id, season, timing ve H/D/A oranları; üç sonucu tam olmayan maçlar atlanır.

    league=None tüm ligleri döndürür; varsayılan Premier League, ligler karışmasın diye.
    """
    sql = (
        "SELECT o.match_id, m.season, o.timing, o.outcome, o.price FROM odds o JOIN matches m ON m.id = o.match_id"
        " WHERE o.market = ? AND o.bookmaker = ?"
    )
    params: tuple = (market, bookmaker)
    if league is not None:
        sql += " AND m.league = ?"
        params += (league,)
    df = pd.read_sql(sql, conn, params=params)
    wide = df.pivot_table(index=["match_id", "season", "timing"], columns="outcome", values="price")
    return wide.reindex(columns=list(MARKET_OUTCOMES[market])).dropna()


def fair_probabilities(conn: sqlite3.Connection, bookmaker: str, league: str | None = "E0") -> pd.DataFrame:
    return remove_margin(market_prices(conn, bookmaker, league)).reset_index()
