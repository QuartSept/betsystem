"""Faz 10 testleri: ön kayıtlara birebir uyarak çalıştırılır.

Ön kayıtlar: docs/on-kayit/faz10_10a.md (3a4f8d2), faz10_10c.md (03c39d1), faz10_10d.md (1ade138).
Tüm nihai kararlar tek yönlü α = 0,05/3 ile (#72); eşik seçimi #40 kuralıyla; N fizibilite aracıyla (#71).
"""

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from betsistem.asama2.feasibility import (
    ALPHA_FAZ10,
    K_GRID_10A,
    MODEL_SEASONS,
    MODELLESS_SEASONS,
    feasibility_10a,
    feasibility_10c,
    feasibility_10d,
    model_ou_probabilities,
)
from betsistem.backtest import engine
from betsistem.config import MARKET_1X2, MARKET_OU25, season_label
from betsistem.model.experiments import LEAGUE_MODELS, run as faz3_run
from betsistem.model.market import market_prices, remove_margin
from betsistem.model.movement import MovementResult, movement_test
from betsistem.model.timeline import assert_unlocked, decision_date
from betsistem.report import markdown_table as _md

X12 = ["H", "D", "A"]
OU = ["O", "U"]


def _snap(conn, bookmaker, league, timing, market=MARKET_1X2) -> pd.DataFrame:
    p = market_prices(conn, bookmaker, league, market).xs(timing, level="timing")
    return p.reset_index(level="season")  # index: match_id, sütunlar: season + sonuçlar


def _match_info(conn, league) -> pd.DataFrame:
    df = pd.read_sql("SELECT id AS match_id, match_date, ftr, fthg, ftag FROM matches WHERE league = ?",
                     conn, params=(league,)).set_index("match_id")
    df["decision_date"] = pd.to_datetime(df.match_date).dt.date.map(decision_date).astype(str)
    return df


def _settle(bets: pd.DataFrame, results: pd.Series) -> pd.DataFrame:
    """bets: match_id, outcome, price, p_model, p_close, decision_date, season, league."""
    out = bets.copy()
    out["clv"] = out.price * out.p_close - 1.0
    out["won"] = results.reindex(out.match_id).to_numpy() == out.outcome.to_numpy()
    out["pnl"] = np.where(out.won, out.price - 1.0, -1.0)
    return out


def _row(label: str, s: engine.Summary) -> dict:
    return {
        "": label,
        "bahis": s.bets,
        "ort. CLV": round(s.clv["mean"], 4),
        f"CLV alt (tek yönlü, α={ALPHA_FAZ10:.4f})": round(s.clv["lo_one_sided"], 4),
        "CLV %95 GA": f"{s.clv['lo']:.4f} … {s.clv['hi']:.4f}",
        "ROI": round(s.roi["mean"], 4),
        "ROI %95 GA": f"{s.roi['lo']:.4f} … {s.roi['hi']:.4f}",
        "¼ Kelly kasa (100'den)": round(s.kelly_final, 1),
    }


def _breakdown(settled: pd.DataFrame) -> list[dict]:
    rows = []
    for (lg, season), g in settled.groupby(["league", "season"]):
        rows.append(_row(f"{lg} {season_label(season)}", engine.summarize(g, alpha=ALPHA_FAZ10)))
    return rows


class Faz10AlreadyRun(Exception):
    pass


def _assert_not_run(conn) -> None:
    done = [r[0] for r in conn.execute("SELECT test FROM faz10_runs")]
    if done:
        raise Faz10AlreadyRun(f"Faz 10 testleri daha önce çalıştırıldı ({', '.join(done)}); ikinci çalıştırma yapılamaz (#83).")


def _record_runs(conn, results) -> None:
    from betsistem.asama2.faz11 import _git_commit
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with conn:
        for r in results:
            conn.execute("INSERT INTO faz10_runs (test, run_at, git_commit, result) VALUES (?, ?, ?, ?)",
                         (r.name, now, _git_commit(), r.verdict))


@dataclass
class TestResult:
    name: str
    passed: bool
    verdict: str
    sections: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- 10a

