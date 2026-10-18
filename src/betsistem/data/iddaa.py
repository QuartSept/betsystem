"""İddaa oran kayıtları: tek şablon templates/iddaa_kayit_sablonu.xlsx (karar #79).

Kurallar:
- Takım adları football-data yazımıyla girilir (fikstür dosyasındaki HomeTeam/AwayTeam). Her satır,
  `fikstur_dosyasi` sütununda adı yazılan referans fikstür dosyasındaki bir maçla birebir eşleşmek zorundadır.
  Referans dosya önce `betsistem import-fixtures` ile yüklenmiş olmalıdır.
- Kayıt zamanı Türkiye saatidir (+03:00). Fikstür dosyasının indirme anından 2 saatten uzak kayıtlar
  kaydedilir ama uyarı verilir (karar #76'daki ±2 saat kuralı analizde ayrıca uygulanır).
- Dosya birikimli tutulabilir: daha önce eklenmiş satırlar atlanır. Aynı (kayıt zamanı, ev, deplasman) için
  farklı oran veya MBS gelirse hiçbir şey yazılmaz, hata verilir; düzeltme yeni bir kayıt zamanıyla eklenir.
- Hatalı satır varsa dosyanın hiçbir satırı yazılmaz; tüm hatalar birlikte listelenir.
"""

import difflib
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path

import openpyxl

from betsistem.config import LEAGUES, RAW_DIR, season_of
from betsistem.data.fixtures import TR, fixture_matches
from betsistem.data.raw import RawDataError, store_raw

SOURCE = "iddaa"
SHEET = "Kayıtlar"
COLUMNS = ("kayit_zamani", "lig", "mac_tarihi", "mac_saati", "ev_sahibi", "deplasman",
           "iddaa_1", "iddaa_x", "iddaa_2", "mbs", "fikstur_dosyasi", "not")
REQUIRED = ("kayit_zamani", "lig", "mac_tarihi", "ev_sahibi", "deplasman", "iddaa_1", "iddaa_x", "iddaa_2",
            "mbs", "fikstur_dosyasi")
MAX_GAP = timedelta(hours=2)  # karar #76


@dataclass
class IddaaImportResult:
    added: int = 0
    already_present: int = 0
    warnings: list[str] = field(default_factory=list)


def _parse_datetime(v) -> datetime:
    if isinstance(v, datetime):
        dt = v
    else:
        text = str(v).strip()
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M", "%d.%m.%Y %H:%M:%S"):
            try:
                dt = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        else:
            raise ValueError(f"kayit_zamani anlaşılamadı: {text!r} (örn. 2026-10-23 19:40)")
    return dt.replace(tzinfo=TR) if dt.tzinfo is None else dt.astimezone(TR)


def _parse_date(v) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    text = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"mac_tarihi anlaşılamadı: {text!r} (örn. 2026-10-24)")


def _parse_time(v) -> str | None:
    if v is None or str(v).strip() == "":
        return None
    if isinstance(v, (time, datetime)):
        return v.strftime("%H:%M")
    text = str(v).strip()
    try:
        return datetime.strptime(text[:5], "%H:%M").strftime("%H:%M")
    except ValueError as exc:
        raise ValueError(f"mac_saati anlaşılamadı: {text!r} (örn. 17:00)") from exc


def _parse_price(v, name: str) -> float:
    try:
        price = float(str(v).strip().replace(",", ".")) if not isinstance(v, (int, float)) else float(v)
    except ValueError as exc:
        raise ValueError(f"{name} sayı değil: {v!r}") from exc
    if price <= 1.0:
        raise ValueError(f"{name} 1'den büyük olmalı: {price}")
    return price


def _parse_mbs(v) -> int:
    try:
        mbs = int(float(str(v).replace(",", ".")))
    except ValueError as exc:
        raise ValueError(f"mbs tam sayı değil: {v!r}") from exc
    if mbs < 1:
        raise ValueError(f"mbs en az 1 olmalı: {mbs}")
    return mbs


def read_rows(path: Path) -> list[tuple[int, dict]]:
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    if SHEET not in wb.sheetnames:
        raise RawDataError(f"'{SHEET}' sayfası yok; şablon: templates/iddaa_kayit_sablonu.xlsx")
    rows = list(wb[SHEET].iter_rows(values_only=True))
    header = [str(h).strip() if h is not None else "" for h in rows[0]]
    if tuple(header[: len(COLUMNS)]) != COLUMNS:
        raise RawDataError(f"Başlık satırı şablonla aynı olmalı: {', '.join(COLUMNS)}")
    out = []
    for i, raw in enumerate(rows[1:], start=2):
        rec = dict(zip(COLUMNS, raw[: len(COLUMNS)]))
        if all(rec[c] in (None, "") for c in COLUMNS):
            continue  # boş satır (yalnızca formül sütunu dolu olabilir)
        out.append((i, rec))
    return out


