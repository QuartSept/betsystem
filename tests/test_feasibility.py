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
