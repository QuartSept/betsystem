import json
import sqlite3

import numpy as np
import pandas as pd
import pytest

from betsistem.backtest import engine
from betsistem.backtest.run import CONFIRM_PHRASE, FinalSetAlreadyOpened, open_final_set
from betsistem.data.db import connect, init_db
from betsistem.model.predict import walk_forward
from betsistem.model.timeline import FinalSetToken, LockedSeasonError, assert_unlocked


def _preds():
    return pd.DataFrame({
        "match_id": [1, 2, 3],
        "decision_date": ["2021-01-01", "2021-01-01", "2021-01-08"],
        "p_home": [0.60, 0.32, 0.34],
        "p_draw": [0.25, 0.28, 0.33],
        "p_away": [0.15, 0.40, 0.33],
    })


def _early():
    return pd.DataFrame({"match_id": [1, 2, 3], "H": [1.80, 3.0, 2.9], "D": [3.6, 3.4, 3.3], "A": [5.0, 2.4, 2.5]})


def test_select_bets_one_per_match_best_edge():
    bets = engine.select_bets(_preds(), _early(), threshold=0.0)
    # maç 1: H değeri 0.08; maç 2: en iyi değer −0.04 -> bahis yok; maç 3: D 0.089
    assert bets.match_id.tolist() == [1, 3]
    assert bets.outcome.tolist() == ["H", "D"]
    assert bets.edge.round(3).tolist() == [0.08, 0.089]
    assert engine.select_bets(_preds(), _early(), threshold=0.085).match_id.tolist() == [3]


def test_missing_bet_price_means_no_bet():
    bets = engine.select_bets(_preds(), _early()[_early().match_id != 1], threshold=0.0)
    assert 1 not in bets.match_id.tolist()


def test_settle_clv_and_pnl():
    bets = engine.select_bets(_preds(), _early(), 0.0)
    closing = pd.DataFrame({"match_id": [1, 3], "H": [0.58, 0.30], "D": [0.26, 0.32], "A": [0.16, 0.38]})
    s = engine.settle(bets, pd.Series({1: "H", 3: "A"}), closing)
    assert s.clv.round(4).tolist() == [round(1.80 * 0.58 - 1, 4), round(3.3 * 0.32 - 1, 4)]
    assert s.pnl.tolist() == [pytest.approx(0.8), -1.0]


def test_max_drawdown():
    assert engine.max_drawdown([1, -1, -1, 2, -3]) == 3.0
    assert engine.max_drawdown([-1, -1]) == 2.0


def test_kelly_uses_bankroll_at_start_of_decision_day():
    bets = pd.DataFrame({"decision_date": ["d1", "d1"], "match_id": [1, 2], "p_model": [0.6, 0.6],
                         "price": [2.0, 2.0], "won": [True, False]})
    path = engine.kelly_path(bets)
    # pay = 0.25 * 0.2 / 1 = 0.05 -> iki bahis de 5 birim; +5 −5
    assert path.tolist() == [100.0]


def test_choose_threshold_rule():
    def s(bets, clv):
        return engine.Summary(bets, {"mean": clv, "lo_one_sided": clv}, {"mean": 0}, 0, 100, 0)
    sums = {0.0: s(500, -0.02), 0.02: s(250, -0.01), 0.05: s(100, 0.03)}
    assert engine.choose_threshold(sums, 202) == 0.02  # 0.05 yeterli bahis vermiyor
    assert engine.choose_threshold({0.0: s(50, 0), 0.05: s(10, 0.1)}, 202) == 0.0


def test_passes():
    ok = engine.Summary(202, {"mean": 0.01, "lo_one_sided": 0.001}, {}, 0, 0, 0)
    assert ok.passes(202)
    assert not engine.Summary(201, ok.clv, {}, 0, 0, 0).passes(202)
    assert not engine.Summary(300, {"mean": 0.01, "lo_one_sided": -0.001}, {}, 0, 0, 0).passes(202)


@pytest.fixture
def conn():
    c = connect(":memory:")
    init_db(c)
    yield c
    c.close()


def test_final_set_opens_once(conn):
    with pytest.raises(PermissionError):
        open_final_set(conn, "B1", "{}", 0.02, "evet")
    token = open_final_set(conn, "B1", "{}", 0.02, CONFIRM_PHRASE)
    assert isinstance(token, FinalSetToken)
    assert_unlocked(["2324"], token)
    with pytest.raises(FinalSetAlreadyOpened):
        open_final_set(conn, "B1", "{}", 0.02, CONFIRM_PHRASE)
    open_final_set(conn, "E0", "{}", 0.02, CONFIRM_PHRASE)  # başka lig ayrı açılır


def test_final_set_record_is_tamper_proof(conn):
    open_final_set(conn, "B1", "{}", 0.02, CONFIRM_PHRASE)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM final_set_runs")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE final_set_runs SET league = 'E0'")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE final_set_runs SET threshold = 0.05")
    conn.execute("UPDATE final_set_runs SET result_json = '{}'")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE final_set_runs SET result_json = '{\"x\": 1}'")


def test_locked_seasons_need_token():
    with pytest.raises(LockedSeasonError):
        assert_unlocked(["2425"])
    with pytest.raises(LockedSeasonError):
        walk_forward(pd.DataFrame(columns=["season", "home", "away", "match_date", "fthg", "ftag"]), ["2425"])


def test_faz11_window_locked(conn):
    from betsistem.asama2.faz11 import CONFIRM_PHRASE as P11, Faz11AlreadyOpened, open_faz11_window
    from betsistem.model.timeline import Faz11Token
    with pytest.raises(LockedSeasonError, match="Faz 11"):
        assert_unlocked(["2223", "2526"])
    with pytest.raises(LockedSeasonError):
        assert_unlocked(["2627"], FinalSetToken("E0"))  # final set izni pencereyi açmaz
    with pytest.raises(PermissionError):
        open_faz11_window(conn, "10a", "{}", "evet")
    token = open_faz11_window(conn, "10a", "{}", P11)
    assert isinstance(token, Faz11Token)
    assert_unlocked(["2526", "2627"], token)
    with pytest.raises(Faz11AlreadyOpened):
        open_faz11_window(conn, "10a", "{}", P11)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM faz11_runs")


def test_faz10_runs_once(conn):
    from betsistem.asama2.faz10 import Faz10AlreadyRun, _assert_not_run
    _assert_not_run(conn)
    conn.execute("INSERT INTO faz10_runs (test, run_at, result) VALUES ('10a', 'x', 'y')")
    with pytest.raises(Faz10AlreadyRun):
        _assert_not_run(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE faz10_runs SET result = 'z'")
