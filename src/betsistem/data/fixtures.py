"""football-data haftalık fikstür dosyası (fixtures.csv) sürümleme (karar #80).

Her indirme `fixture_downloads` tablosuna dosya adı ve indirme zamanıyla eklenir; içerik `data_versions`'ta
sha256 ile tek sürüm olarak saklanır. Ardışık indirmelerin sha'ları karşılaştırılarak dosyanın Cuma günü
ne zaman güncellendiği bulunur (Faz 8.4).
"""

import hashlib
import io
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from betsistem.config import RAW_DIR, season_of
from betsistem.data.raw import RawDataError, store_raw

SOURCE = "football-data-fixtures"
TR = timezone(timedelta(hours=3))  # Türkiye saati; 2016'dan beri yaz saati uygulaması yok


@dataclass
class FixtureImport:
    data_version_id: int
    file_name: str
    downloaded_at: str
    sha12: str
    new_content: bool  # bu içerik daha önce hiç görülmemiş mi
    previous: tuple[str, str, str] | None  # (dosya, indirme zamanı, sha12) — bir önceki indirme
    matches_by_league: dict[str, int]


def read_fixtures_bytes(content: bytes) -> pd.DataFrame:
    try:
        df = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(io.BytesIO(content), encoding="latin-1")
    df.columns = [str(c).strip() for c in df.columns]
    missing = {"Div", "Date", "HomeTeam", "AwayTeam"} - set(df.columns)
    if missing:
        raise RawDataError(f"Fikstür dosyası beklenen sütunları içermiyor: {sorted(missing)}")
    df = df.dropna(subset=["HomeTeam", "AwayTeam"]).copy()
    for col in ("Div", "HomeTeam", "AwayTeam"):
        df[col] = df[col].astype(str).str.strip()
    return df


def import_fixtures(
    conn: sqlite3.Connection, file: Path, *, downloaded_at: datetime | None = None, raw_dir: Path = RAW_DIR
) -> FixtureImport:
    """downloaded_at verilmezse dosyanın değiştirilme zamanı (indirme anı) Türkiye saatiyle kullanılır."""
    file = Path(file)
    content = file.read_bytes()
    df = read_fixtures_bytes(content)
    when = (downloaded_at or datetime.fromtimestamp(file.stat().st_mtime, TR)).astimezone(TR)
    when_iso = when.isoformat(timespec="seconds")

    known = conn.execute(
        "SELECT d.data_version_id, d.downloaded_at FROM fixture_downloads d WHERE d.file_name = ?", (file.name,)
    ).fetchone()

    existed = conn.execute(
        "SELECT id FROM data_versions WHERE source = ? AND sha256 = ?", (SOURCE, hashlib.sha256(content).hexdigest())
    ).fetchone()
    version_id = store_raw(conn, content, source=SOURCE, league="ALL", season=season_of(when.date()),
                           origin=f"manual:{file.name}", raw_dir=raw_dir)
    if known:
        if known["data_version_id"] != version_id:
            raise RawDataError(f"{file.name} adıyla farklı içerikte bir dosya daha önce yüklenmiş; dosyayı yeniden adlandır")
        when_iso = known["downloaded_at"]
    else:
        with conn:
            conn.execute(
                "INSERT INTO fixture_downloads (data_version_id, file_name, downloaded_at, imported_at)"
                " VALUES (?, ?, ?, ?)",
                (version_id, file.name, when_iso, datetime.now(TR).isoformat(timespec="seconds")),
            )

    prev = conn.execute(
        "SELECT f.file_name, f.downloaded_at, substr(v.sha256, 1, 12) AS sha12 FROM fixture_downloads f"
        " JOIN data_versions v ON v.id = f.data_version_id WHERE f.downloaded_at < ?"
        " ORDER BY f.downloaded_at DESC LIMIT 1",
        (when_iso,),
    ).fetchone()
    sha12 = conn.execute("SELECT substr(sha256, 1, 12) FROM data_versions WHERE id = ?", (version_id,)).fetchone()[0]
    return FixtureImport(
        data_version_id=version_id, file_name=file.name, downloaded_at=when_iso, sha12=sha12,
        new_content=existed is None, previous=tuple(prev) if prev else None,
        matches_by_league=df.Div.value_counts().to_dict(),
    )


def fixtures_log(conn: sqlite3.Connection) -> pd.DataFrame:
    """Tüm indirmeler; 'değişti' = içerik bir önceki indirmeden farklı. Cuma güncelleme saati buradan okunur."""
    df = pd.read_sql(
        "SELECT f.downloaded_at, f.file_name, f.data_version_id, substr(v.sha256, 1, 12) AS sha12"
        " FROM fixture_downloads f JOIN data_versions v ON v.id = f.data_version_id ORDER BY f.downloaded_at",
        conn,
    )
    df["değişti"] = df.sha12.ne(df.sha12.shift())
    return df


def fixture_matches(conn: sqlite3.Connection, data_version_id: int, raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    row = conn.execute("SELECT source, file_path FROM data_versions WHERE id = ?", (data_version_id,)).fetchone()
    if row is None or row["source"] != SOURCE:
        raise RawDataError(f"id={data_version_id} bir fikstür sürümü değil")
    return read_fixtures_bytes((raw_dir / row["file_path"]).read_bytes())
