from pathlib import Path

import pytest

from betsistem.config import season_label
from betsistem.data.db import connect, init_db
from betsistem.data.football_data import load_football_data, parse_date, parse_odds_columns
from betsistem.data.raw import RawDataError, import_football_data

FIXTURE = Path(__file__).parent / "fixtures" / "E0_sample.csv"


@pytest.fixture
def conn():
    c = connect(":memory:")
    init_db(c)
    yield c
    c.close()


def test_season_label():
    assert season_label("2223") == "2022/23"
    assert season_label("9900") == "1999/00"


def test_parse_date_handles_both_year_formats():
    assert parse_date("05/08/2022") == "2022-08-05"
    assert parse_date("05/08/22") == "2022-08-05"


def test_parse_odds_columns_1x2_and_ou25_only():
    cols = ["PSH", "PSCH", "MaxCA", "AvgD", "B365>2.5", "PC<2.5", "B365AHH", "PAHH", "AHh", "HC", "BbMxH", "BbAH",
            "FTHG", "AHCh"]
    parsed = {c.column: (c.bookmaker, c.market, c.timing, c.outcome) for c in parse_odds_columns(cols)}
    assert parsed == {
        "PSH": ("PS", "1X2", "early", "H"),
        "PSCH": ("PS", "1X2", "closing", "H"),
        "MaxCA": ("Max", "1X2", "closing", "A"),
        "AvgD": ("Avg", "1X2", "early", "D"),
        "BbMxH": ("BbMx", "1X2", "early", "H"),
        "B365>2.5": ("B365", "OU25", "early", "O"),
        "PC<2.5": ("PS", "OU25", "closing", "U"),  # Pinnacle alt/üstte 'P' yazılır
    }


def test_import_and_load(conn, tmp_path):
    vid = import_football_data(conn, "E0", "2223", FIXTURE, raw_dir=tmp_path)
    result = load_football_data(conn, vid, raw_dir=tmp_path)

    assert result.matches == 3
    # 1-X-2: 3 maç x 8 şirket/zaman x 3 sonuç = 72, biri boş (Fulham-Liverpool PSCH)
    # alt/üst: 3 maç x B365 erken/kapanış x 2 sonuç = 12
    assert result.odds == 83
    assert conn.execute("SELECT COUNT(*) FROM odds WHERE market = 'OU25'").fetchone()[0] == 12

    m = conn.execute(
        "SELECT m.*, h.name AS home, a.name AS away FROM matches m"
        " JOIN teams h ON h.id = m.home_team_id JOIN teams a ON a.id = m.away_team_id"
        " WHERE h.name = 'Crystal Palace'"
    ).fetchone()
    assert (m["away"], m["match_date"], m["kickoff_time"], m["ftr"]) == ("Arsenal", "2022-08-05", "20:00", "A")

    pin_close = conn.execute(
        "SELECT outcome, price FROM odds WHERE match_id = ? AND bookmaker = 'PS' AND timing = 'closing'",
        (m["id"],),
    ).fetchall()
    assert {r["outcome"]: r["price"] for r in pin_close} == {"H": 4.64, "D": 3.62, "A": 1.85}


def test_reload_is_idempotent(conn, tmp_path):
    vid = import_football_data(conn, "E0", "2223", FIXTURE, raw_dir=tmp_path)
    load_football_data(conn, vid, raw_dir=tmp_path)
    ids_before = [r["id"] for r in conn.execute("SELECT id FROM matches ORDER BY id")]

    assert import_football_data(conn, "E0", "2223", FIXTURE, raw_dir=tmp_path) == vid
    load_football_data(conn, vid, raw_dir=tmp_path)

    assert [r["id"] for r in conn.execute("SELECT id FROM matches ORDER BY id")] == ids_before
    assert conn.execute("SELECT COUNT(*) FROM odds").fetchone()[0] == 83
    assert conn.execute("SELECT COUNT(*) FROM teams").fetchone()[0] == 6


def test_rejects_non_csv_content(conn, tmp_path):
    block_page = tmp_path / "blocked.html"
    block_page.write_text("<html><body>Erişim engellendi</body></html>", encoding="utf-8")
    with pytest.raises(RawDataError):
        import_football_data(conn, "E0", "2223", block_page, raw_dir=tmp_path)


def test_parse_odds_columns_newer_bookmaker_codes():
    cols = ["BFD", "BFCD", "BFDD", "BFDCH", "BMGMA", "CLCH", "SKBCD", "PPH", "BVCA"]
    parsed = {c.column: (c.bookmaker, c.timing, c.outcome) for c in parse_odds_columns(cols)}
    assert parsed == {
        "BFD": ("BF", "early", "D"),
        "BFCD": ("BF", "closing", "D"),
        "BFDD": ("BFD", "early", "D"),
        "BFDCH": ("BFD", "closing", "H"),
        "BMGMA": ("BMGM", "early", "A"),
        "CLCH": ("CL", "closing", "H"),
        "SKBCD": ("SKB", "closing", "D"),
        "PPH": ("PP", "early", "H"),
        "BVCA": ("BV", "closing", "A"),
    }


def test_non_numeric_price_is_skipped(conn, tmp_path):
    text = FIXTURE.read_text(encoding="utf-8").replace(",4.64,3.62,1.85,", ",#,3.62,1.85,", 1)
    bad = tmp_path / "bad.csv"
    bad.write_text(text, encoding="utf-8")
    vid = import_football_data(conn, "E0", "2223", bad, raw_dir=tmp_path)
    res = load_football_data(conn, vid, raw_dir=tmp_path)
    assert (res.odds, res.skipped_invalid_prices) == (82, 1)


def test_old_odds_table_is_migrated(tmp_path):
    import sqlite3 as sq
    path = tmp_path / "old.sqlite"
    raw = sq.connect(path)
    raw.executescript("""
        CREATE TABLE odds (id INTEGER PRIMARY KEY, match_id INTEGER NOT NULL, source TEXT NOT NULL,
            bookmaker TEXT NOT NULL, market TEXT NOT NULL,
            outcome TEXT NOT NULL CHECK (outcome IN ('H', 'D', 'A')),
            timing TEXT NOT NULL CHECK (timing IN ('early', 'closing')),
            price REAL NOT NULL CHECK (price > 1.0), recorded_at TEXT, data_version_id INTEGER NOT NULL,
            UNIQUE (match_id, source, bookmaker, market, outcome, timing));
        CREATE INDEX idx_odds_match ON odds (match_id);
        INSERT INTO odds VALUES (1, 1, 'football-data', 'PS', '1X2', 'H', 'early', 2.0, NULL, 1);
    """)
    raw.commit(); raw.close()
    c = connect(path)
    init_db(c)
    assert c.execute("SELECT COUNT(*) FROM odds").fetchone()[0] == 1
    c.execute("PRAGMA foreign_keys = OFF")
    c.execute("INSERT INTO odds (match_id, source, bookmaker, market, outcome, timing, price, data_version_id)"
              " VALUES (1, 'football-data', 'PS', 'OU25', 'O', 'early', 1.9, 1)")
    assert c.execute("SELECT name FROM sqlite_master WHERE name = 'idx_odds_match'").fetchone()
    c.close()
