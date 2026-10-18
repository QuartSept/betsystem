"""Faz 4 çalıştırıcıları: model seçimi döneminde eşik seçimi ve kilitli final setinin tek seferlik testi."""

import json
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from betsistem.backtest import engine
from betsistem.config import (
    BET_PRICE_BOOKMAKER,
    FINAL_TEST_SEASONS,
    N_TARGETS,
    PROJECT_ROOT,
    SENSITIVITY_BOOKMAKERS,
    season_label,
)
from betsistem.model.experiments import CHECK_SEASONS, LEAGUE_MODELS, TUNING_SEASONS  # noqa: F401 (CLI)
from betsistem.model.market import market_prices, remove_margin
from betsistem.model.predict import ModelConfig, load_matches, walk_forward
from betsistem.model.timeline import FinalSetToken
from betsistem.report import markdown_table as _md

SELECTION_SEASONS = TUNING_SEASONS + CHECK_SEASONS  # 2019/20 ısınma (karar #32)
REPORTS = PROJECT_ROOT / "reports"


def selection_file(league: str) -> Path:
    return REPORTS / ("faz4_secim.json" if league == "E0" else f"faz4_secim_{league}.json")


SELECTION_FILE = selection_file("E0")
CONFIRM_PHRASE = "FINAL SETİ AÇ"


class FinalSetAlreadyOpened(Exception):
    pass


def _prices(conn, bookmaker: str, timing: str, league: str) -> pd.DataFrame:
    p = market_prices(conn, bookmaker, league)
    return p[p.index.get_level_values("timing") == timing].reset_index()[["match_id", "H", "D", "A"]]


def _fair(conn, bookmaker: str, timing: str, league: str) -> pd.DataFrame:
    p = market_prices(conn, bookmaker, league)
    p = p[p.index.get_level_values("timing") == timing]
    return remove_margin(p).reset_index()[["match_id", "H", "D", "A"]]


def _predictions(conn, league, seasons, config: ModelConfig, token=None) -> tuple[pd.DataFrame, pd.Series]:
    matches = load_matches(conn, league)
    preds = walk_forward(matches, seasons, config, final_set_token=token)
    info = matches.set_index("match_id")
    preds = preds.join(info[["season", "match_date"]], on="match_id")
    return preds, info["ftr"]


def _run_rule(conn, league, preds, results, bookmaker: str, threshold: float) -> pd.DataFrame:
    bets = engine.select_bets(preds, _prices(conn, bookmaker, "early", league), threshold)
    return engine.settle(bets, results, _fair(conn, bookmaker, "closing", league))


def _summary_row(label: str, s: engine.Summary) -> dict:
    return {
        "": label,
        "bahis": s.bets,
        "ort. CLV": round(s.clv["mean"], 4),
        "CLV alt (tek yönlü %95)": round(s.clv["lo_one_sided"], 4),
        "CLV %95 GA": f"{s.clv['lo']:.4f} … {s.clv['hi']:.4f}",
        "ROI": round(s.roi["mean"], 4),
        "ROI %95 GA": f"{s.roi['lo']:.4f} … {s.roi['hi']:.4f}",
        "en büyük düşüş (birim)": round(s.max_drawdown, 1),
        "¼ Kelly kasa (100'den)": round(s.kelly_final, 1),
        "¼ Kelly en büyük düşüş": f"{s.kelly_max_drawdown_pct:.1%}",
    }


def _season_rows(settled: pd.DataFrame) -> list[dict]:
    return [_summary_row(season_label(season), engine.summarize(g)) for season, g in settled.groupby("season")]