def _rule_10a(conn, soft: str, fair_source: str, leagues, seasons) -> tuple[pd.DataFrame, pd.Series]:
    """Maç başına o_soft × p_adil en yüksek sonuç; tüm maçlar (eşik sonra uygulanır)."""
    assert_unlocked(seasons)
    frames, results = [], []
    for lg in leagues:
        soft_e = _snap(conn, soft, lg, "early")
        fair_e = _snap(conn, fair_source, lg, "early")
        ps_c = _snap(conn, "PS", lg, "closing")
        info = _match_info(conn, lg)
        ids = soft_e.index.intersection(fair_e.index).intersection(ps_c.index)
        ids = ids[soft_e.loc[ids, "season"].isin(seasons).to_numpy()]
        if len(ids) == 0:
            continue
        price = soft_e.loc[ids, X12].to_numpy()
        p_fair = remove_margin(fair_e.loc[ids, X12])[X12].to_numpy()
        p_close = remove_margin(ps_c.loc[ids, X12])[X12].to_numpy()
        ratio = price * p_fair
        best = ratio.argmax(axis=1)
        r = np.arange(len(ids))
        frames.append(pd.DataFrame({
            "match_id": ids, "league": lg, "season": soft_e.loc[ids, "season"].to_numpy(),
            "decision_date": info.loc[ids, "decision_date"].to_numpy(),
            "outcome": np.array(X12)[best], "price": price[r, best], "p_model": p_fair[r, best],
            "p_close": p_close[r, best], "ratio": ratio[r, best],
        }))
        results.append(info.ftr)
    return pd.concat(frames, ignore_index=True), pd.concat(results)


def run_10a(conn: sqlite3.Connection) -> TestResult:
    feas = feasibility_10a(conn)
    n_req = feas.n_required
    leagues, seasons = ("E0", "T1"), MODELLESS_SEASONS
    cand, results = _rule_10a(conn, "B365", "Avg", leagues, seasons)

    settled = {k: _settle(cand[cand.ratio > 1 + k], results) for k in K_GRID_10A}
    summaries = {k: engine.summarize(s, alpha=ALPHA_FAZ10) for k, s in settled.items()}
    eligible = {k: s for k, s in summaries.items() if s.bets >= n_req}
    if not eligible:
        return TestResult("10a", False, "Yetersiz güç: hiçbir k N'ye ulaşmadı (#71).")
    chosen = engine.choose_threshold(summaries, n_req)
    main = summaries[chosen]
    passed = main.passes(n_req)

    sens_rows = []
    s_cand, s_res = _rule_10a(conn, "B365", "PS", leagues, seasons)
    s_set = _settle(s_cand[s_cand.ratio > 1 + chosen], s_res)
    sens_rows.append(_row(f"Duyarlılık: p_adil Pinnacle erken (k={chosen:g})", engine.summarize(s_set, alpha=ALPHA_FAZ10)))
    for bk in ("WH", "BW", "IW", "VC"):
        try:
            b_cand, b_res = _rule_10a(conn, bk, "Avg", leagues, seasons)
        except (KeyError, ValueError):  # şirketin bu liglerde oranı yok
            continue
        b_set = _settle(b_cand[b_cand.ratio > 1 + chosen], b_res)
        if len(b_set):
            sens_rows.append(_row(f"Bilgi: {bk} (k={chosen:g}, {b_cand.league.nunique()} lig)",
                                  engine.summarize(b_set, alpha=ALPHA_FAZ10)))

    sections = [
        f"N = {n_req} (fizibilite ile aynı). Aday maç: {len(cand)}.",
        _md(pd.DataFrame([_row(f"k = {k:g}", s) for k, s in summaries.items()])),
        f"**Seçilen k = {chosen:g}** (#40).",
        _md(pd.DataFrame([_row("seçilen", main)] + _breakdown(settled[chosen]))),
        "Ayrıca raporlananlar (karar vermez):",
        _md(pd.DataFrame(sens_rows)),
    ]
    verdict = (f"{'GEÇTİ' if passed else 'Geçmedi'}: {main.bets} bahis, ortalama CLV {main.clv['mean']:.4f}, "
               f"tek yönlü alt sınır {main.clv['lo_one_sided']:.4f}.")
    return TestResult("10a", passed, verdict, sections)


# ---------------------------------------------------------------- 10c

