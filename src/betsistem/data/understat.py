"""Understat maç xG verisini indirip match_xg tablosuna yükler.

Understat lig sayfası veriyi getLeagueData/<lig>/<sezon başlangıç yılı> uç noktasından JSON olarak çeker.
Yanıt 'dates' (maçlar, xG) ve 'teams' (takım bazında maç geçmişi, npxG dahil) içerir.
"""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import requests

from betsistem.config import RAW_DIR
from betsistem.data.db import UnknownTeamError, resolve_team
from betsistem.data.raw import RawDataError, store_raw

SOURCE = "understat"
URL = "https://understat.com/getLeagueData/{league}/{year}"
# football-data kodu -> Understat kodu
LEAGUE_CODES = {"E0": "EPL", "SP1": "La_liga", "D1": "Bundesliga", "I1": "Serie_A", "F1": "Ligue_1"}
# Bu kadar günden fazla tarih farkı olan eşleşmeler raporlanır (Understat saati UTC).
MAX_DATE_DIFF_DAYS = 1


@dataclass
class XgLoadResult:
    matched: int = 0
    not_played: int = 0
    # Devam eden sezonda football-data dosyası Understat'tan geride kalabilir.
    missing_in_football_data: list[str] = field(default_factory=list)
    date_mismatches: list[str] = field(default_factory=list)


def understat_year(season: str) -> str:
    """football-data sezon kodu '2223' -> Understat yılı '2022'."""
    start = int(season[:2])
    return str((1900 if start >= 90 else 2000) + start)


def _check_payload(content: bytes) -> dict:
    try:
        data = json.loads(content)
    except ValueError as exc:
        raise RawDataError(f"Understat yanıtı JSON değil: {content[:120]!r}") from exc
    if not isinstance(data, dict) or not {"dates", "teams"} <= data.keys():
        raise RawDataError("Understat yanıtında 'dates' ve 'teams' alanları yok")
    return data


def fetch_understat(
    conn: sqlite3.Connection, league: str, season: str, *, raw_dir: Path = RAW_DIR, timeout: float = 30
) -> int:
    code = LEAGUE_CODES[league]
    year = understat_year(season)
    url = URL.format(league=code, year=year)
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"https://understat.com/league/{code}/{year}",
            },
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RawDataError(f"{url} indirilemedi: {exc}") from exc
    _check_payload(resp.content)
    return store_raw(
        conn, resp.content, source=SOURCE, league=league, season=season, origin=url, suffix=".json", raw_dir=raw_dir
    )


def load_understat(conn: sqlite3.Connection, data_version_id: int, *, raw_dir: Path = RAW_DIR) -> XgLoadResult:
    version = conn.execute("SELECT * FROM data_versions WHERE id = ?", (data_version_id,)).fetchone()
    if version is None or version["source"] != SOURCE:
        raise ValueError(f"id={data_version_id} bir Understat veri sürümü değil")
    data = _check_payload((raw_dir / version["file_path"]).read_bytes())

    # Ev sahibinin maç geçmişindeki satır: npxG = ev npxG, npxGA = deplasman npxG.
    home_history = {
        (team["title"], h["date"]): h
        for team in data["teams"].values()
        for h in team["history"]
        if h["h_a"] == "h"
    }

    result = XgLoadResult()
    unknown: set[str] = set()
    rows = []
    for m in data["dates"]:
        if not m["isResult"]:
            result.not_played += 1
            continue
        try:
            home_id = resolve_team(conn, SOURCE, m["h"]["title"])
            away_id = resolve_team(conn, SOURCE, m["a"]["title"])
        except UnknownTeamError as exc:
            unknown.add(str(exc))
            continue
        rows.append((m, home_id, away_id))
    if unknown:
        conn.rollback()
        raise UnknownTeamError("; ".join(sorted(unknown)))

    with conn:
        for m, home_id, away_id in rows:
            match = conn.execute(
                "SELECT id, match_date FROM matches"
                " WHERE league = ? AND season = ? AND home_team_id = ? AND away_team_id = ?"
                " ORDER BY ABS(julianday(match_date) - julianday(?)) LIMIT 1",  # tekrar eden eşleşme (#90)
                (version["league"], version["season"], home_id, away_id, m["datetime"][:10]),
            ).fetchone()
            if match is None:
                result.missing_in_football_data.append(f"{m['h']['title']} - {m['a']['title']} ({m['datetime']})")
                continue
            us_date = date.fromisoformat(m["datetime"][:10])
            if abs((us_date - date.fromisoformat(match["match_date"])).days) > MAX_DATE_DIFF_DAYS:
                result.date_mismatches.append(
                    f"{m['h']['title']} - {m['a']['title']}: football-data {match['match_date']}, understat {us_date}"
                )
            hist = home_history.get((m["h"]["title"], m["datetime"]))
            conn.execute(
                "INSERT INTO match_xg (match_id, source, external_id, home_xg, away_xg, home_npxg, away_npxg,"
                " data_version_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT (match_id, source) DO UPDATE SET external_id = excluded.external_id,"
                " home_xg = excluded.home_xg, away_xg = excluded.away_xg, home_npxg = excluded.home_npxg,"
                " away_npxg = excluded.away_npxg, data_version_id = excluded.data_version_id",
                (
                    match["id"],
                    SOURCE,
                    m["id"],
                    float(m["xG"]["h"]),
                    float(m["xG"]["a"]),
                    hist["npxG"] if hist else None,
                    hist["npxGA"] if hist else None,
                    data_version_id,
                ),
            )
            result.matched += 1
    return result
