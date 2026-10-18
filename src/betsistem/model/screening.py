"""Lig taraması (karar #47): model kurmadan, yalnızca Pinnacle oranlarıyla ligleri karşılaştırır.

Ölçüt bilgi kazancı = log-loss(marjsız erken) − log-loss(marjsız kapanış). Büyükse erken oranlar daha
az isabetlidir: karar anından sonra piyasaya daha çok bilgi girer, model için daha geniş alan vardır.
Yalnızca 2019/20–2022/23 kullanılır; 2023/24–2024/25 her ligin kilitli final setidir.
"""

import sqlite3
from datetime import datetime, timezone

import pandas as pd

from betsistem.config import LEAGUES, MODEL_SELECTION_SEASONS
from betsistem.data.understat import LEAGUE_CODES as UNDERSTAT_LEAGUES
from betsistem.model import metrics
from betsistem.model.experiments import FAZ3_MODEL, TUNING_SEASONS, CHECK_SEASONS
from betsistem.model.market import market_prices, remove_margin
from betsistem.model.movement import movement_test
from betsistem.model.predict import load_matches, walk_forward
from betsistem.model.timeline import assert_unlocked
from betsistem.report import markdown_table as _md

SCREEN_SEASONS = MODEL_SELECTION_SEASONS  # 2019/20–2022/23
MIN_MATCHES = 900
MIN_COVERAGE = 0.90
SELECT_COUNT = 2
REFERENCE_LEAGUE = "E0"


def _fair(conn, timing: str) -> pd.DataFrame:
    p = market_prices(conn, "PS", league=None)
    p = p[p.index.get_level_values("timing") == timing]
    out = remove_margin(p).reset_index()
    return out[["match_id", "H", "D", "A", "overround"]].set_index("match_id")


def league_table(conn: sqlite3.Connection) -> pd.DataFrame:
    assert_unlocked(SCREEN_SEASONS)
    placeholders = ",".join("?" for _ in SCREEN_SEASONS)
    matches = pd.read_sql(
        f"SELECT id AS match_id, league, ftr FROM matches WHERE season IN ({placeholders})",
        conn, params=SCREEN_SEASONS,
    ).set_index("match_id")
    early, close = _fair(conn, "early"), _fair(conn, "closing")

    rows = []
    for league, g in matches.groupby("league"):
        ids = g.index[g.index.isin(early.index) & g.index.isin(close.index) & g.ftr.notna()]
        row = {"lig": league, "ad": LEAGUES.get(league, league), "maç": len(g), "PS erken+kapanış": len(ids),
               "doluluk": round(len(ids) / len(g), 3) if len(g) else 0.0,
               "xG (Understat)": "var" if league in UNDERSTAT_LEAGUES else "yok"}
        if len(ids):
            ll_e = metrics.log_loss_per_match(early.loc[ids, ["H", "D", "A"]].to_numpy(), g.ftr[ids])
            ll_c = metrics.log_loss_per_match(close.loc[ids, ["H", "D", "A"]].to_numpy(), g.ftr[ids])
            mean, lo, hi = metrics.paired_bootstrap(ll_e - ll_c)
            row |= {"bilgi kazancı": round(mean, 4), "%95 GA": f"{lo:.4f} … {hi:.4f}",
                    "kapanış log-loss": round(ll_c.mean(), 4),
                    "kapanış marjı": round(close.loc[ids, "overround"].mean() - 1, 4),
                    "erken marjı": round(early.loc[ids, "overround"].mean() - 1, 4)}
        row["uygun"] = row["PS erken+kapanış"] >= MIN_MATCHES and row["doluluk"] >= MIN_COVERAGE
        rows.append(row)
    return pd.DataFrame(rows)


def select_leagues(table: pd.DataFrame) -> list[str]:
    """Karar #47: uygun adaylar (Premier League hariç) arasında bilgi kazancı en yüksek iki lig."""
    cand = table[(table.lig != REFERENCE_LEAGUE) & table.uygun].sort_values("bilgi kazancı", ascending=False)
    return cand.lig.head(SELECT_COUNT).tolist()


def epl_movement(conn: sqlite3.Connection):
    """Referans: Premier League Faz 3 modelinin seçim dönemindeki hareket testi (karar #46)."""
    seasons = TUNING_SEASONS + CHECK_SEASONS
    preds = walk_forward(load_matches(conn), seasons, FAZ3_MODEL).set_index("match_id")
    early, close = _fair(conn, "early"), _fair(conn, "closing")
    ids = preds.index.intersection(early.index).intersection(close.index)
    return movement_test(
        preds.loc[ids, ["p_home", "p_draw", "p_away"]].to_numpy(),
        early.loc[ids, ["H", "D", "A"]].to_numpy(),
        close.loc[ids, ["H", "D", "A"]].to_numpy(),
    )


def render_report(conn: sqlite3.Connection) -> str:
    table = league_table(conn)
    chosen = select_leagues(table)
    ordered = table.sort_values("bilgi kazancı", ascending=False)
    mv = epl_movement(conn)

    parts = [
        "# Lig taraması (karar #47)",
        f"Oluşturulma: {datetime.now(timezone.utc).isoformat(timespec='seconds')} (UTC).",
        "## Kurallar (ön kayıt)",
        "\n".join([
            "- Sezonlar: 2019/20–2022/23. Model kurulmadı; yalnızca marjsız Pinnacle erken ve kapanış olasılıkları.",
            "- Bilgi kazancı = log-loss(erken) − log-loss(kapanış), maç başına ortalama; bootstrap %95 GA.",
            f"- Uygunluk: en az {MIN_MATCHES} maçta erken ve kapanış birlikte dolu, doluluk ≥ %{int(MIN_COVERAGE * 100)}.",
            f"- Seçim: Premier League dışındaki uygun ligler arasında bilgi kazancı en yüksek {SELECT_COUNT} lig. "
            "Marj, maç sayısı ve xG yalnızca bilgi içindir.",
        ]),
        "## Sonuç",
        f"Seçilen ligler: **{', '.join(f'{c} ({LEAGUES.get(c, c)})' for c in chosen) or 'yok'}**.",
        "## Lig tablosu (bilgi kazancına göre)",
        _md(ordered),
        "## Referans: Premier League Faz 3 modelinin hareket testi (karar #46)",
        f"{mv.matches} maç, eğim {mv.slope:.4f} (tek yönlü %95 alt sınır {mv.lo_one_sided:.4f}; "
        f"%95 GA {mv.lo:.4f} … {mv.hi:.4f}): **{'geçti' if mv.passes else 'geçemedi'}**. "
        "Sonuç bazında korelasyon: "
        + ", ".join(f"{o} {r:+.3f}" for o, r in mv.corr_by_outcome.items()) + ".",
    ]
    return "\n\n".join(parts) + "\n"
