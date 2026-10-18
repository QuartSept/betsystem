"""Faz 10 fizibilite kapısı (karar #71): sonuçlara ve kuralın CLV'sine bakmadan bahis sayısı ile N karşılaştırılır.

Kullanılanlar: erken fiyatlar, model olasılıkları (walk-forward, yalnız geçmiş maçlarla eğitilir) ve σ için
Aşama 1 vekili (erken fiyat × marjsız kapanış − 1, maç başına sabit tohumla seçilen tek sonuç). Bahis
kuralının seçtiği bahislerin CLV'si, ROI'si veya maç sonuçları hesaplanmaz.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from betsistem.backtest.engine import THRESHOLDS
from betsistem.backtest.sample_size import POWER, required_n
from betsistem.config import MARKET_1X2, MARKET_OU25
from betsistem.model.experiments import LEAGUE_MODELS
from betsistem.model.market import market_prices, remove_margin
from betsistem.model.predict import ModelConfig, load_matches, walk_forward

ALPHA_FAZ10 = 0.05 / 3  # karar #72
DELTA = 0.015
SEED = 20261018
MODEL_SEASONS = ("2021", "2122", "2223")  # 2019/20 ısınma (#32)
MODELLESS_SEASONS = ("1920", "2021", "2122", "2223")  # 10a, ısınma gerekmez (#73)
K_GRID_10A = (0.0, 0.01, 0.02, 0.03)


@dataclass
class Feasibility:
    test: str
    leagues: tuple[str, ...]
    seasons: tuple[str, ...]
    matches: int
    sigma: float
    n_required: int
    counts: dict[float, int]
    notes: list[str] = field(default_factory=list)

    @property
    def feasible_thresholds(self) -> list[float]:
        return [t for t, n in self.counts.items() if n >= self.n_required]

    @property
    def feasible(self) -> bool:
        return bool(self.feasible_thresholds)


def _snapshot(conn, bookmaker, league, timing, market=MARKET_1X2) -> pd.DataFrame:
    p = market_prices(conn, bookmaker, league, market)
    return p.xs(timing, level="timing")


def _sigma_proxy(price: np.ndarray, fair_close: np.ndarray, seed: int = SEED) -> np.ndarray:
    rng = np.random.default_rng(seed)
    j = rng.integers(0, price.shape[1], len(price))
    rows = np.arange(len(price))
    return price[rows, j] * fair_close[rows, j] - 1.0


def _n(values: list[np.ndarray]) -> tuple[float, int]:
    sigma = float(np.concatenate(values).std(ddof=1))
    return sigma, required_n(sigma, DELTA, alpha=ALPHA_FAZ10, power=POWER)


def feasibility_10a(conn, leagues=("E0", "T1"), seasons=MODELLESS_SEASONS) -> Feasibility:
    """10a: o_B365 / o_adil (marjsız Avg erken) oranı en yüksek sonuç; oran > 1 + k ise bahis."""
    best, sig, total = [], [], 0
    for lg in leagues:
        b365 = _snapshot(conn, "B365", lg, "early")
        avg = _snapshot(conn, "Avg", lg, "early")
        ps_close = _snapshot(conn, "PS", lg, "closing")
        ids = b365.index.intersection(avg.index).intersection(ps_close.index)
        ids = ids[ids.get_level_values("season").isin(seasons)]
        cols = ["H", "D", "A"]
        ratio = b365.loc[ids, cols].to_numpy() * remove_margin(avg.loc[ids])[cols].to_numpy()
        best.append(ratio.max(axis=1))
        sig.append(_sigma_proxy(b365.loc[ids, cols].to_numpy(), remove_margin(ps_close.loc[ids])[cols].to_numpy()))
        total += len(ids)
    best_all = np.concatenate(best)
    sigma, n = _n(sig)
    return Feasibility("10a", tuple(leagues), tuple(seasons), total, sigma, n,
                       {k: int((best_all > 1 + k).sum()) for k in K_GRID_10A})


def _over_probability(lam_total: np.ndarray) -> np.ndarray:
    """Bağımsız Poisson: toplam gol ~ Poisson(λ_ev + λ_dep); P(toplam > 2,5) = 1 − P(≤ 2)."""
    lam = np.asarray(lam_total, dtype=float)
    return 1.0 - np.exp(-lam) * (1.0 + lam + lam**2 / 2.0)


def model_ou_probabilities(conn, league: str, config: ModelConfig, seasons=MODEL_SEASONS) -> pd.DataFrame:
    if config.dixon_coles:
        raise ValueError("Alt/üst olasılığı bu fonksiyonda bağımsız Poisson varsayar; Dixon-Coles modeli desteklenmez")
    preds = walk_forward(load_matches(conn, league), seasons, config).set_index("match_id")
    p_over = _over_probability(preds.lambda_home + preds.lambda_away)
    return pd.DataFrame({"O": p_over, "U": 1.0 - p_over}, index=preds.index)


def feasibility_10c(conn, leagues=("E0", "B1"), seasons=MODEL_SEASONS) -> Feasibility:
    """10c: model P(üst/alt) × Pinnacle alt/üst erken oranı − 1 en yüksek taraf; > eşik ise bahis."""
    edges, sig, total = [], [], 0
    for lg in leagues:
        model = model_ou_probabilities(conn, lg, LEAGUE_MODELS[lg], seasons)
        early = _snapshot(conn, "PS", lg, "early", MARKET_OU25).reset_index(level="season", drop=True)
        close = _snapshot(conn, "PS", lg, "closing", MARKET_OU25).reset_index(level="season", drop=True)
        ids = model.index.intersection(early.index).intersection(close.index)
        cols = ["O", "U"]
        e = model.loc[ids, cols].to_numpy() * early.loc[ids, cols].to_numpy() - 1.0
        edges.append(e.max(axis=1))
        sig.append(_sigma_proxy(early.loc[ids, cols].to_numpy(), remove_margin(close.loc[ids], cols)[cols].to_numpy()))
        total += len(ids)
    best = np.concatenate(edges)
    sigma, n = _n(sig)
    return Feasibility("10c", tuple(leagues), tuple(seasons), total, sigma, n,
                       {t: int((best > t).sum()) for t in THRESHOLDS})


def feasibility_10d(conn, leagues=("T1", "F2", "I2", "E2", "E3"), seasons=MODEL_SEASONS) -> Feasibility:
    """10d (Faz 4 aşaması): beraberlik değeri = model P(X) × Pinnacle erken X oranı − 1 > eşik.

    Gerçek test her ligde Faz 3 boru hattıyla seçilen modeli kullanır. Fizibilite, ayar seçimi gerektirmeyen
    Faz 2 temel modeliyle (ModelConfig()) yaklaşık olarak hesaplanır; sayılar bu nedenle yaklaşıktır.
    """
    edges, sig, total = [], [], 0
    for lg in leagues:
        preds = walk_forward(load_matches(conn, lg), seasons, ModelConfig()).set_index("match_id")
        early = _snapshot(conn, "PS", lg, "early").reset_index(level="season", drop=True)
        close = _snapshot(conn, "PS", lg, "closing").reset_index(level="season", drop=True)
        ids = preds.index.intersection(early.index).intersection(close.index)
        edges.append(preds.loc[ids, "p_draw"].to_numpy() * early.loc[ids, "D"].to_numpy() - 1.0)
        fair_d = remove_margin(close.loc[ids])["D"].to_numpy()
        sig.append(early.loc[ids, "D"].to_numpy() * fair_d - 1.0)  # yalnız beraberlik bahsi
        total += len(ids)
    best = np.concatenate(edges)
    sigma, n = _n(sig)
    return Feasibility("10d", tuple(leagues), tuple(seasons), total, sigma, n,
                       {t: int((best > t).sum()) for t in THRESHOLDS},
                       notes=["Sayılar Faz 2 temel modeliyle yaklaşık; gerçek test Faz 3 modeliyle."])


def render(f: Feasibility) -> str:
    rows = "\n".join(f"| {t:g} | {n} | {'evet' if n >= f.n_required else 'hayır'} |" for t, n in f.counts.items())
    verdict = (f"**Fizibil.** Fizibil eşikler: {', '.join(f'{t:g}' for t in f.feasible_thresholds)}."
               if f.feasible else "**Yetersiz güç:** hiçbir eşik N'ye ulaşmıyor; test sonuç analizine girmez (#71).")
    notes = "".join(f"\n- {n}" for n in f.notes)
    return (
        f"- Ligler: {', '.join(f.leagues)}; sezonlar: {', '.join(f.seasons)}; maç: {f.matches}.\n"
        f"- σ = {f.sigma:.4f}; α = {ALPHA_FAZ10:.4f} (tek yönlü), güç = {POWER}, δ = {DELTA}: **N = {f.n_required}**."
        f"{notes}\n\n| eşik | bahis sayısı | ≥ N |\n| --- | --- | --- |\n{rows}\n\n{verdict}\n"
    )
