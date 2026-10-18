"""Yeni lig protokolü (karar #48): bir ligde Faz 2, Faz 3 ve hareket testi.

Faz 4'e geçiş hareket testine (karar #46) bağlıdır; bu modül backtest çalıştırmaz.
"""

import sqlite3
from datetime import datetime, timezone

from betsistem.config import LEAGUES, season_label
from betsistem.data.understat import LEAGUE_CODES as UNDERSTAT_LEAGUES
from betsistem.model import metrics
from betsistem.model.evaluation import COLS, _market
from betsistem.model.experiments import (
    CHECK_SEASONS,
    EVAL_SEASONS,
    TUNING_SEASONS,
    _grid_md,
    _vs_market,
    run,
)
from betsistem.model.movement import MovementResult, movement_test
from betsistem.model.predict import save_predictions
from betsistem.report import markdown_table as _md


def league_movement(exp, config) -> MovementResult:
    preds = exp.predictions(config).set_index("match_id")
    early = _market(exp.conn, "PS", "early", exp.league).set_index("match_id")
    close = _market(exp.conn, "PS", "closing", exp.league).set_index("match_id")
    ids = preds.index.intersection(early.index).intersection(close.index)
    return movement_test(preds.loc[ids, COLS].to_numpy(), early.loc[ids, COLS].to_numpy(),
                         close.loc[ids, COLS].to_numpy())


def analyse_league(conn: sqlite3.Connection, league: str) -> dict:
    use_xg = league in UNDERSTAT_LEAGUES and conn.execute(
        "SELECT COUNT(*) FROM match_xg x JOIN matches m ON m.id = x.match_id WHERE m.league = ?", (league,)
    ).fetchone()[0] > 0
    r = run(conn, league, use_xg=use_xg)
    exp, base, final = r["exp"], r["base"], r["final"]
    save_predictions(conn, "poisson", final.key(), exp.predictions(final))
    summary, gaps = _vs_market(exp, {"Faz 2 Poisson": base, "Faz 3 model": final})
    r |= {"use_xg": use_xg, "summary": summary, "gaps": gaps, "movement": league_movement(exp, final)}
    return r


def render_league_report(conn: sqlite3.Connection, league: str) -> tuple[str, dict]:
    r = analyse_league(conn, league)
    exp, final, mv = r["exp"], r["final"], r["movement"]
    fp = exp.predictions(final)
    calib = metrics.calibration_table(fp[COLS].to_numpy(), fp.ftr)
    calib = calib[calib.n >= 20]

    parts = [
        f"# {LEAGUES.get(league, league)} ({league}): Faz 2, Faz 3 ve hareket testi",
        f"Oluşturulma: {datetime.now(timezone.utc).isoformat(timespec='seconds')} (UTC).",
        "## Protokol (karar #48)",
        "\n".join([
            "- 2019/20 ısınma; değerlendirme "
            + ", ".join(season_label(s) for s in EVAL_SEASONS)
            + f" ({len(fp)} maç). Kilitli final sezonları (2023/24–2024/25) yüklenmedi.",
            f"- Ayarlar yalnızca {', '.join(season_label(s) for s in TUNING_SEASONS)}'de seçildi; "
            f"{', '.join(season_label(s) for s in CHECK_SEASONS)} iç kontrol (karar #33).",
            f"- xG: {'denendi' if r['use_xg'] else 'Understat kapsamında değil, denenmedi'}.",
            f"- Seçilen model: `{final.key()}`. Karar: "
            + ", ".join(f"{k} {'tutuldu' if v else 'elendi'}" for k, v in r["kept"].items()) + ".",
        ]),
        "## Faz 3 adımları (log-loss farkı, negatif = iyileşme)",
        _md(r["cumulative"]),
        "## Zaman ağırlığı ızgarası",
        _grid_md(r["time_table"], "xi"),
        "## Piyasa ile karşılaştırma (Faz 2 ve Faz 3)",
        _md(r["summary"]),
        _md(r["gaps"]),
        "## Hareket testi (karar #46)",
        f"{mv.matches} maç, eğim {mv.slope:.4f} (tek yönlü %95 alt sınır {mv.lo_one_sided:.4f}; "
        f"%95 GA {mv.lo:.4f} … {mv.hi:.4f}): **{'geçti' if mv.passes else 'geçemedi'}**.",
        "Sonuç bazında (bilgi amaçlı): "
        + ", ".join(f"{o}: eğim {mv.slope_by_outcome[o]:+.3f}, korelasyon {mv.corr_by_outcome[o]:+.3f}"
                    for o in ("H", "D", "A")) + ".",
        "## Faz 3 modelinin kalibrasyonu",
        _md(calib),
    ]
    return "\n\n".join(parts) + "\n", r
