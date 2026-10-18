"""Hareket testi (karar #46): modelin erken orandan sapması, erken→kapanış hareketini öngörüyor mu?

x = logit(model) − logit(marjsız erken), y = logit(marjsız kapanış) − logit(marjsız erken).
Üç sonuç birlikte y'nin x'e regresyon eğimi; güven aralığı maçlar yeniden örneklenerek (aynı maçın
üç sonucu birlikte) bootstrap ile bulunur.
"""

from dataclasses import dataclass

import numpy as np

N_BOOT = 5000
SEED = 20261018
EPS = 1e-6


def _logit(p):
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    return np.log(p / (1 - p))


def _slope(x: np.ndarray, y: np.ndarray) -> float:
    xc = x - x.mean()
    denom = xc @ xc
    return float(xc @ (y - y.mean()) / denom) if denom > 0 else float("nan")


@dataclass
class MovementResult:
    matches: int
    slope: float
    lo_one_sided: float
    lo: float
    hi: float
    corr_by_outcome: dict[str, float]
    slope_by_outcome: dict[str, float]

    @property
    def passes(self) -> bool:
        return self.slope > 0 and self.lo_one_sided > 0


def movement_test(model: np.ndarray, early: np.ndarray, closing: np.ndarray,
                  n_boot: int = N_BOOT, seed: int = SEED, alpha: float = 0.05,
                  names=("H", "D", "A")) -> MovementResult:
    """Girdiler (n, k) olasılık matrisleri, aynı maç sırasıyla; varsayılan k = 3 [H, D, A].

    Tek sütun (k = 1) verilirse tek bir sonucun (ör. yalnız beraberlik, yalnız üst) testi yapılır.
    lo_one_sided: tek yönlü (1 − α) alt sınır; Faz 10'da α = 0,05/3 (#72).
    """
    model, early, closing = (np.asarray(a, dtype=float).reshape(len(a), -1) for a in (model, early, closing))
    x = _logit(model) - _logit(early)
    y = _logit(closing) - _logit(early)
    n = len(x)
    rng = np.random.default_rng(seed)
    boots = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, n, n)
        boots[b] = _slope(x[idx].ravel(), y[idx].ravel())
    return MovementResult(
        matches=n,
        slope=_slope(x.ravel(), y.ravel()),
        lo_one_sided=float(np.percentile(boots, 100 * alpha)),
        lo=float(np.percentile(boots, 2.5)),
        hi=float(np.percentile(boots, 97.5)),
        corr_by_outcome={o: float(np.corrcoef(x[:, k], y[:, k])[0, 1]) for k, o in enumerate(names)},
        slope_by_outcome={o: _slope(x[:, k], y[:, k]) for k, o in enumerate(names)},
    )
