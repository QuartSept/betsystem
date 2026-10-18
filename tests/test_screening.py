import numpy as np
import pandas as pd

from betsistem.model.movement import movement_test
from betsistem.model.screening import select_leagues


def _probs(rng, n):
    raw = rng.dirichlet([4, 2.5, 3], size=n)
    return raw


def _shift(p, logit_shift):
    lp = np.log(p / (1 - p)) + logit_shift
    q = 1 / (1 + np.exp(-lp))
    return q / q.sum(axis=1, keepdims=True)


def test_movement_detects_informative_model():
    rng = np.random.default_rng(0)
    early = _probs(rng, 2000)
    signal = rng.normal(0, 0.3, size=early.shape)
    model = _shift(early, signal)
    closing = _shift(early, 0.4 * signal + rng.normal(0, 0.1, size=early.shape))
    r = movement_test(model, early, closing, n_boot=500)
    assert r.passes
    assert 0.25 < r.slope < 0.55


def test_movement_rejects_noise_model():
    rng = np.random.default_rng(1)
    early = _probs(rng, 2000)
    model = _shift(early, rng.normal(0, 0.3, size=early.shape))
    closing = _shift(early, rng.normal(0, 0.1, size=early.shape))
    r = movement_test(model, early, closing, n_boot=500)
    assert r.lo < 0 < r.hi


def test_select_leagues_rule():
    table = pd.DataFrame({
        "lig": ["E0", "A", "B", "C", "D"],
        "uygun": [True, True, False, True, True],
        "bilgi kazancı": [0.05, 0.01, 0.09, 0.03, 0.02],
    })
    assert select_leagues(table) == ["C", "D"]  # E0 referans, B uygun değil


def test_movement_single_column():
    rng = np.random.default_rng(2)
    early = rng.uniform(0.2, 0.35, size=(1500, 1))
    signal = rng.normal(0, 0.3, size=early.shape)
    lg = np.log(early / (1 - early))
    model = 1 / (1 + np.exp(-(lg + signal)))
    closing = 1 / (1 + np.exp(-(lg + 0.3 * signal + rng.normal(0, 0.05, size=early.shape))))
    r = movement_test(model, early, closing, n_boot=300, alpha=0.05 / 3, names=("X",))
    assert r.passes and set(r.corr_by_outcome) == {"X"}


def test_bootstrap_alpha_lowers_bound():
    from betsistem.backtest.engine import bootstrap_mean
    v = np.random.default_rng(3).normal(0.01, 0.1, 400)
    assert bootstrap_mean(v, alpha=0.05 / 3)["lo_one_sided"] < bootstrap_mean(v)["lo_one_sided"]
