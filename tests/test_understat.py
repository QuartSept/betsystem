import json
from pathlib import Path

import pytest

from betsistem.data.db import UnknownTeamError, connect, init_db
from betsistem.data.football_data import load_football_data
from betsistem.data.raw import import_football_data, store_raw
from betsistem.data.understat import load_understat, understat_year

FIXTURE = Path(__file__).parent / "fixtures" / "E0_sample.csv"


def _match(mid, home, away, xg_h, xg_a, dt):
    return {
        "id": mid, "isResult": True, "datetime": dt,
        "h": {"title": home}, "a": {"title": away},
        "xG": {"h": str(xg_h), "a": str(xg_a)},
    }


def _payload(dates):
    teams = {
        str(i): {"title": m["h"]["title"], "history": [{"h_a": "h", "date": m["datetime"], "npxG": 0.5, "npxGA": 0.4}]}
        for i, m in enumerate(dates)
    }
    return json.dumps({"dates": dates, "teams": teams, "players": []}).encode()


@pytest.fixture
def conn(tmp_path):
    c = connect(":memory:")
    init_db(c)
    vid = import_football_data(c, "E0", "2223", FIXTURE, raw_dir=tmp_path)
    load_football_data(c, vid, raw_dir=tmp_path)
    yield c
    c.close()


def _store(conn, tmp_path, dates):
    return store_raw(conn, _payload(dates), source="understat", league="E0", season="2223",
                     origin="test", suffix=".json", raw_dir=tmp_path)


def test_understat_year():
    assert understat_year("2223") == "2022"
    assert understat_year("9900") == "1999"


def test_load_maps_teams_and_xg(conn, tmp_path):
    vid = _store(conn, tmp_path, [
        _match("1", "Crystal Palace", "Arsenal", 1.2, 1.4, "2022-08-05 19:00:00"),
        _match("2", "Fulham", "Liverpool", 1.1, 2.0, "2022-08-09 11:30:00"),  # tarih 3 gün kaymış
    ])
    res = load_understat(conn, vid, raw_dir=tmp_path)
    assert res.matched == 2
    assert len(res.date_mismatches) == 1
    row = conn.execute("SELECT home_xg, away_xg, home_npxg, away_npxg FROM match_xg WHERE external_id = '1'").fetchone()
    assert tuple(row) == (1.2, 1.4, 0.5, 0.4)


def test_alias_table_used(conn, tmp_path):
    conn.execute("INSERT INTO teams (name) VALUES ('Man City')")
    conn.execute("INSERT INTO teams (name) VALUES ('Wolves')")
    from betsistem.data.db import resolve_team
    assert resolve_team(conn, "understat", "Manchester City") == \
        conn.execute("SELECT id FROM teams WHERE name = 'Man City'").fetchone()[0]


def test_unknown_team_fails_without_partial_write(conn, tmp_path):
    vid = _store(conn, tmp_path, [
        _match("1", "Crystal Palace", "Arsenal", 1.2, 1.4, "2022-08-05 19:00:00"),
        _match("9", "Atlantis FC", "Arsenal", 0.1, 0.1, "2022-08-06 14:00:00"),
    ])
    with pytest.raises(UnknownTeamError, match="Atlantis FC"):
        load_understat(conn, vid, raw_dir=tmp_path)
    assert conn.execute("SELECT COUNT(*) FROM match_xg").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM team_aliases WHERE source = 'understat'").fetchone()[0] == 0
