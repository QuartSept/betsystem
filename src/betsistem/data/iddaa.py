"""Elle tutulan İddaa oran kayıtlarını (templates/iddaa_oranlari.csv biçimi) iddaa_odds_log'a ekler.

Dosya birikimli tutulabilir: daha önce eklenmiş satırlar atlanır. Aynı (recorded_at, ev, deplasman)
için farklı oranlar gelirse kayıt değiştirilmez, hata verilir.
"""

import csv
import io
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from betsistem.config import RAW_DIR, season_of
from betsistem.data.raw import RawDataError, store_raw

SOURCE = "iddaa"
COLUMNS = (
    "recorded_at", "match_date", "kickoff_time", "home_team", "away_team",
    "price_home", "price_draw", "price_away", "note",
)
PRICE_COLUMNS = ("price_home", "price_draw", "price_away")


@dataclass
class IddaaImportResult:
    added: int = 0
    already_present: int = 0


def _parse_row(lineno: int, row: dict) -> dict:
    def fail(msg):
        raise RawDataError(f"Satır {lineno}: {msg}")

    try:
        recorded = datetime.fromisoformat(row["recorded_at"].strip())
    except ValueError:
        fail(f"recorded_at ISO 8601 değil: {row['recorded_at']!r} (örn. 2026-10-16T15:30+03:00)")
    if recorded.tzinfo is None:
        fail("recorded_at saat dilimi içermeli (örn. +03:00)")
    try:
        match_date = date.fromisoformat(row["match_date"].strip())
    except ValueError:
        fail(f"match_date YYYY-MM-DD değil: {row['match_date']!r}")
    if recorded.date() > match_date:
        fail("recorded_at maç tarihinden sonra olamaz")

    out = {
        "recorded_at": recorded.isoformat(timespec="minutes"),
        "match_date": match_date.isoformat(),
        "kickoff_time": (row.get("kickoff_time") or "").strip() or None,
        "home_team": row["home_team"].strip(),
        "away_team": row["away_team"].strip(),
        "note": (row.get("note") or "").strip() or None,
    }
    if not out["home_team"] or not out["away_team"]:
        fail("takım adı boş")
    for col in PRICE_COLUMNS:
        try:
            price = float(row[col].strip().replace(",", "."))
        except ValueError:
            fail(f"{col} sayı değil: {row[col]!r}")
        if price <= 1.0:
            fail(f"{col} 1'den büyük olmalı: {price}")
        out[col] = price
    return out


def import_iddaa(
    conn: sqlite3.Connection, file: Path, *, league: str = "E0", raw_dir: Path = RAW_DIR
) -> IddaaImportResult:
    content = Path(file).read_bytes()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    if tuple(reader.fieldnames or ()) != COLUMNS:
        raise RawDataError(f"Başlık satırı şablonla aynı olmalı: {','.join(COLUMNS)}")
    rows = [_parse_row(i, r) for i, r in enumerate(reader, start=2)]
    if not rows:
        return IddaaImportResult()

    season = season_of(date.fromisoformat(rows[0]["match_date"]))
    version_id = store_raw(
        conn, content, source=SOURCE, league=league, season=season, origin=f"manual:{Path(file).name}",
        raw_dir=raw_dir,
    )

    result = IddaaImportResult()
    with conn:
        for r in rows:
            existing = conn.execute(
                "SELECT price_home, price_draw, price_away FROM iddaa_odds_log"
                " WHERE recorded_at = ? AND home_team = ? AND away_team = ?",
                (r["recorded_at"], r["home_team"], r["away_team"]),
            ).fetchone()
            if existing:
                if tuple(existing) != tuple(r[c] for c in PRICE_COLUMNS):
                    raise RawDataError(
                        f"{r['recorded_at']} {r['home_team']} - {r['away_team']} daha önce farklı oranlarla"
                        " kaydedilmiş; kayıtlar değiştirilemez. Düzeltme gerekiyorsa yeni recorded_at ile ekle."
                    )
                result.already_present += 1
                continue
            conn.execute(
                f"INSERT INTO iddaa_odds_log ({', '.join(COLUMNS)}, data_version_id)"
                f" VALUES ({', '.join('?' for _ in COLUMNS)}, ?)",
                (*(r[c] for c in COLUMNS), version_id),
            )
            result.added += 1
    return result
