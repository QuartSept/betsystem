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
