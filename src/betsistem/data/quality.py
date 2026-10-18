"""Veri kalite raporu: sezon ve sütun bazında doluluk, xG kapsaması, Pinnacle tutarlılığı.

Sezon özeti tüm ligleri kapsar; oran ve Pinnacle bölümleri Premier League (E0) içindir. Diğer liglerin
oran kalitesi lig taraması raporunda (karar #47) yer alır.

Yalnızca veri kalitesine bakar; sonuçlara veya getirilere bakmaz. Bu yüzden kilitli final
sezonlarında (karar #15) da çalıştırılabilir.
"""

import sqlite3
from datetime import datetime, timezone

import pandas as pd

from betsistem.config import BET_PRICE_BOOKMAKER, is_final_test_season, season_label
from betsistem.model.market import fair_probabilities
from betsistem.report import markdown_table as _md

# Bir maçta 1-X-2 olasılıkları toplamı bu aralığın dışındaysa şüpheli sayılır.
OVERROUND_MIN, OVERROUND_MAX = 1.0, 1.10
# Erken ile kapanış arasında marjsız olasılık bu kadardan fazla oynadıysa raporlanır.
LARGE_MOVE = 0.20
# Pinnacle ile piyasa ortalamasının marjsız olasılıkları bu kadardan fazla ayrışırsa raporlanır.
PS_AVG_GAP = 0.10


