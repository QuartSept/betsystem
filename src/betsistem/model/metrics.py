"""Olasılık tahmini ölçüleri: log-loss, Brier, kalibrasyon ve eşleştirilmiş bootstrap farkı.

Tüm fonksiyonlar maç başına (n, 3) olasılık matrisi [H, D, A] ve sonuç dizisi ('H'/'D'/'A') alır.
"""

import numpy as np
import pandas as pd

OUTCOMES = ("H", "D", "A")
EPS = 1e-12


def one_hot(results) -> np.ndarray:
    idx = np.array([OUTCOMES.index(r) for r in results])
    out = np.zeros((len(idx), 3))
    out[np.arange(len(idx)), idx] = 1.0
    return out


def log_loss_per_match(probs: np.ndarray, results) -> np.ndarray:
    y = one_hot(results)
    return -np.log(np.clip((probs * y).sum(axis=1), EPS, 1.0))


def brier_per_match(probs: np.ndarray, results) -> np.ndarray:
    """Üç sonuç üzerinden toplanan Brier skoru (0 = mükemmel, 2 = en kötü)."""
    return ((probs - one_hot(results)) ** 2).sum(axis=1)


def calibration_table(probs: np.ndarray, results, bins: int = 10) -> pd.DataFrame:
    """Her sonuç için eşit genişlikte olasılık aralıklarında ortalama tahmin ile gerçekleşme sıklığı."""
    y = one_hot(results)
    edges = np.linspace(0, 1, bins + 1)
    rows = []
    for k, outcome in enumerate(OUTCOMES):
        b = np.clip(np.digitize(probs[:, k], edges) - 1, 0, bins - 1)
        for i in range(bins):
            mask = b == i
            if mask.any():
                rows.append(
                    {
                        "outcome": outcome,
                        "bin": f"{edges[i]:.1f}-{edges[i + 1]:.1f}",
                        "n": int(mask.sum()),
                        "mean_pred": round(float(probs[mask, k].mean()), 4),
                        "observed": round(float(y[mask, k].mean()), 4),
                    }
                )
    return pd.DataFrame(rows)


def expected_calibration_error(probs: np.ndarray, results, bins: int = 10) -> float:
    """Sonuç başına ECE'nin ortalaması: Σ (n_bin/n) |ortalama tahmin − gerçekleşme|."""
    table = calibration_table(probs, results, bins)
    n = len(probs)
    per_outcome = table.assign(gap=(table.mean_pred - table.observed).abs() * table.n / n).groupby("outcome").gap.sum()
    return float(per_outcome.mean())


def paired_bootstrap(diff: np.ndarray, n_boot: int = 5000, seed: int = 20261018) -> tuple[float, float, float]:
    """Maç başına farkların ortalaması ve %95 bootstrap güven aralığı (maçlar yeniden örneklenir)."""
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(diff), size=(n_boot, len(diff)))
    means = diff[idx].mean(axis=1)
    return float(diff.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))
