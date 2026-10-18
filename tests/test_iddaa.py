import sqlite3

import pytest

from betsistem.data.db import connect, init_db
from betsistem.data.iddaa import COLUMNS, import_iddaa
from betsistem.data.raw import RawDataError

HEADER = ",".join(COLUMNS)
ROW = "2026-10-16T15:30+03:00,2026-10-18,17:00,Arsenal,Chelsea,1.85,3.60,4.10,"


@pytest.fixture
def conn():
    c = connect(":memory:")
    init_db(c)
    yield c
    c.close()


def _write(tmp_path, *rows, name="iddaa.csv"):
    p = tmp_path / name
    p.write_text("\n".join([HEADER, *rows]) + "\n", encoding="utf-8")
    return p


def test_import_and_cumulative_reimport(conn, tmp_path):
    raw = tmp_path / "raw"
    res = import_iddaa(conn, _write(tmp_path, ROW), raw_dir=raw)
    assert (res.added, res.already_present) == (1, 0)

    second = "2026-10-17T12:00+03:00,2026-10-18,17:00,Arsenal,Chelsea,1.80,3.70,4.20,"
    res = import_iddaa(conn, _write(tmp_path, ROW, second), raw_dir=raw)
    assert (res.added, res.already_present) == (1, 1)
    row = conn.execute("SELECT * FROM iddaa_odds_log ORDER BY recorded_at").fetchone()
    assert (row["recorded_at"], row["price_draw"]) == ("2026-10-16T15:30+03:00", 3.6)
    assert conn.execute("SELECT season FROM data_versions WHERE source = 'iddaa' LIMIT 1").fetchone()[0] == "2627"


def test_changed_prices_rejected(conn, tmp_path):
    raw = tmp_path / "raw"
    import_iddaa(conn, _write(tmp_path, ROW), raw_dir=raw)
    with pytest.raises(RawDataError, match="değiştirilemez"):
        import_iddaa(conn, _write(tmp_path, ROW.replace("1.85", "1.90")), raw_dir=raw)


def test_log_is_append_only(conn, tmp_path):
    import_iddaa(conn, _write(tmp_path, ROW), raw_dir=tmp_path / "raw")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE iddaa_odds_log SET price_home = 2.0")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM iddaa_odds_log")


@pytest.mark.parametrize("bad, msg", [
    (ROW.replace("+03:00", ""), "saat dilimi"),
    (ROW.replace("2026-10-16", "2026-10-19"), "sonra olamaz"),
    (ROW.replace("4.10", "1.00"), "büyük olmalı"),
])
def test_validation(conn, tmp_path, bad, msg):
    with pytest.raises(RawDataError, match=msg):
        import_iddaa(conn, _write(tmp_path, bad), raw_dir=tmp_path / "raw")