def season_overview(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT m.league, m.season, COUNT(*) AS matches, MIN(m.match_date) AS first, MAX(m.match_date) AS last,
               SUM(m.ftr IS NULL) AS missing_result, SUM(m.kickoff_time IS NULL) AS missing_time,
               COUNT(x.match_id) AS xg_matches, COUNT(x.home_npxg) AS npxg_matches
        FROM matches m LEFT JOIN match_xg x ON x.match_id = m.id
        GROUP BY m.league, m.season ORDER BY m.league, m.season
        """,
        conn,
    )


def odds_coverage(conn: sqlite3.Connection) -> pd.DataFrame:
    """Sezon x (şirket, zaman) için üç sonucun da dolu olduğu maç oranı (%)."""
    df = pd.read_sql(
        """
        SELECT m.season, o.bookmaker || ':' || o.timing AS col, COUNT(*) AS n
        FROM (SELECT match_id, bookmaker, timing FROM odds WHERE market = '1X2'
              GROUP BY match_id, bookmaker, timing HAVING COUNT(DISTINCT outcome) = 3) o
        JOIN matches m ON m.id = o.match_id
        WHERE m.league = 'E0'
        GROUP BY m.season, col
        """,
        conn,
    )
    totals = pd.read_sql("SELECT season, COUNT(*) AS total FROM matches WHERE league = 'E0' GROUP BY season", conn)
    df = df.merge(totals, on="season")
    df["pct"] = (100 * df["n"] / df["total"]).round(1)
    return df.pivot(index="col", columns="season", values="pct").fillna(0.0).sort_index()


# Eksik ana fiyat listesinde gösterilecek en fazla maç.
MISSING_LIST_LIMIT = 40


def _complete_matches_sql(timing: str) -> str:
    return (
        "SELECT match_id FROM odds WHERE market = '1X2' AND bookmaker = :bk AND timing = '" + timing + "'"
        " GROUP BY match_id HAVING COUNT(DISTINCT outcome) = 3"
    )


def bet_price_missing(conn: sqlite3.Connection, bookmaker: str = BET_PRICE_BOOKMAKER) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Ana bahis fiyatının (karar #24) eksik olduğu maçlar. Bu maçlarda bahis yapılmaz (karar #27)."""
    matches = pd.read_sql(
        f"""
        SELECT m.id, m.season, m.match_date, h.name AS home, a.name AS away,
               m.id IN ({_complete_matches_sql('early')}) AS has_early,
               m.id IN ({_complete_matches_sql('closing')}) AS has_closing
        FROM matches m JOIN teams h ON h.id = m.home_team_id JOIN teams a ON a.id = m.away_team_id
        WHERE m.league = 'E0'
        ORDER BY m.match_date
        """,
        conn,
        params={"bk": bookmaker},
    )
    summary = matches.groupby("season").agg(
        matches=("id", "count"),
        early_missing=("has_early", lambda s: int((s == 0).sum())),
        closing_missing=("has_closing", lambda s: int((s == 0).sum())),
    ).reset_index()
    dates = matches.groupby("season").agg(
        last_early=("match_date", lambda d: d[matches.loc[d.index, "has_early"] == 1].max()),
        first_missing=("match_date", lambda d: d[matches.loc[d.index, "has_early"] == 0].min()),
    ).reset_index()
    summary = summary.merge(dates, on="season")
    summary["early_missing_pct"] = (100 * summary["early_missing"] / summary["matches"]).round(2)
    summary["closing_missing_pct"] = (100 * summary["closing_missing"] / summary["matches"]).round(2)
    missing = matches[(matches.has_early == 0) | (matches.has_closing == 0)].copy()
    missing["missing"] = missing.apply(
        lambda r: ", ".join(t for t, ok in (("early", r.has_early), ("closing", r.has_closing)) if not ok), axis=1
    )
    return summary, missing[["season", "match_date", "home", "away", "missing"]]


def pinnacle_consistency(conn: sqlite3.Connection) -> tuple[pd.DataFrame, pd.DataFrame]:
    ps = fair_probabilities(conn, "PS")
    if ps.empty:
        return pd.DataFrame(), pd.DataFrame()

    margin = ps.groupby(["season", "timing"])["overround"].agg(
        n="count",
        mean=lambda s: round(s.mean(), 4),
        min=lambda s: round(s.min(), 4),
        max=lambda s: round(s.max(), 4),
        out_of_range=lambda s: int(((s < OVERROUND_MIN) | (s > OVERROUND_MAX)).sum()),
    ).reset_index()

    early = ps[ps.timing == "early"].set_index(["match_id", "season"])[["H", "D", "A"]]
    close = ps[ps.timing == "closing"].set_index(["match_id", "season"])[["H", "D", "A"]]
    move = (close - early).abs().max(axis=1).dropna().rename("max_move").reset_index()

    avg = fair_probabilities(conn, "Avg")
    gap = pd.DataFrame()
    if not avg.empty:
        a = avg.set_index(["match_id", "season", "timing"])[["H", "D", "A"]]
        p = ps.set_index(["match_id", "season", "timing"])[["H", "D", "A"]]
        gap = (p - a).abs().max(axis=1).dropna().rename("gap").reset_index()

    checks = []
    for season, grp in move.groupby("season"):
        row = {
            "season": season,
            "early_closing_pairs": len(grp),
            "median_move": round(grp["max_move"].median(), 4),
            f"move>{LARGE_MOVE}": int((grp["max_move"] > LARGE_MOVE).sum()),
        }
        if not gap.empty:
            g = gap[gap.season == season]
            row["ps_vs_avg_median_gap"] = round(g["gap"].median(), 4)
            row[f"ps_vs_avg_gap>{PS_AVG_GAP}"] = int((g["gap"] > PS_AVG_GAP).sum())
        checks.append(row)
    return margin, pd.DataFrame(checks)


def data_versions(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql(
        "SELECT id, source, league, season, origin, substr(sha256, 1, 12) AS sha256, acquired_at"
        " FROM data_versions ORDER BY source, season, id",
        conn,
    )


def render_report(conn: sqlite3.Connection) -> str:
    overview = season_overview(conn)
    overview.insert(2, "label", overview["season"].map(season_label))
    overview["final_test"] = overview["season"].map(lambda s: "kilitli" if is_final_test_season(s) else "")
    margin, checks = pinnacle_consistency(conn)
    missing_summary, missing = bet_price_missing(conn)

    parts = [
        "# Veri kalite raporu",
        f"Oluşturulma: {datetime.now(timezone.utc).isoformat(timespec='seconds')} (UTC). "
        "Bu rapor yalnızca veri kalitesine bakar; sonuç veya getiri içermez.",
        "## Sezonlar",
        _md(overview),
        "## 1-X-2 oran doluluğu (%)",
        "Üç sonucun da dolu olduğu maçların oranı. `early` = football-data erken oran saati, `closing` = kapanış.",
        _md(odds_coverage(conn).reset_index()),
        f"## Ana bahis fiyatı ({BET_PRICE_BOOKMAKER}) eksikliği",
        "Karar #27: ana fiyatın erken oranı eksik maçta bahis yapılmaz, başka şirketle doldurulmaz. "
        "Eksiklik yüksekse ve maçlar rastgele dağılmıyorsa karar yeniden konuşulur.",
        _md(missing_summary),
        f"Eksik maçlar (ilk {MISSING_LIST_LIMIT}, toplam {len(missing)}):",
        _md(missing.head(MISSING_LIST_LIMIT)),
        "## Pinnacle marjı (olasılık toplamı)",
        f"`out_of_range`: toplamı {OVERROUND_MIN} altında veya {OVERROUND_MAX} üstünde olan maç sayısı.",
        _md(margin),
        "## Pinnacle tutarlılık kontrolleri",
        f"`max_move`: erken ile kapanış arasında marjsız olasılığın en büyük değişimi. "
        f"`ps_vs_avg_gap`: Pinnacle ile piyasa ortalamasının marjsız olasılık farkı (aynı zaman dilimi).",
        _md(checks),
        "## Veri sürümleri",
        _md(data_versions(conn)),
    ]
    return "\n\n".join(parts) + "\n"
