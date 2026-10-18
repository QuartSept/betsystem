"""Faz 4 backtest motoru: bahis seçimi, CLV, ROI, en büyük düşüş ve çeyrek Kelly (karar #38–#41).

Girdi tahminleri walk-forward üretilmiş olmalıdır; motor yalnızca kuralları uygular.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

OUTCOMES = ("H", "D", "A")
PROB_COLS = {"H": "p_home", "D": "p_draw", "A": "p_away"}
THRESHOLDS = (0.0, 0.01, 0.02, 0.03, 0.05, 0.075, 0.10)  # karar #40
KELLY_FRACTION = 0.25
KELLY_START = 100.0
N_BOOT = 5000
SEED = 20261018


def select_bets(preds: pd.DataFrame, early: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Karar #38: maç başına değeri en yüksek tek sonuç; değer > eşik ise bahis.

    preds: match_id, p_home, p_draw, p_away (+ bilgi sütunları). early: match_id, H, D, A (bahis oranları).
    Oranı eksik maç birleştirmede düşer: bahis yok, başka şirketle doldurma yok (karar #27).
    """
    df = preds.merge(early, on="match_id", how="inner")
    edges = np.column_stack([df[PROB_COLS[o]] * df[o] - 1.0 for o in OUTCOMES])
    best = edges.argmax(axis=1)
    rows = np.arange(len(df))
    out = df.drop(columns=list(OUTCOMES)).copy()
    out["outcome"] = np.array(OUTCOMES)[best]
    out["price"] = df[list(OUTCOMES)].to_numpy()[rows, best]
    out["p_model"] = df[[PROB_COLS[o] for o in OUTCOMES]].to_numpy()[rows, best]
    out["edge"] = edges[rows, best]
    return out[out.edge > threshold].reset_index(drop=True)


def settle(bets: pd.DataFrame, results: pd.Series, closing_fair: pd.DataFrame) -> pd.DataFrame:
    """Sonuç ve CLV ekler. results: match_id -> ftr. closing_fair: match_id, H, D, A (marjsız olasılık)."""
    out = bets.merge(closing_fair, on="match_id", how="left", suffixes=("", "_close"))
    p_close = out.apply(lambda r: r[r.outcome], axis=1) if len(out) else pd.Series(dtype=float)
    out = out.drop(columns=list(OUTCOMES))
    out["p_close"] = p_close
    out["clv"] = out["price"] * out["p_close"] - 1.0  # karar #39
    out["won"] = out.match_id.map(results).to_numpy() == out.outcome.to_numpy()
    out["pnl"] = np.where(out.won, out.price - 1.0, -1.0)
    return out


def max_drawdown(pnl_series) -> float:
    cum = np.cumsum(np.asarray(pnl_series, dtype=float))
    peak = np.maximum.accumulate(np.concatenate([[0.0], cum]))[1:]
    return float((peak - cum).max()) if len(cum) else 0.0


def kelly_path(bets: pd.DataFrame) -> pd.Series:
    """Çeyrek Kelly kasa yolu. Aynı karar gününe ait bahislerin payı o günün başındaki kasadan hesaplanır."""
    bankroll = KELLY_START
    path = []
    for _, group in bets.sort_values(["decision_date", "match_id"]).groupby("decision_date", sort=True):
        frac = KELLY_FRACTION * (group.p_model * group.price - 1.0) / (group.price - 1.0)
        stakes = bankroll * frac.clip(lower=0.0)
        bankroll += float((stakes * np.where(group.won, group.price - 1.0, -1.0)).sum())
        path.append(bankroll)
    return pd.Series(path, dtype=float)


def bootstrap_mean(values, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    v = np.asarray(values, dtype=float)
    if len(v) == 0:
        return {"mean": np.nan, "lo_one_sided": np.nan, "lo": np.nan, "hi": np.nan}
    rng = np.random.default_rng(seed)
    means = v[rng.integers(0, len(v), size=(n_boot, len(v)))].mean(axis=1)
    return {
        "mean": float(v.mean()),
        "lo_one_sided": float(np.percentile(means, 5)),  # karar #41
        "lo": float(np.percentile(means, 2.5)),
        "hi": float(np.percentile(means, 97.5)),
    }


@dataclass
class Summary:
    bets: int
    clv: dict
    roi: dict
    max_drawdown: float
    kelly_final: float
    kelly_max_drawdown_pct: float

    def passes(self, n_required: int) -> bool:
        """Karar #42: en az N bahis, ortalama CLV > 0 ve tek yönlü alt sınır > 0."""
        return self.bets >= n_required and self.clv["mean"] > 0 and self.clv["lo_one_sided"] > 0


def summarize(settled: pd.DataFrame) -> Summary:
    ordered = settled.sort_values(["decision_date", "match_id"])
    kelly = kelly_path(ordered) if len(ordered) else pd.Series([KELLY_START])
    peak = np.maximum.accumulate(np.concatenate([[KELLY_START], kelly.to_numpy()]))[1:]
    kelly_dd = float(((peak - kelly.to_numpy()) / peak).max()) if len(kelly) else 0.0
    return Summary(
        bets=len(settled),
        clv=bootstrap_mean(settled.clv),
        roi=bootstrap_mean(settled.pnl),
        max_drawdown=max_drawdown(ordered.pnl),
        kelly_final=float(kelly.iloc[-1]),
        kelly_max_drawdown_pct=kelly_dd,
    )


def choose_threshold(summaries: dict[float, Summary], n_required: int) -> float:
    """Karar #40: en az N bahis verenler arasında ortalama CLV'si en yüksek eşik; yoksa en düşük eşik."""
    eligible = {t: s for t, s in summaries.items() if s.bets >= n_required}
    if not eligible:
        return min(summaries)
    return max(eligible, key=lambda t: eligible[t].clv["mean"])