def run_10c(conn: sqlite3.Connection) -> TestResult:
    feas = feasibility_10c(conn)
    n_req = feas.n_required
    frames, results = [], []
    for lg in ("E0", "B1"):
        model = model_ou_probabilities(conn, lg, LEAGUE_MODELS[lg], MODEL_SEASONS)
        early = _snap(conn, "PS", lg, "early", MARKET_OU25)
        close = _snap(conn, "PS", lg, "closing", MARKET_OU25)
        info = _match_info(conn, lg)
        ids = model.index.intersection(early.index).intersection(close.index)
        e_fair = remove_margin(early.loc[ids, OU], OU)[OU]
        c_fair = remove_margin(close.loc[ids, OU], OU)[OU]
        frames.append(pd.DataFrame({
            "match_id": ids, "league": lg, "season": early.loc[ids, "season"].to_numpy(),
            "decision_date": info.loc[ids, "decision_date"].to_numpy(),
            "pm_O": model.loc[ids, "O"].to_numpy(), "pm_U": model.loc[ids, "U"].to_numpy(),
            "o_O": early.loc[ids, "O"].to_numpy(), "o_U": early.loc[ids, "U"].to_numpy(),
            "pe_O": e_fair["O"].to_numpy(), "pc_O": c_fair["O"].to_numpy(), "pc_U": c_fair["U"].to_numpy(),
        }))
        total = info.fthg + info.ftag
        results.append(pd.Series(np.where(total > 2.5, "O", "U"), index=info.index)[info.ftr.notna()])
    df = pd.concat(frames, ignore_index=True)
    res = pd.concat(results)

    mv = movement_test(df[["pm_O"]].to_numpy(), df[["pe_O"]].to_numpy(), df[["pc_O"]].to_numpy(),
                       alpha=ALPHA_FAZ10, names=("O",))
    per_league = [_movement_row(f"{lg}", movement_test(g[["pm_O"]].to_numpy(), g[["pe_O"]].to_numpy(),
                                                          g[["pc_O"]].to_numpy(), alpha=ALPHA_FAZ10, names=("O",)))
                  for lg, g in df.groupby("league")]
    sections = [
        f"Maç: {len(df)} (E0 ve B1, 2020/21–2022/23). Aşama 1 – hareket testi (yalnız üst):",
        _md(pd.DataFrame([_movement_row("birleşik (karar)", mv)] + per_league)),
    ]
    if not mv.passes:
        return TestResult("10c", False, f"Geçmedi (aşama 1): hareket eğimi {mv.slope:.4f}, alt sınır "
                          f"{mv.lo_one_sided:.4f}. Aşama 2 çalıştırılmadı.", sections)

    edge_o = df.pm_O * df.o_O - 1.0
    edge_u = df.pm_U * df.o_U - 1.0
    side_o = edge_o >= edge_u
    cand = pd.DataFrame({
        "match_id": df.match_id, "league": df.league, "season": df.season, "decision_date": df.decision_date,
        "outcome": np.where(side_o, "O", "U"), "price": np.where(side_o, df.o_O, df.o_U),
        "p_model": np.where(side_o, df.pm_O, df.pm_U), "p_close": np.where(side_o, df.pc_O, df.pc_U),
        "edge": np.where(side_o, edge_o, edge_u),
    })
    settled = {t: _settle(cand[cand.edge > t], res) for t in engine.THRESHOLDS}
    summaries = {t: engine.summarize(s, alpha=ALPHA_FAZ10) for t, s in settled.items()}
    chosen = engine.choose_threshold(summaries, n_req)
    main = summaries[chosen]
    passed = main.passes(n_req)
    sections += [
        f"Aşama 2 – N = {n_req}:",
        _md(pd.DataFrame([_row(f"eşik {t:g}", s) for t, s in summaries.items()])),
        f"**Seçilen eşik {chosen:g}** (#40).",
        _md(pd.DataFrame([_row("seçilen", main)] + _breakdown(settled[chosen]))),
    ]
    verdict = (f"{'GEÇTİ' if passed else 'Geçmedi'} (aşama 1 geçti, eğim {mv.slope:.4f}): {main.bets} bahis, "
               f"ortalama CLV {main.clv['mean']:.4f}, alt sınır {main.clv['lo_one_sided']:.4f}.")
    return TestResult("10c", passed, verdict, sections)


def _movement_row(label: str, mv: MovementResult) -> dict:
    return {"": label, "maç": mv.matches, "eğim": round(mv.slope, 4),
            f"alt sınır (α={ALPHA_FAZ10:.4f})": round(mv.lo_one_sided, 4),
            "%95 GA": f"{mv.lo:.4f} … {mv.hi:.4f}", "geçti": "evet" if mv.passes else "hayır"}


# ---------------------------------------------------------------- 10d

LEAGUES_10D = ("T1", "F2", "I2", "E2", "E3")