def _git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def selection_report(conn: sqlite3.Connection, league: str = "E0", out_file: Path | None = None) -> str:
    config = LEAGUE_MODELS[league]
    n_required = N_TARGETS[league]
    out_file = out_file or selection_file(league)
    preds, results = _predictions(conn, league, SELECTION_SEASONS, config)

    settled = {t: _run_rule(conn, league, preds, results, BET_PRICE_BOOKMAKER, t) for t in engine.THRESHOLDS}
    summaries = {t: engine.summarize(s) for t, s in settled.items()}
    chosen = engine.choose_threshold(summaries, n_required)
    main = summaries[chosen]

    grid = pd.DataFrame([_summary_row(f"eşik {t:g}", s) for t, s in summaries.items()])
    sens = []
    for bk in SENSITIVITY_BOOKMAKERS:
        s_bk = engine.summarize(_run_rule(conn, league, preds, results, bk, chosen))
        sens.append(_summary_row(f"{bk} erken, eşik {chosen:g}", s_bk))

    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps({
        "league": league,
        "config": config.key(),
        "threshold": chosen,
        "n_required": n_required,
        "selected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    passed = main.passes(n_required)
    parts = [
        f"# Faz 4: model seçimi döneminde geriye dönük test ({league})",
        f"Oluşturulma: {datetime.now(timezone.utc).isoformat(timespec='seconds')} (UTC).",
        "## Kurallar (ön kayıt: karar #38–#42)",
        "\n".join([
            f"- Lig: {league}. Model: `{config.key()}` (karar #35 / #50), walk-forward, karar günü Cuma/Salı.",
            f"- Dönem: {', '.join(season_label(s) for s in SELECTION_SEASONS)} (2019/20 ısınma).",
            "- Maç başına değeri en yüksek tek sonuç; değer = model olasılığı × Pinnacle erken oranı − 1.",
            "- CLV = bahis oranı × marjsız Pinnacle kapanış olasılığı − 1. ROI sabit 1 birimle.",
            f"- Eşik seçimi: en az {n_required} bahis verenler arasında ortalama CLV'si en yüksek eşik.",
        ]),
        "## Eşik ızgarası",
        _md(grid),
        f"## Seçilen eşik: {chosen:g}",
        _md(pd.DataFrame([_summary_row("tüm dönem", main)] + _season_rows(settled[chosen]))),
        "## Duyarlılık: B365 erken oranı (karar #25)",
        "Aynı model ve eşik; bahis B365 erken oranıyla seçilir, CLV B365 kapanışına göre hesaplanır.",
        _md(pd.DataFrame(sens)),
        "## Geçme şartı (karar #42), seçim dönemi",
        f"En az {n_required} bahis, ortalama CLV > 0, tek yönlü %95 alt sınır > 0: **{'sağlandı' if passed else 'sağlanmadı'}** "
        f"({main.bets} bahis, ortalama CLV {main.clv['mean']:.4f}, alt sınır {main.clv['lo_one_sided']:.4f}).",
        "Kâr var ama CLV negatifse sonuç büyük ihtimalle şanstır.",
    ]
    return "\n\n".join(parts) + "\n"


def open_final_set(
    conn: sqlite3.Connection, league: str, config_key: str, threshold: float, confirm: str
) -> FinalSetToken:
    """Ligin final setini açar ve açılışı kalıcı olarak kaydeder. İkinci açılış reddedilir (karar #42)."""
    if confirm != CONFIRM_PHRASE:
        raise PermissionError(f"Final setini açmak için onay ifadesi gerekir: {CONFIRM_PHRASE!r}")
    if conn.execute("SELECT 1 FROM final_set_runs WHERE league = ?", (league,)).fetchone():
        raise FinalSetAlreadyOpened(f"{league} kilitli final seti daha önce açıldı; ikinci çalıştırma yapılamaz.")
    with conn:
        conn.execute(
            "INSERT INTO final_set_runs (league, opened_at, config, threshold, git_commit) VALUES (?, ?, ?, ?, ?)",
            (league, datetime.now(timezone.utc).isoformat(timespec="seconds"), config_key, threshold, _git_commit()),
        )
    return FinalSetToken(run_id=league)


def final_report(conn: sqlite3.Connection, league: str, confirm: str) -> str:
    selection = json.loads(selection_file(league).read_text(encoding="utf-8"))
    config = ModelConfig(**json.loads(selection["config"]))
    threshold = float(selection["threshold"])
    n_required = int(selection["n_required"])
    token = open_final_set(conn, league, config.key(), threshold, confirm)

    preds, results = _predictions(conn, league, FINAL_TEST_SEASONS, config, token)
    settled = _run_rule(conn, league, preds, results, BET_PRICE_BOOKMAKER, threshold)
    main = engine.summarize(settled)
    sens = [_summary_row(f"{bk} erken", engine.summarize(_run_rule(conn, league, preds, results, bk, threshold)))
            for bk in SENSITIVITY_BOOKMAKERS]
    passed = main.passes(n_required)

    with conn:
        conn.execute(
            "UPDATE final_set_runs SET result_json = ? WHERE league = ?",
            (json.dumps({"passed": passed, "bets": main.bets, "clv": main.clv, "roi": main.roi}), league),
        )

    parts = [
        f"# Faz 4: kilitli final set (tek seferlik, {league})",
        f"Çalıştırma: {datetime.now(timezone.utc).isoformat(timespec='seconds')} (UTC). Ayar değiştirilmedi.",
        f"- Model: `{config.key()}`, eşik {threshold:g} (seçim: {selection['selected_at']}).",
        f"- Dönem: {', '.join(season_label(s) for s in FINAL_TEST_SEASONS)}.",
        "## Sonuç",
        _md(pd.DataFrame([_summary_row("final set", main)] + _season_rows(settled))),
        "## Duyarlılık: B365 erken",
        _md(pd.DataFrame(sens)),
        "## Geçme şartı (karar #42), final set",
        f"**{'Sağlandı' if passed else 'Sağlanmadı'}** (en az {n_required} bahis gerekir; {main.bets} bahis, "
        f"ortalama CLV {main.clv['mean']:.4f}, alt sınır {main.clv['lo_one_sided']:.4f}).",
    ]
    return "\n\n".join(parts) + "\n"
