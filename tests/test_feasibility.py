import numpy as np
import pytest
from scipy.stats import poisson

from betsistem.asama2.feasibility import Feasibility, _over_probability, _sigma_proxy


def test_over_probability_matches_poisson():
    lam = np.array([1.5, 2.6, 3.4])
    assert _over_probability(lam) == pytest.approx(1 - poisson.cdf(2, lam))


def test_feasible_thresholds():
    f = Feasibility("x", ("E0",), ("2021",), 100, 0.1, 50, {0.0: 80, 0.01: 50, 0.02: 49})
    assert f.feasible_thresholds == [0.0, 0.01]
    assert f.feasible
    assert not Feasibility("x", ("E0",), ("2021",), 100, 0.1, 500, {0.0: 80}).feasible


def test_sigma_proxy_one_outcome_per_match():
    price = np.array([[2.0, 3.0, 4.0]] * 4)
    fair = np.array([[0.5, 1 / 3, 0.25]] * 4)
    assert _sigma_proxy(price, fair) == pytest.approx(np.zeros(4))


def test_shin_probabilities():
    import pandas as pd
    from betsistem.model.market import remove_margin, remove_margin_shin, shin_probabilities
    odds = np.array([1.5, 4.2, 7.5])
    p = shin_probabilities(odds)
    prop = (1 / odds) / (1 / odds).sum()
    assert p.sum() == pytest.approx(1.0)
    assert p[2] < prop[2] and p[0] > prop[0]  # uzak ihtimal küçülür, favori büyür
    assert shin_probabilities(np.array([2.0, 2.0])) == pytest.approx([0.5, 0.5])
    df = pd.DataFrame([odds], columns=["H", "D", "A"])
    assert remove_margin_shin(df)[["H", "D", "A"]].to_numpy()[0] == pytest.approx(p)
    assert remove_margin_shin(df)["overround"].iloc[0] == pytest.approx(remove_margin(df)["overround"].iloc[0])
