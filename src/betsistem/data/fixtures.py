"""football-data haftalık fikstür dosyası (fixtures.csv) sürümleme (karar #80, #94).

Her indirme `fixture_downloads` tablosuna dosya adı, indirme zamanı ve sitedeki "Latest fixtures uploaded"
zamanıyla eklenir; içerik `data_versions`'ta sha256 ile tek sürüm olarak saklanır.

Dosya, yüklendiği günden önceki (veya aynı) en yakın Cuma ya da Salı'nın oranlarını taşır (football-data
oranları Cuma/Salı öğleden sonra toplar; dosya ertesi sabah yüklenir, ilk gözlem 17/10/26 09:35 İngiltere
saati). İndirme anına göre beklenen toplama gününden eski bir dosya, yani yeni yükleme yapılmadan indirilmiş
önceki haftanın dosyası reddedilir (#94).
"""

import hashlib
import io
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from betsistem.config import RAW_DIR, season_of
from betsistem.data.raw import RawDataError, store_raw

SOURCE = "football-data-fixtures"
TR = timezone(timedelta(hours=3))  # Türkiye saati; 2016'dan beri yaz saati uygulaması yok
UK = ZoneInfo("Europe/London")  # football-data'nın yayımladığı saat (yaz saatli)
TUESDAY, FRIDAY = 1, 4


def collection_day(d: date) -> date:
    """d gününe göre en yakın önceki (veya aynı) Cuma ya da Salı: oranların toplandığı gün."""
    back = min((d.weekday() - wd) % 7 for wd in (TUESDAY, FRIDAY))
    return d - timedelta(days=back)


def parse_uploaded(text: str) -> datetime:
    """Sitedeki biçim '17/10/26 09:35' (İngiltere saati) veya '2026-10-17 09:35'."""
    for fmt in ("%d/%m/%y %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text.strip(), fmt).replace(tzinfo=UK)
        except ValueError:
            continue
    raise RawDataError(f"Yükleme zamanı anlaşılamadı: {text!r} (sitedeki gibi: 17/10/26 09:35)")


@dataclass
class FixtureImport:
    data_version_id: int
    file_name: str
    downloaded_at: str
    uploaded_at: str
    collection_day: str
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
    conn: sqlite3.Connection,
    file: Path,
    *,
    uploaded_at: datetime,
    downloaded_at: datetime | None = None,
    raw_dir: Path = RAW_DIR,
) -> FixtureImport:
    """uploaded_at: sitedeki "Latest fixtures uploaded" zamanı (İngiltere saati, zorunlu).
    downloaded_at verilmezse dosyanın değiştirilme zamanı (indirme anı) kullanılır."""
    file = Path(file)
    content = file.read_bytes()
    df = read_fixtures_bytes(content)
    when = (downloaded_at or datetime.fromtimestamp(file.stat().st_mtime, TR)).astimezone(TR)
    uploaded = uploaded_at.astimezone(UK)
    if uploaded > when:
        raise RawDataError(f"Yükleme zamanı ({uploaded:%d/%m/%y %H:%M} UK) indirme anından sonra olamaz")
    file_day = collection_day(uploaded.date())
    expected_day = collection_day(when.date())
    if file_day < expected_day:
        raise RawDataError(
            f"Önceki haftanın dosyası: site {uploaded:%d/%m/%y %H:%M} (UK) yüklemesini gösteriyor, bu dosya "
            f"{file_day} oranlarını taşıyor; indirme anına göre beklenen toplama günü {expected_day}. "
            "Yeni yükleme yapılınca tekrar indir (#94)."
        )
    when_iso = when.isoformat(timespec="seconds")
    uploaded_iso = uploaded.isoformat(timespec="minutes")

    known = conn.execute(
        "SELECT data_version_id, downloaded_at FROM fixture_downloads WHERE file_name = ?", (file.name,)
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
                "INSERT INTO fixture_downloads (data_version_id, file_name, downloaded_at, uploaded_at,"
                " collection_day, imported_at) VALUES (?, ?, ?, ?, ?, ?)",
                (version_id, file.name, when_iso, uploaded_iso, file_day.isoformat(),
                 datetime.now(TR).isoformat(timespec="seconds")),
            )

    prev = conn.execute(
        "SELECT f.file_name, f.downloaded_at, substr(v.sha256, 1, 12) AS sha12 FROM fixture_downloads f"
        " JOIN data_versions v ON v.id = f.data_version_id WHERE f.downloaded_at < ?"
        " ORDER BY f.downloaded_at DESC LIMIT 1",
        (when_iso,),
    ).fetchone()
    sha12 = conn.execute("SELECT substr(sha256, 1, 12) FROM data_versions WHERE id = ?", (version_id,)).fetchone()[0]
    return FixtureImport(
        data_version_id=version_id, file_name=file.name, downloaded_at=when_iso, uploaded_at=uploaded_iso,
        collection_day=file_day.isoformat(), sha12=sha12, new_content=existed is None,
        previous=tuple(prev) if prev else None, matches_by_league=df.Div.value_counts().to_dict(),
    )


def fixtures_log(conn: sqlite3.Connection) -> pd.DataFrame:
    """Tüm indirmeler; yükleme günü/saati (UK) ve içerik değişimi. Yükleme düzeni buradan izlenir (#97)."""
    df = pd.read_sql(
        "SELECT f.downloaded_at, f.uploaded_at, f.collection_day, f.file_name, f.data_version_id,"
        " substr(v.sha256, 1, 12) AS sha12"
        " FROM fixture_downloads f JOIN data_versions v ON v.id = f.data_version_id ORDER BY f.downloaded_at",
        conn,
    )
    up = pd.to_datetime(df.uploaded_at.str[:16])
    df["yükleme (UK)"] = up.dt.strftime("%a %H:%M")
    df["değişti"] = df.sha12.ne(df.sha12.shift())
    return df


def fixture_download(conn: sqlite3.Connection, file_name: str):
    """(data_version_id, toplama günü, yükleme zamanı) — İddaa içe aktarması için."""
    row = conn.execute(
        "SELECT data_version_id, collection_day, uploaded_at FROM fixture_downloads WHERE file_name = ?", (file_name,)
    ).fetchone()
    if row is None:
        return None
    return row["data_version_id"], date.fromisoformat(row["collection_day"]), datetime.fromisoformat(row["uploaded_at"])


def fixture_matches(conn: sqlite3.Connection, data_version_id: int, raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    row = conn.execute("SELECT source, file_path FROM data_versions WHERE id = ?", (data_version_id,)).fetchone()
    if row is None or row["source"] != SOURCE:
        raise RawDataError(f"id={data_version_id} bir fikstür sürümü değil")
    return read_fixtures_bytes((raw_dir / row["file_path"]).read_bytes())
