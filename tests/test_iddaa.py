import sqlite3
from datetime import datetime

import openpyxl
import pytest

from betsistem.data.db import connect, init_db
from betsistem.data.fixtures import TR, fixtures_log, import_fixtures
from betsistem.data.iddaa import COLUMNS, import_iddaa
from betsistem.data.raw import RawDataError

FIXTURES = "Div,Date,Time,HomeTeam,AwayTeam,AvgH,AvgD,AvgA\n" \
           "E0,24/10/2026,15:00,Arsenal,Chelsea,1.9,3.6,4.2\n" \
           "E0,24/10/2026,17:30,Man United,Nott'm Forest,1.7,3.9,4.8\n" \
           "T1,24/10/2026,19:00,Galatasaray,Fenerbahce,2.1,3.5,3.3\n"
ROW = ["2026-10-23 19:40", "E0", "2026-10-24", "17:00", "Arsenal", "Chelsea", "1,85", 3.6, 4.1, 1,
       "fixtures_20261023_1930.csv", None]


@pytest.fixture
def conn():
    c = connect(":memory:")
    init_db(c)
    yield c
    c.close()


@pytest.fixture
def env(conn, tmp_path):
    raw = tmp_path / "raw"
    fx = tmp_path / "fixtures_20261023_1930.csv"
    fx.write_text(FIXTURES, encoding="utf-8")
    import_fixtures(conn, fx, downloaded_at=datetime(2026, 10, 23, 19, 30, tzinfo=TR), raw_dir=raw)
    return conn, tmp_path, raw


def _xlsx(tmp_path, *rows, name="iddaa.xlsx"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Kayıtlar"
    ws.append([*COLUMNS, "iddaa_marji"])
    for r in rows:
        ws.append(list(r))
    ws.append([None] * len(COLUMNS) + ["=1"])  # yalnızca formül sütunu dolu boş satır
    p = tmp_path / name
    wb.save(p)
    return p


def test_import_and_cumulative(env):
    conn, tmp, raw = env
    res = import_iddaa(conn, _xlsx(tmp, ROW), raw_dir=raw)
    assert (res.added, res.already_present, res.warnings) == (1, 0, [])
    row = conn.execute("SELECT * FROM iddaa_odds_log").fetchone()
    assert (row["league"], row["mbs"], row["price_home"], row["recorded_at"]) == ("E0", 1, 1.85, "2026-10-23T19:40+03:00")
    fx_vid = conn.execute("SELECT data_version_id FROM fixture_downloads").fetchone()[0]
    assert row["fixtures_version_id"] == fx_vid

    second = ["2026-10-23 20:10", "E0", "2026-10-24", "17:30", "Man United", "Nott'm Forest", 1.72, "3,9", 4.7, 2,
              "fixtures_20261023_1930.csv", "not"]
    res = import_iddaa(conn, _xlsx(tmp, ROW, second), raw_dir=raw)
    assert (res.added, res.already_present) == (1, 1)


def test_unknown_team_rejected_with_suggestion(env):
    conn, tmp, raw = env
    bad = list(ROW)
    bad[4] = "Arsenall"
    with pytest.raises(RawDataError, match="Arsenal"):
        import_iddaa(conn, _xlsx(tmp, bad), raw_dir=raw)
    assert conn.execute("SELECT COUNT(*) FROM iddaa_odds_log").fetchone()[0] == 0


def test_whole_file_rejected_if_any_row_bad(env):
    conn, tmp, raw = env
    bad = list(ROW)
    bad[0], bad[4], bad[5] = "2026-10-23 19:45", "Galatasaray", "Fenerbahce"  # lig yanlış (T1 maçı E0 diye)
    with pytest.raises(RawDataError, match="Satır 3"):
        import_iddaa(conn, _xlsx(tmp, ROW, bad), raw_dir=raw)
    assert conn.execute("SELECT COUNT(*) FROM iddaa_odds_log").fetchone()[0] == 0


def test_missing_fixture_file(env):
    conn, tmp, raw = env
    bad = list(ROW)
    bad[10] = "fixtures_yok.csv"
    with pytest.raises(RawDataError, match="import-fixtures"):
        import_iddaa(conn, _xlsx(tmp, bad), raw_dir=raw)


def test_changed_prices_rejected(env):
    conn, tmp, raw = env
    import_iddaa(conn, _xlsx(tmp, ROW), raw_dir=raw)
    changed = list(ROW)
    changed[6] = 1.95
    with pytest.raises(RawDataError, match="değiştirilemez"):
        import_iddaa(conn, _xlsx(tmp, changed, name="b.xlsx"), raw_dir=raw)


def test_gap_warning(env):
    conn, tmp, raw = env
    late = list(ROW)
    late[0] = "2026-10-23 23:00"
    res = import_iddaa(conn, _xlsx(tmp, late), raw_dir=raw)
    assert res.added == 1 and "2 saatten fazla" in res.warnings[0]


def test_log_is_append_only(env):
    conn, tmp, raw = env
    import_iddaa(conn, _xlsx(tmp, ROW), raw_dir=raw)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE iddaa_odds_log SET mbs = 2")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM iddaa_odds_log")


def test_fixture_versions_and_change_log(conn, tmp_path):
    raw = tmp_path / "raw"
    a = tmp_path / "fixtures_1.csv"
    b = tmp_path / "fixtures_2.csv"
    d = tmp_path / "fixtures_3.csv"
    a.write_text(FIXTURES, encoding="utf-8")
    b.write_text(FIXTURES, encoding="utf-8")
    d.write_text(FIXTURES.replace("1.9", "1.95"), encoding="utf-8")
    r1 = import_fixtures(conn, a, downloaded_at=datetime(2026, 10, 23, 12, 0, tzinfo=TR), raw_dir=raw)
    r2 = import_fixtures(conn, b, downloaded_at=datetime(2026, 10, 23, 14, 0, tzinfo=TR), raw_dir=raw)
    r3 = import_fixtures(conn, d, downloaded_at=datetime(2026, 10, 23, 16, 0, tzinfo=TR), raw_dir=raw)
    assert r1.data_version_id == r2.data_version_id != r3.data_version_id
    assert (r1.new_content, r2.new_content, r3.new_content) == (True, False, True)
    assert fixtures_log(conn)["değişti"].tolist() == [True, False, True]
    # aynı adla başka içerik reddedilir
    a.write_text(FIXTURES.replace("1.9", "2.0"), encoding="utf-8")
    with pytest.raises(RawDataError, match="yeniden adlandır"):
        import_fixtures(conn, a, raw_dir=raw)