def run_10d(conn: sqlite3.Connection) -> TestResult:
    feas = feasibility_10d(conn)
    n_req = feas.n_required
    frames, results, configs = [], [], []
    for lg in LEAGUES_10D:
        r = faz3_run(conn, lg, use_xg=False)  # karar #33 protokolü, log-loss ile seçim
        final = r["final"]
        configs.append({"lig": lg, "model": final.key(),
                        "Dixon-Coles": "tutuldu" if r["kept"]["Dixon-Coles"] else "elendi",
                        "zaman ağırlığı": "tutuldu" if r["kept"]["Zaman ağırlığı"] else "elendi"})
        preds = r["exp"].predictions(final).set_index("match_id")
        early = _snap(conn, "PS", lg, "early")
        close = _snap(conn, "PS", lg, "closing")
        info = _match_info(conn, lg)
        ids = preds.index.intersection(early.index).intersection(close.index)
        frames.append(pd.DataFrame({
            "match_id": ids, "league": lg, "season": early.loc[ids, "season"].to_numpy(),
            "decision_date": info.loc[ids, "decision_date"].to_numpy(),
            "pm_D": preds.loc[ids, "p_draw"].to_numpy(), "o_D": early.loc[ids, "D"].to_numpy(),
            "pe_D": remove_margin(early.loc[ids, X12])["D"].to_numpy(),
            "pc_D": remove_margin(close.loc[ids, X12])["D"].to_numpy(),
        }))
        results.append(info.ftr)
    df = pd.concat(frames, ignore_index=True)
    res = pd.concat(results)

    mv = movement_test(df[["pm_D"]].to_numpy(), df[["pe_D"]].to_numpy(), df[["pc_D"]].to_numpy(),
                       alpha=ALPHA_FAZ10, names=("X",))
    per_league = [_movement_row(lg, movement_test(g[["pm_D"]].to_numpy(), g[["pe_D"]].to_numpy(),
                                                  g[["pc_D"]].to_numpy(), alpha=ALPHA_FAZ10, names=("X",)))
                  for lg, g in df.groupby("league")]
    sections = [
        "Faz 3 boru hattıyla seçilen modeller (log-loss ile, #33):",
        _md(pd.DataFrame(configs)),
        f"Maç: {len(df)}. Aşama 1 – beraberlik hareket testi:",
        _md(pd.DataFrame([_movement_row("birleşik (karar)", mv)] + per_league)),
    ]
    if not mv.passes:
        return TestResult("10d", False, f"Geçmedi (aşama 1): beraberlik eğimi {mv.slope:.4f}, alt sınır "
                          f"{mv.lo_one_sided:.4f}. Aşama 2 çalıştırılmadı.", sections)

    edge = df.pm_D * df.o_D - 1.0
    cand = pd.DataFrame({"match_id": df.match_id, "league": df.league, "season": df.season,
                         "decision_date": df.decision_date, "outcome": "D", "price": df.o_D,
                         "p_model": df.pm_D, "p_close": df.pc_D, "edge": edge})
    settled = {t: _settle(cand[cand.edge > t], res) for t in engine.THRESHOLDS}
    summaries = {t: engine.summarize(s, alpha=ALPHA_FAZ10) for t, s in settled.items()}
    chosen = engine.choose_threshold(summaries, n_req)
    main = summaries[chosen]
    passed = main.passes(n_req)
    sections += [
        f"Aşama 2 – N = {n_req}:",
        _md(pd.DataFrame([_row(f"eşik {t:g}", s) for t, s in summaries.items()])),
        f"**Seçilen eşik {chosen:g}** (#40).",
        _md(pd.DataFrame([_row("seçilen", main)] + _breakdown(settled[chosen]))),
    ]
    verdict = (f"{'GEÇTİ' if passed else 'Geçmedi'} (aşama 1 geçti, eğim {mv.slope:.4f}): {main.bets} bahis, "
               f"ortalama CLV {main.clv['mean']:.4f}, alt sınır {main.clv['lo_one_sided']:.4f}.")
    return TestResult("10d", passed, verdict, sections)


def render_report(conn: sqlite3.Connection) -> tuple[str, list[TestResult]]:
    _assert_not_run(conn)
    results = [run_10a(conn), run_10c(conn), run_10d(conn)]
    _record_runs(conn, results)
    parts = [
        "# Faz 10 sonuçları",
        f"Oluşturulma: {datetime.now(timezone.utc).isoformat(timespec='seconds')} (UTC). Ön kayıtlar: "
        "`docs/on-kayit/faz10_10a.md` (3a4f8d2), `faz10_10c.md` (03c39d1), `faz10_10d.md` (1ade138). "
        f"Tüm nihai kararlarda tek yönlü α = {ALPHA_FAZ10:.4f} (#72).",
        "## Özet",
        _md(pd.DataFrame([{"test": r.name, "sonuç": r.verdict} for r in results])),
    ]
    titles = {"10a": "10a – Yumuşak şirket fiyatı (modelsiz)", "10c": "10c – 2.5 alt/üst",
              "10d": "10d – Beraberlik çoğaltması"}
    for r in results:
        parts += [f"## {titles[r.name]}", r.verdict, *r.sections]
    return "\n\n".join(parts) + "\n", results
