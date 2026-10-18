"""Ham veri edinme. Ham dosyalar değiştirilmeden saklanır; her dosya bir veri sürümüdür."""

import hashlib
import zipfile
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import requests

from betsistem.config import RAW_DIR

FOOTBALL_DATA_SOURCE = "football-data"
FOOTBALL_DATA_URL = "https://www.football-data.co.uk/mmz4281/{season}/{league}.csv"


class RawDataError(Exception):
    pass


def _check_football_data_csv(content: bytes) -> None:
    """Engel sayfası veya HTML hata sayfası gibi yanlış içeriğin saklanmasını önler."""
    header = content[:2000].decode("utf-8-sig", errors="replace").splitlines()[0] if content else ""
    columns = {c.strip() for c in header.split(",")}
    if not {"Div", "Date", "HomeTeam", "AwayTeam"} <= columns:
        raise RawDataError(
            "İçerik football-data CSV'sine benzemiyor (başlık satırı beklenen sütunları içermiyor). "
            f"İlk satır: {header[:120]!r}"
        )


def store_raw(
    conn: sqlite3.Connection,
    content: bytes,
    *,
    source: str,
    league: str,
    season: str,
    origin: str,
    suffix: str = ".csv",
    raw_dir: Path = RAW_DIR,
) -> int:
    """Ham içeriği saklar ve data_versions kaydının id'sini döndürür. Aynı içerik ikinci kez saklanmaz."""
    sha = hashlib.sha256(content).hexdigest()
    row = conn.execute(
        "SELECT id FROM data_versions WHERE source = ? AND league = ? AND season = ? AND sha256 = ?",
        (source, league, season, sha),
    ).fetchone()
    if row:
        return row["id"]

    rel_path = Path(source) / league / f"{season}_{sha[:12]}{suffix}"
    dest = raw_dir / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)

    cur = conn.execute(
        "INSERT INTO data_versions (source, league, season, origin, file_path, sha256, acquired_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            source,
            league,
            season,
            origin,
            rel_path.as_posix(),
            sha,
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ),
    )
    conn.commit()
    return cur.lastrowid


def download_football_data(
    conn: sqlite3.Connection, league: str, season: str, *, raw_dir: Path = RAW_DIR, timeout: float = 30
) -> int:
    url = FOOTBALL_DATA_URL.format(league=league, season=season)
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RawDataError(
            f"{url} indirilemedi: {exc}. Dosyayı elle indirip 'betsistem import-raw' ile ekleyebilirsin."
        ) from exc
    _check_football_data_csv(resp.content)
    return store_raw(
        conn, resp.content, source=FOOTBALL_DATA_SOURCE, league=league, season=season, origin=url, raw_dir=raw_dir
    )


def import_football_data(
    conn: sqlite3.Connection, league: str, season: str, file: Path, *, raw_dir: Path = RAW_DIR
) -> int:
    content = Path(file).read_bytes()
    _check_football_data_csv(content)
    return store_raw(
        conn,
        content,
        source=FOOTBALL_DATA_SOURCE,
        league=league,
        season=season,
        origin=f"manual:{Path(file).name}",
        raw_dir=raw_dir,
    )


def import_football_data_zip(
    conn: sqlite3.Connection, zip_path: Path, season: str, *, raw_dir: Path = RAW_DIR
) -> list[tuple[str, int]]:
    """football-data sezon paketi (data.zip): her lig CSV'si ayrı veri sürümü olarak saklanır.

    Lig kodu dosya adından alınır (SP1.csv -> SP1); yükleyici dosyadaki Div sütununu ayrıca doğrular.
    """
    out = []
    with zipfile.ZipFile(zip_path) as z:
        for name in sorted(z.namelist()):
            if not name.lower().endswith(".csv"):
                continue
            content = z.read(name)
            _check_football_data_csv(content)
            league = Path(name).stem
            version_id = store_raw(
                conn, content, source=FOOTBALL_DATA_SOURCE, league=league, season=season,
                origin=f"manual:{Path(zip_path).name}/{name}", raw_dir=raw_dir,
            )
            out.append((league, version_id))
    return out
