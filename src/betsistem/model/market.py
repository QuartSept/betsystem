"""Piyasa olasılıkları: oranlardan marjı çıkarılmış 1-X-2 olasılıkları.

Faz 2 kuralı: olasılık = 1/oran, toplamı 1'i aşan kısım (marj) oransal olarak çıkarılır:
p_i = (1/o_i) / Σ(1/o). Model bu olasılıklarla karşılaştırılır.
"""

import sqlite3

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from betsistem.config import MARKET_1X2, MARKET_OUTCOMES

OUTCOMES = ("H", "D", "A")


def remove_margin(prices: pd.DataFrame, outcomes=OUTCOMES) -> pd.DataFrame:
    """Oran sütunlarından (varsayılan H/D/A) marjsız olasılıklar ve overround (Σ 1/o)."""
    inv = 1.0 / prices[list(outcomes)]
    out = inv.div(inv.sum(axis=1), axis=0)
    out["overround"] = inv.sum(axis=1)
    return out


def shin_probabilities(odds) -> np.ndarray:
    """Shin (1993) yöntemiyle marjsız olasılıklar: içeriden bilgili bahis payı z ile favori–uzak ihtimal
    eğilimini hesaba katar. p_i = (√(z² + 4(1 − z)π_i²/S) − z) / (2(1 − z)), π_i = 1/o_i, S = Σπ_i; Σp_i = 1."""
    pi = 1.0 / np.asarray(odds, dtype=float)
    s = pi.sum()
    if s <= 1.0:
        return pi / s  # marj yoksa oransal ile aynı

    def p_of(z):
        return (np.sqrt(z**2 + 4 * (1 - z) * pi**2 / s) - z) / (2 * (1 - z))

    z = brentq(lambda z: p_of(z).sum() - 1.0, 0.0, 0.5)
    return p_of(z)


def remove_margin_shin(prices: pd.DataFrame, outcomes=OUTCOMES) -> pd.DataFrame:
    """remove_margin ile aynı biçimde, Shin yöntemiyle (karar #84, #88)."""
    cols = list(outcomes)
    probs = np.vstack([shin_probabilities(row) for row in prices[cols].to_numpy()]) if len(prices) else         np.empty((0, len(cols)))
    out = pd.DataFrame(probs, index=prices.index, columns=cols)
    out["overround"] = (1.0 / prices[cols]).sum(axis=1)
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
