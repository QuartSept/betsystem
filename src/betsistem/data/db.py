"""SQLite bağlantısı ve şema kurulumu."""

import csv
import sqlite3
from functools import cache
from importlib import resources
from pathlib import Path

from betsistem.config import DB_PATH


def connect(path: Path | str = DB_PATH) -> sqlite3.Connection:
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate_final_set_runs(conn: sqlite3.Connection) -> None:
    """Eski tek satırlık final_set_runs (id = 1) tablosunu lig bazlı tabloya çevirir; yalnızca boşsa."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(final_set_runs)")]
    if cols and "league" not in cols:
        if conn.execute("SELECT COUNT(*) FROM final_set_runs").fetchone()[0]:
            raise RuntimeError("final_set_runs dolu ve eski biçimde; elle incelenmeli")
        conn.execute("DROP TABLE final_set_runs")


def init_db(conn: sqlite3.Connection) -> None:
    _migrate_final_set_runs(conn)
    schema = resources.files("betsistem.data").joinpath("schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.commit()


def get_or_create_team(conn: sqlite3.Connection, source: str, alias: str) -> int:
    """Kaynaktaki takım adını kanonik takıma çevirir; yoksa adı kanonik kabul edip oluşturur.

    football-data adları başlangıç kanonik adlarıdır. Diğer kaynaklar (Understat vb.)
    eşleştirme tablosu üzerinden bu takımlara bağlanır.
    """
    row = conn.execute(
        "SELECT team_id FROM team_aliases WHERE source = ? AND alias = ?", (source, alias)
    ).fetchone()
    if row:
        return row["team_id"]
    conn.execute("INSERT OR IGNORE INTO teams (name) VALUES (?)", (alias,))
    team_id = conn.execute("SELECT id FROM teams WHERE name = ?", (alias,)).fetchone()["id"]
    conn.execute(
        "INSERT INTO team_aliases (source, alias, team_id) VALUES (?, ?, ?)", (source, alias, team_id)
    )
    return team_id


class UnknownTeamError(Exception):
    pass


@cache
def _static_aliases() -> dict[tuple[str, str], str]:
    text = resources.files("betsistem.data").joinpath("team_aliases.csv").read_text(encoding="utf-8")
    return {(r["source"], r["alias"]): r["canonical"] for r in csv.DictReader(text.splitlines())}


def resolve_team(conn: sqlite3.Connection, source: str, alias: str) -> int:
    """Kaynaktaki adı mevcut kanonik takıma bağlar. Yeni takım oluşturmaz.

    Sıra: daha önce kaydedilmiş eşleşme, team_aliases.csv, birebir aynı kanonik ad.
    Hiçbiri tutmazsa UnknownTeamError; eşleşme team_aliases.csv'ye elle eklenir.
    """
    row = conn.execute(
        "SELECT team_id FROM team_aliases WHERE source = ? AND alias = ?", (source, alias)
    ).fetchone()
    if row:
        return row["team_id"]
    canonical = _static_aliases().get((source, alias), alias)
    team = conn.execute("SELECT id FROM teams WHERE name = ?", (canonical,)).fetchone()
    if team is None:
        raise UnknownTeamError(f"{source} takımı eşleşmedi: {alias!r} (team_aliases.csv'ye ekle)")
    conn.execute(
        "INSERT INTO team_aliases (source, alias, team_id) VALUES (?, ?, ?)", (source, alias, team["id"])
    )
    return team["id"]
