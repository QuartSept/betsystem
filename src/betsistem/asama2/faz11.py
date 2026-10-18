"""Faz 11 penceresi (2025/26–2026/27) kilidi ve 8.5 doluluk ölçümü (karar #81).

Pencere, Faz 10'u geçen her fikir için yalnızca bir kez açılır. Açılış veritabanına kaydedilir; ikinci
açılışı kod reddeder (final_set_runs ile aynı mekanizma). Açılmadan önce pencerede yalnızca oran doluluğu
ölçülebilir: CLV, maç sonucu veya kural çıktısı hesaplanmaz.
"""

import sqlite3
import subprocess
from datetime import datetime, timezone

import pandas as pd

from betsistem.config import FAZ11_WINDOW_SEASONS, PROJECT_ROOT
from betsistem.model.timeline import Faz11Token

CONFIRM_PHRASE = "FAZ 11 PENCERESİNİ AÇ"
COVERAGE_BOOKMAKERS = ("BFE", "Avg", "B365", "PS")


class Faz11AlreadyOpened(Exception):
    pass


def _git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def open_faz11_window(conn: sqlite3.Connection, idea: str, config: str, confirm: str) -> Faz11Token:
    if confirm != CONFIRM_PHRASE:
        raise PermissionError(f"Faz 11 penceresini açmak için onay ifadesi gerekir: {CONFIRM_PHRASE!r}")
    if conn.execute("SELECT 1 FROM faz11_runs WHERE idea = ?", (idea,)).fetchone():
        raise Faz11AlreadyOpened(f"{idea} için Faz 11 penceresi daha önce açıldı; ikinci çalıştırma yapılamaz.")
    with conn:
        conn.execute(
            "INSERT INTO faz11_runs (idea, opened_at, config, git_commit) VALUES (?, ?, ?, ?)",
            (idea, datetime.now(timezone.utc).isoformat(timespec="seconds"), config, _git_commit()),
        )
    return Faz11Token(idea)


def window_coverage(conn: sqlite3.Connection, leagues=None) -> pd.DataFrame:
    """8.5: pencerede lig, sezon, şirket ve zaman başına 1-X-2 oran doluluğu. Yalnızca sayım; sonuç veya
    oran değeri okunmaz."""
    placeholders = ",".join("?" for _ in FAZ11_WINDOW_SEASONS)
    params: list = list(FAZ11_WINDOW_SEASONS)
    league_filter = ""
    if leagues:
        league_filter = f" AND m.league IN ({','.join('?' for _ in leagues)})"
        params += list(leagues)
    totals = pd.read_sql(
        f"SELECT m.league, m.season, COUNT(*) AS matches FROM matches m WHERE m.season IN ({placeholders})"
        f"{league_filter} GROUP BY m.league, m.season", conn, params=params,
    )
    bk = ",".join("?" for _ in COVERAGE_BOOKMAKERS)
    complete = pd.read_sql(
        f"""
        SELECT m.league, m.season, o.bookmaker, o.timing, COUNT(*) AS n FROM (
            SELECT match_id, bookmaker, timing FROM odds
            WHERE market = '1X2' AND bookmaker IN ({bk})
            GROUP BY match_id, bookmaker, timing HAVING COUNT(DISTINCT outcome) = 3) o
        JOIN matches m ON m.id = o.match_id
        WHERE m.season IN ({placeholders}){league_filter}
        GROUP BY m.league, m.season, o.bookmaker, o.timing
        """,
        conn, params=[*COVERAGE_BOOKMAKERS, *params],
    )
    df = complete.merge(totals, on=["league", "season"])
    df["doluluk"] = (df.n / df.matches).round(3)
    wide = df.pivot_table(index=["league", "season", "matches"], columns=["bookmaker", "timing"], values="doluluk")
    wide.columns = [f"{b} {t}" for b, t in wide.columns]
    return wide.reset_index().fillna(0.0)
