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


def _prepare_odds_migration(conn: sqlite3.Connection) -> bool:
    """Eski odds tablosu alt/üst sonuçlarına (O/U) izin vermiyorsa kenara alır; satırlar sonra taşınır."""
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'odds'").fetchone()
    if row is None or "'O'" in row[0]:
        return False
    conn.executescript("DROP INDEX IF EXISTS idx_odds_match; ALTER TABLE odds RENAME TO odds_old;")
    return True


def _migrate_iddaa_log(conn: sqlite3.Connection) -> None:
    """Eski iddaa_odds_log (lig/MBS/fikstür sürümü olmayan) boşsa kaldırılır; doluysa elle incelenmeli."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(iddaa_odds_log)")]
    if cols and ("fixtures_version_id" not in cols or "has_reference" not in cols):
        if conn.execute("SELECT COUNT(*) FROM iddaa_odds_log").fetchone()[0]:
            raise RuntimeError("iddaa_odds_log dolu ve eski biçimde; elle incelenmeli")
        conn.execute("DROP TABLE iddaa_odds_log")


def _migrate_matches_leg(conn: sqlite3.Connection, schema: str) -> None:
    """matches tablosuna leg sütunu ve (lig, sezon, ev, deplasman, leg) anahtarı ekler (karar #90).

    Güvenli SQLite yöntemi: yeni tablo oluştur, kopyala, eskiyi sil, yeniyi yeniden adlandır. id'ler korunur;
    eski satırların hepsi leg = 1 olur (eski anahtar tekrar eden eşleşmeyi zaten tek satıra indiriyordu).
    """
    cols = [r[1] for r in conn.execute("PRAGMA table_info(matches)")]
    if not cols or "leg" in cols:
        return
    start = schema.index("CREATE TABLE IF NOT EXISTS matches (")
    end = schema.index("\n);", start) + 3  # yorumlardaki ');' ile karışmasın
    create_new = schema[start:end].replace("CREATE TABLE IF NOT EXISTS matches (", "CREATE TABLE matches_new (")
    col_list = ", ".join(cols)
    conn.executescript(
        "PRAGMA foreign_keys = OFF;"
        "DROP INDEX IF EXISTS idx_matches_season;"
        f"{create_new};"
        f"INSERT INTO matches_new ({col_list}, leg) SELECT {col_list}, 1 FROM matches;"
        "DROP TABLE matches;"
        "ALTER TABLE matches_new RENAME TO matches;"
        "PRAGMA foreign_keys = ON;"
    )


def _migrate_fixture_downloads(conn: sqlite3.Connection) -> None:
    """Yükleme zamanı sütunları olmayan eski fixture_downloads boşsa kaldırılır (#94)."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(fixture_downloads)")]
    if cols and "uploaded_at" not in cols:
        if conn.execute("SELECT COUNT(*) FROM fixture_downloads").fetchone()[0]:
            raise RuntimeError("fixture_downloads dolu ve eski biçimde; elle incelenmeli")
        conn.execute("DROP TABLE fixture_downloads")


def init_db(conn: sqlite3.Connection) -> None:
    _migrate_final_set_runs(conn)
    _migrate_fixture_downloads(conn)
    _migrate_iddaa_log(conn)
    migrate_odds = _prepare_odds_migration(conn)
    schema = resources.files("betsistem.data").joinpath("schema.sql").read_text(encoding="utf-8")
    _migrate_matches_leg(conn, schema)
    conn.executescript(schema)
    if migrate_odds:
        # Satırlar olduğu gibi taşınır; yabancı anahtarlar kopyalama sırasında yeniden denetlenmez.
        conn.executescript(
            "PRAGMA foreign_keys = OFF; INSERT INTO odds SELECT * FROM odds_old; DROP TABLE odds_old;"
            " PRAGMA foreign_keys = ON;"
        )
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
