from datetime import date

import numpy as np
import pytest

from betsistem.model.poisson import fit_poisson, outcome_probabilities
from betsistem.model.timeline import LockedSeasonError, assert_unlocked, decision_date


@pytest.mark.parametrize("match_day, expected", [
    (date(2022, 8, 5), date(2022, 8, 5)),    # Cuma -> aynı gün
    (date(2022, 8, 6), date(2022, 8, 5)),    # Cumartesi -> Cuma
    (date(2022, 8, 8), date(2022, 8, 5)),    # Pazartesi -> önceki Cuma
    (date(2022, 8, 30), date(2022, 8, 30)),  # Salı -> aynı gün
    (date(2022, 9, 1), date(2022, 8, 30)),   # Perşembe -> Salı
])
def test_decision_date(match_day, expected):
    assert decision_date(match_day) == expected


def test_locked_seasons_rejected():
    assert_unlocked(["1920", "2223"])
    with pytest.raises(LockedSeasonError):
        assert_unlocked(["2223", "2324"])


def test_outcome_probabilities():
    ph, pd_, pa = outcome_probabilities(1.5, 1.5)
    assert ph + pd_ + pa == pytest.approx(1.0)
    assert ph == pytest.approx(pa)
    ph, _, pa = outcome_probabilities(2.0, 0.8)
    assert ph > pa


def test_fit_recovers_parameters():
    rng = np.random.default_rng(0)
    teams = [f"T{i}" for i in range(10)]
    att = np.linspace(-0.4, 0.4, 10)
    dfn = np.linspace(0.3, -0.3, 10)
    mu, home_adv = 0.1, 0.25
    home, away, hg, ag = [], [], [], []
    for _ in range(300):  # bol veri: örnekleme gürültüsü toleransın altında kalsın
        for i in range(10):
            for j in range(10):
                if i != j:
                    home.append(teams[i]); away.append(teams[j])
                    hg.append(rng.poisson(np.exp(mu + home_adv + att[i] - dfn[j])))
                    ag.append(rng.poisson(np.exp(mu + att[j] - dfn[i])))
    m = fit_poisson(home, away, hg, ag, l2=0.0)
    assert m.home_advantage == pytest.approx(home_adv, abs=0.05)
    # hücum ve savunma yalnızca toplam sabitine kadar tanımlı: farklara bak
    assert np.allclose(m.attack - m.attack.mean(), att - att.mean(), atol=0.05)
    assert np.allclose(m.defence - m.defence.mean(), dfn - dfn.mean(), atol=0.05)


def test_unseen_team_gets_average_strength():
    m = fit_poisson(["A", "B"], ["B", "A"], [2, 1], [0, 1], l2=1.0)
    assert m.expected_goals("A", "Yeni") != m.expected_goals("B", "Yeni")
    lam_h, lam_a = m.expected_goals("Yeni1", "Yeni2")
    assert lam_h / lam_a == pytest.approx(np.exp(m.home_advantage))
