"""football-data.co.uk CSV'lerini okuyup matches ve odds tablolarına yükler."""

import re
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from betsistem.config import MARKET_1X2, RAW_DIR, season_of
from betsistem.data.db import get_or_create_team
from betsistem.data.raw import FOOTBALL_DATA_SOURCE

# 1-X-2 oran sütunları: <şirket kodu>[C]<H|D|A>. 'C' kapanış oranı demektir.
# Kodlar football-data notlarından: PS = Pinnacle, Max/Avg = piyasa en yüksek/ortalama,
# BbMx/BbAv = eski sezonlardaki Betbrain en yüksek/ortalama. Kod listesi yeni sezonlarda büyür
# (BFD = Betfred, BMGM = BetMGM, BV = BetVictor, CL = Coral, PP = Paddy Power, SK/SKB = Sky Bet; notlarda SK, dosyalarda SKB geçiyor).
# Alt/üst ve Asya handikap sütunları bu kalıba uymaz, bilerek dışarıda kalır (karar #10).
ODDS_COLUMN = re.compile(
    r"^(?P<bookmaker>BbMx|BbAv|BMGM|B365|SKB|SK|BFE|BFD|1XB|BW|BV|CL|IW|PP|PS|WH|VC|Max|Avg|BF|LB|SJ|GB|BS|SB|SO|SY)"
    r"(?P<closing>C)?(?P<outcome>[HDA])$"
)

REQUIRED_COLUMNS = ("Div", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR")

# DB sütunu -> CSV sütunu
MATCH_STAT_COLUMNS = {
    "hthg": "HTHG",
    "htag": "HTAG",
    "referee": "Referee",
    "home_shots": "HS",
    "away_shots": "AS",
    "home_shots_on_target": "HST",
    "away_shots_on_target": "AST",
}


@dataclass
class OddsColumn:
    column: str
    bookmaker: str
    timing: str  # 'early' | 'closing'
    outcome: str  # 'H' | 'D' | 'A'


@dataclass
class LoadResult:
    matches: int = 0
    odds: int = 0
    skipped_invalid_prices: int = 0
    odds_columns: list[str] = field(default_factory=list)


def parse_odds_columns(columns) -> list[OddsColumn]:
    parsed = []
    for col in columns:
        m = ODDS_COLUMN.match(col)
        if m:
            parsed.append(
                OddsColumn(
                    column=col,
                    bookmaker=m["bookmaker"],
                    timing="closing" if m["closing"] else "early",
                    outcome=m["outcome"],
                )
            )
    return parsed


def parse_date(value: str) -> str:
    """football-data tarihleri dd/mm/yyyy (eski dosyalarda dd/mm/yy)."""
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(value.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"Tarih çözümlenemedi: {value!r}")


def read_football_data_csv(path: Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin-1")
    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    df = df.dropna(subset=["HomeTeam", "AwayTeam"])
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path} içinde eksik sütunlar: {missing}")
    return df.reset_index(drop=True)


def _int_or_none(value):
    return None if pd.isna(value) else int(value)


def _str_or_none(value):
    return None if pd.isna(value) else str(value).strip()


def load_football_data(conn: sqlite3.Connection, data_version_id: int, *, raw_dir: Path = RAW_DIR) -> LoadResult:
    """Bir veri sürümünü yükler. Tekrar çalıştırılabilir: maç id'leri korunur, oranlar yenilenir."""
    version = conn.execute("SELECT * FROM data_versions WHERE id = ?", (data_version_id,)).fetchone()
    if version is None:
        raise ValueError(f"data_versions içinde id={data_version_id} yok")
    if version["source"] != FOOTBALL_DATA_SOURCE:
        raise ValueError(f"Beklenen kaynak {FOOTBALL_DATA_SOURCE}, gelen {version['source']}")

    df = read_football_data_csv(raw_dir / version["file_path"])
    divisions = set(df["Div"].dropna().unique())
    if divisions != {version["league"]}:
        raise ValueError(f"Dosyadaki lig {divisions}, beklenen {version['league']}")

    first_date = min(date.fromisoformat(parse_date(str(d))) for d in df["Date"])
    if season_of(first_date) != version["season"]:
        raise ValueError(
            f"Dosyanın ilk maçı {first_date} ({season_of(first_date)} sezonu), beklenen sezon {version['season']}"
        )

    odds_cols = parse_odds_columns(df.columns)
    result = LoadResult(odds_columns=[c.column for c in odds_cols])

    with conn:
        # itertuples geçersiz Python adlarını (B365>2.5 gibi) yeniden adlandırır; sütun adıyla erişim için dict.
        for row in df.itertuples(index=False):
            rec = dict(zip(df.columns, row))
            home_id = get_or_create_team(conn, FOOTBALL_DATA_SOURCE, str(rec["HomeTeam"]).strip())
            away_id = get_or_create_team(conn, FOOTBALL_DATA_SOURCE, str(rec["AwayTeam"]).strip())

            values = {
                "league": version["league"],
                "season": version["season"],
                "match_date": parse_date(str(rec["Date"])),
                "kickoff_time": _str_or_none(rec.get("Time")),
                "home_team_id": home_id,
                "away_team_id": away_id,
                "fthg": _int_or_none(rec["FTHG"]),
                "ftag": _int_or_none(rec["FTAG"]),
                "ftr": _str_or_none(rec["FTR"]),
                "data_version_id": data_version_id,
            }
            for db_col, csv_col in MATCH_STAT_COLUMNS.items():
                raw = rec.get(csv_col)
                values[db_col] = _str_or_none(raw) if db_col == "referee" else _int_or_none(raw)

            cols = ", ".join(values)
            placeholders = ", ".join("?" for _ in values)
            updates = ", ".join(
                f"{c} = excluded.{c}" for c in values if c not in ("league", "season", "home_team_id", "away_team_id")
            )
            match_id = conn.execute(
                f"INSERT INTO matches ({cols}) VALUES ({placeholders})"
                f" ON CONFLICT (league, season, home_team_id, away_team_id) DO UPDATE SET {updates}"
                " RETURNING id",
                tuple(values.values()),
            ).fetchone()["id"]
            result.matches += 1

            conn.execute("DELETE FROM odds WHERE match_id = ? AND source = ?", (match_id, FOOTBALL_DATA_SOURCE))
            for oc in odds_cols:
                price = rec[oc.column]
                if pd.isna(price):
                    continue
                try:
                    price = float(price)
                except ValueError:  # ör. '#': bozuk hücre
                    result.skipped_invalid_prices += 1
                    continue
                if price <= 1.0:
                    result.skipped_invalid_prices += 1
                    continue
                conn.execute(
                    "INSERT INTO odds (match_id, source, bookmaker, market, outcome, timing, price,"
                    " recorded_at, data_version_id) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?)",
                    (match_id, FOOTBALL_DATA_SOURCE, oc.bookmaker, MARKET_1X2, oc.outcome, oc.timing, price,
                     data_version_id),
                )
                result.odds += 1
    return result
