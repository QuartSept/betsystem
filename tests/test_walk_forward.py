from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from betsistem.model import metrics
from betsistem.model.predict import ModelConfig, walk_forward
from betsistem.model.timeline import LockedSeasonError


def _season(start: date, season: str, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    teams = [f"T{i}" for i in range(6)]
    rows, d, mid = [], start, seed * 1000
    for rnd in range(10):
        for i in range(0, 6, 2):
            h, a = teams[(i + rnd) % 6], teams[(i + 1 + 2 * rnd) % 6]
            if h == a:
                continue
            hg, ag = rng.poisson(1.5), rng.poisson(1.1)
            rows.append({"match_id": mid, "season": season, "match_date": d, "home": h, "away": a,
                         "fthg": hg, "ftag": ag, "ftr": "H" if hg > ag else ("A" if hg < ag else "D")})
            mid += 1
        d += timedelta(days=7)  # her hafta Cumartesi
    return pd.DataFrame(rows)


@pytest.fixture
def matches():
    return pd.concat([_season(date(2019, 8, 10), "1920", 1), _season(date(2020, 8, 8), "2021", 2)], ignore_index=True)


def test_future_results_do_not_change_past_predictions(matches):
    before = walk_forward(matches, seasons=["2021"])
    cutoff = date(2020, 9, 1)
    changed = matches.copy()
    future = changed.match_date >= cutoff
    changed.loc[future, ["fthg", "ftag"]] = 9  # gelecekteki skorları boz
    after = walk_forward(changed, seasons=["2021"])

    past_ids = set(matches[(matches.season == "2021") & (matches.match_date < cutoff)].match_id)
    b = before.set_index("match_id").loc[sorted(past_ids)]
    a = after.set_index("match_id").loc[sorted(past_ids)]
    pd.testing.assert_frame_equal(b, a)


def test_training_uses_only_matches_before_decision_date(matches):
    preds = walk_forward(matches, seasons=["2021"], config=ModelConfig(window_days=3650))
    for r in preds.itertuples():
        dd = date.fromisoformat(r.decision_date)
        assert r.train_matches == (matches.match_date < dd).sum()


def test_locked_seasons_cannot_be_predicted(matches):
    with pytest.raises(LockedSeasonError):
        walk_forward(matches, seasons=["2324"])


def test_metrics_known_values():
    probs = np.array([[0.5, 0.3, 0.2], [0.2, 0.3, 0.5]])
    assert metrics.log_loss_per_match(probs, ["H", "D"]) == pytest.approx([-np.log(0.5), -np.log(0.3)])
    assert metrics.brier_per_match(probs, ["H", "H"]) == pytest.approx([0.38, 0.98])
    mean, lo, hi = metrics.paired_bootstrap(np.full(50, 0.1))
    assert (mean, lo, hi) == pytest.approx((0.1, 0.1, 0.1))


def test_xg_target_mix_and_fallback():
    from betsistem.model.predict import _targets
    train = pd.DataFrame({"fthg": [2, 1], "ftag": [0, 1], "home_xg": [1.0, None], "away_xg": [0.4, None]})
    hg, ag = _targets(train, 0.5)
    assert list(hg) == [1.5, 1.0]  # xG yoksa gol
    assert list(ag) == [0.2, 1.0]
    assert list(_targets(train, 0.0)[0]) == [2.0, 1.0]


def test_time_weight_changes_predictions(matches):
    plain = walk_forward(matches, seasons=["2021"], config=ModelConfig(window_days=3650))
    weighted = walk_forward(matches, seasons=["2021"], config=ModelConfig(window_days=3650, xi=0.01))
    assert not np.allclose(plain.p_home, weighted.p_home)


def test_promoted_flags():
    from betsistem.model.predict import promoted_flags
    df = pd.DataFrame({
        "season": ["1920", "1920", "2021", "2021"],
        "home": ["A", "B", "A", "C"],
        "away": ["B", "A", "C", "A"],
    })
    flags = promoted_flags(df)
    assert flags.home_promoted.tolist() == [False, False, False, True]  # ilk sezonda kimse yeni çıkan değil
    assert flags.away_promoted.tolist() == [False, False, True, False]