def _resolve_fixture(conn, name: str):
    row = conn.execute(
        "SELECT data_version_id, downloaded_at FROM fixture_downloads WHERE file_name = ?", (name,)
    ).fetchone()
    if row is None:
        raise ValueError(f"fikstür dosyası '{name}' yüklenmemiş; önce: betsistem import-fixtures {name}")
    return row["data_version_id"], datetime.fromisoformat(row["downloaded_at"])


def import_iddaa(conn: sqlite3.Connection, file: Path, *, raw_dir: Path = RAW_DIR) -> IddaaImportResult:
    file = Path(file)
    rows = read_rows(file)
    result = IddaaImportResult()
    if not rows:
        return result

    errors, parsed = [], []
    fixtures_cache: dict[int, object] = {}
    for line, rec in rows:
        try:
            missing = [c for c in REQUIRED if rec[c] in (None, "")]
            if missing:
                raise ValueError(f"boş zorunlu alan: {', '.join(missing)}")
            recorded = _parse_datetime(rec["kayit_zamani"])
            league = str(rec["lig"]).strip()
            if league not in LEAGUES:
                raise ValueError(f"lig kodu tanınmıyor: {league!r} (örn. E0, T1)")
            match_date = _parse_date(rec["mac_tarihi"])
            if recorded.date() > match_date:
                raise ValueError("kayit_zamani maç tarihinden sonra olamaz")
            home, away = str(rec["ev_sahibi"]).strip(), str(rec["deplasman"]).strip()
            fx_version, downloaded = _resolve_fixture(conn, str(rec["fikstur_dosyasi"]).strip())
            if fx_version not in fixtures_cache:
                fixtures_cache[fx_version] = fixture_matches(conn, fx_version, raw_dir)
            fx = fixtures_cache[fx_version]
            lg = fx[fx.Div == league]
            hit = lg[(lg.HomeTeam == home) & (lg.AwayTeam == away)]
            if hit.empty:
                names = sorted(set(lg.HomeTeam) | set(lg.AwayTeam))
                hints = [f"{n!r} -> {difflib.get_close_matches(n, names, n=1, cutoff=0.5)}"
                         for n in (home, away) if n not in names]
                raise ValueError(
                    f"{home} - {away} ({league}) referans fikstür dosyasında yok."
                    + (f" Yazım önerisi: {'; '.join(hints)}" if hints else " Takımlar doğru, maç bu dosyada yok.")
                )
            parsed.append({
                "recorded_at": recorded.isoformat(timespec="minutes"),
                "league": league,
                "match_date": match_date.isoformat(),
                "kickoff_time": _parse_time(rec["mac_saati"]),
                "home_team": home,
                "away_team": away,
                "price_home": _parse_price(rec["iddaa_1"], "iddaa_1"),
                "price_draw": _parse_price(rec["iddaa_x"], "iddaa_x"),
                "price_away": _parse_price(rec["iddaa_2"], "iddaa_2"),
                "mbs": _parse_mbs(rec["mbs"]),
                "fixtures_version_id": fx_version,
                "note": (str(rec["not"]).strip() or None) if rec["not"] is not None else None,
            })
            if abs(recorded - downloaded) > MAX_GAP:
                result.warnings.append(
                    f"Satır {line}: kayıt {recorded:%Y-%m-%d %H:%M}, fikstür indirme {downloaded:%Y-%m-%d %H:%M}; "
                    "fark 2 saatten fazla (karar #76)"
                )
        except ValueError as exc:
            errors.append(f"Satır {line}: {exc}")
    if errors:
        raise RawDataError("İddaa dosyasında hata var, hiçbir satır yazılmadı:\n  " + "\n  ".join(errors))

    content = file.read_bytes()
    version_id = store_raw(
        conn, content, source=SOURCE, league="ALL", season=season_of(date.fromisoformat(parsed[0]["match_date"])),
        origin=f"manual:{file.name}", suffix=".xlsx", raw_dir=raw_dir,
    )
    cols = list(parsed[0]) + ["data_version_id"]
    with conn:
        for r in parsed:
            existing = conn.execute(
                "SELECT price_home, price_draw, price_away, mbs FROM iddaa_odds_log"
                " WHERE recorded_at = ? AND home_team = ? AND away_team = ?",
                (r["recorded_at"], r["home_team"], r["away_team"]),
            ).fetchone()
            if existing:
                if tuple(existing) != (r["price_home"], r["price_draw"], r["price_away"], r["mbs"]):
                    raise RawDataError(
                        f"{r['recorded_at']} {r['home_team']} - {r['away_team']} daha önce farklı oran/MBS ile"
                        " kaydedilmiş; kayıtlar değiştirilemez. Düzeltme gerekiyorsa yeni kayit_zamani ile ekle."
                    )
                result.already_present += 1
                continue
            conn.execute(
                f"INSERT INTO iddaa_odds_log ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})",
                (*r.values(), version_id),
            )
            result.added += 1
    return result
