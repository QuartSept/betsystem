"""Faz 11 penceresi (2025/26–2026/27) kilidi ve 8.5 doluluk ölçümü (karar #81).

Pencere, Faz 10'u geçen her fikir için yalnızca bir kez açılır. Açılış veritabanına kaydedilir; ikinci
açılışı kod reddeder (final_set_runs ile aynı mekanizma). Açılmadan önce pencerede yalnızca oran doluluğu
ölçülebilir: CLV, maç sonucu veya kural çıktısı hesaplanmaz.
"""

import sqlite3
import subprocess
from datetime import datetime, timezone

import pandas as pd

from betsistem.config import FAZ11_WINDOW_SEASONS, PROJECT_ROOT
from betsistem.model.timeline import Faz11Token

CONFIRM_PHRASE = "FAZ 11 PENCERESİNİ AÇ"
COVERAGE_BOOKMAKERS = ("BFE", "Avg", "B365", "PS")


class Faz11AlreadyOpened(Exception):
    pass


def _git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def open_faz11_window(conn: sqlite3.Connection, idea: str, config: str, confirm: str) -> Faz11Token:
    if confirm != CONFIRM_PHRASE:
        raise PermissionError(f"Faz 11 penceresini açmak için onay ifadesi gerekir: {CONFIRM_PHRASE!r}")
    if conn.execute("SELECT 1 FROM faz11_runs WHERE idea = ?", (idea,)).fetchone():
        raise Faz11AlreadyOpened(f"{idea} için Faz 11 penceresi daha önce açıldı; ikinci çalıştırma yapılamaz.")
    with conn:
        conn.execute(
            "INSERT INTO faz11_runs (idea, opened_at, config, git_commit) VALUES (?, ?, ?, ?)",
            (idea, datetime.now(timezone.utc).isoformat(timespec="seconds"), config, _git_commit()),
        )
    return Faz11Token(idea)


def window_coverage(conn: sqlite3.Connection, leagues=None) -> pd.DataFrame:
    """8.5: pencerede lig, sezon, şirket ve zaman başına 1-X-2 oran doluluğu. Yalnızca sayım; sonuç veya
    oran değeri okunmaz."""
    placeholders = ",".join("?" for _ in FAZ11_WINDOW_SEASONS)
    params: list = list(FAZ11_WINDOW_SEASONS)
    league_filter = ""
    if leagues:
        league_filter = f" AND m.league IN ({','.join('?' for _ in leagues)})"
        params += list(leagues)
    totals = pd.read_sql(
        f"SELECT m.league, m.season, COUNT(*) AS matches FROM matches m WHERE m.season IN ({placeholders})"
        f"{league_filter} GROUP BY m.league, m.season", conn, params=params,
    )
    bk = ",".join("?" for _ in COVERAGE_BOOKMAKERS)
    complete = pd.read_sql(
        f"""
        SELECT m.league, m.season, o.bookmaker, o.timing, COUNT(*) AS n FROM (
            SELECT match_id, bookmaker, timing FROM odds
            WHERE market = '1X2' AND bookmaker IN ({bk})
            GROUP BY match_id, bookmaker, timing HAVING COUNT(DISTINCT outcome) = 3) o
        JOIN matches m ON m.id = o.match_id
        WHERE m.season IN ({placeholders}){league_filter}
        GROUP BY m.league, m.season, o.bookmaker, o.timing
        """,
        conn, params=[*COVERAGE_BOOKMAKERS, *params],
    )
    df = complete.merge(totals, on=["league", "season"])
    df["doluluk"] = (df.n / df.matches).round(3)
    wide = df.pivot_table(index=["league", "season", "matches"], columns=["bookmaker", "timing"], values="doluluk")
    wide.columns = [f"{b} {t}" for b, t in wide.columns]
    return wide.reset_index().fillna(0.0)


# ---------------------------------------------------------------- 10a ön fizibilite (#85, #86, #89)

WINDOW_END = "2026-12-31"  # karar #65
K_10A = 0.0  # karar #83, #84: kural aynen


def _complete_ids(conn, bookmaker: str, timing: str, leagues) -> set[int]:
    """Doluluk: üç sonucu da bulunan maçlar (yalnızca varlık; değer okunmaz)."""
    ph = ",".join("?" for _ in leagues)
    rows = conn.execute(
        f"""SELECT o.match_id FROM odds o JOIN matches m ON m.id = o.match_id
            WHERE o.market = '1X2' AND o.bookmaker = ? AND o.timing = ? AND m.league IN ({ph})
            GROUP BY o.match_id HAVING COUNT(DISTINCT o.outcome) = 3""",
        (bookmaker, timing, *leagues),
    ).fetchall()
    return {r[0] for r in rows}


def window_matches(conn, leagues) -> pd.DataFrame:
    ph = ",".join("?" for _ in leagues)
    sp = ",".join("?" for _ in FAZ11_WINDOW_SEASONS)
    return pd.read_sql(
        f"SELECT id AS match_id, league, season, match_date FROM matches"
        f" WHERE league IN ({ph}) AND season IN ({sp}) AND match_date <= ?",
        conn, params=(*leagues, *FAZ11_WINDOW_SEASONS, WINDOW_END),
    )


def eligible_leagues_86(conn, threshold: float = 0.90) -> pd.DataFrame:
    """#86: pencerede B365 erken, Avg erken ve BFE kapanış doluluğu (iki sezon birlikte) ≥ %90 olan ligler."""
    leagues = [r[0] for r in conn.execute(
        f"SELECT DISTINCT league FROM matches WHERE season IN ({','.join('?' for _ in FAZ11_WINDOW_SEASONS)})",
        FAZ11_WINDOW_SEASONS)]
    wm = window_matches(conn, leagues)
    cov = {name: _complete_ids(conn, bk, t, leagues)
           for name, bk, t in (("B365 erken", "B365", "early"), ("Avg erken", "Avg", "early"),
                               ("BFE kapanış", "BFE", "closing"))}
    rows = []
    for lg, g in wm.groupby("league"):
        ids = set(g.match_id)
        row = {"lig": lg, "maç": len(ids)}
        for name, s in cov.items():
            row[name] = round(len(ids & s) / len(ids), 3)
        row["uygun"] = all(row[name] >= threshold for name in cov)
        rows.append(row)
    return pd.DataFrame(rows).sort_values("lig").reset_index(drop=True)


def window_bet_counts_10a(conn, leagues, reference: dict[str, str] | None = None) -> pd.DataFrame:
    """#85: pencerede 10a kuralının (k = 0) üreteceği bahis SAYISI; yalnızca erken fiyatlar.

    Oranlar ve kural çıktıları dışarı verilmez; yalnızca lig/sezon başına sayılar döner. Kapanış oranı
    yalnızca varlık olarak (doluluk) sayılır. Faz 11 izni gerektirmez ve izni tüketmez.
    """
    from betsistem.model.market import market_prices, remove_margin

    wm = window_matches(conn, leagues).set_index("match_id")
    reference = reference or {lg: "BFE" for lg in leagues}
    ref_close = {bk: _complete_ids(conn, bk, "closing", leagues) for bk in set(reference.values())}
    rows = []
    for lg in leagues:
        try:
            b = market_prices(conn, "B365", lg).xs("early", level="timing").reset_index(level="season", drop=True)
            a = market_prices(conn, "Avg", lg).xs("early", level="timing").reset_index(level="season", drop=True)
        except KeyError:
            continue
        lg_ids = wm.index[wm.league == lg]
        ids = lg_ids.intersection(b.index).intersection(a.index)
        cols = ["H", "D", "A"]
        bet = (b.loc[ids, cols].to_numpy() * remove_margin(a.loc[ids])[cols].to_numpy()).max(axis=1) > 1 + K_10A
        bet_ids = set(ids[bet])
        for season, g in wm.loc[lg_ids].groupby("season"):
            sids = set(g.index)
            rows.append({"lig": lg, "sezon": season, "pencere maçı": len(sids),
                         "B365+Avg erken dolu": len(sids & set(ids)),
                         "bahis (k=0)": len(sids & bet_ids),
                         "referans": reference[lg],
                         "bahis, ref. kapanış dolu": len(sids & bet_ids & ref_close[reference[lg]])})
    return pd.DataFrame(rows)


def projected_window_matches(conn, league: str) -> int:
    """2026/27'nin 31 Aralık'a kadarki maç sayısı tahmini: 2025/26'nın aynı tarihe kadarki payı × sezon büyüklüğü."""
    r = conn.execute(
        "SELECT COUNT(*), SUM(match_date <= '2025-12-31') FROM matches WHERE league = ? AND season = '2526'", (league,)
    ).fetchone()
    return int(round(r[1])) if r and r[0] else 0


def _projected_bets(counts: pd.DataFrame, conn) -> tuple[int, int]:
    """(gözlenen, 31 Aralık 2026'ya projeksiyon) — referans kapanışı dolu bahis sayısı."""
    observed = int(counts["bahis, ref. kapanış dolu"].sum())
    projected = observed
    for lg, g in counts.groupby("lig"):
        cur = g[g.sezon == "2627"]
        prev = g[g.sezon == "2526"]
        if cur.empty or prev.empty or prev["pencere maçı"].iloc[0] == 0:
            continue
        rate = prev["bahis, ref. kapanış dolu"].iloc[0] / prev["pencere maçı"].iloc[0]
        remaining = max(projected_window_matches(conn, lg) - int(cur["pencere maçı"].iloc[0]), 0)
        projected += int(round(rate * remaining))
    return observed, projected


def render_preliminary_feasibility(conn) -> str:
    """#86 sırasıyla ön fizibilite. N, #89 önerisiyle (seçim dönemi σ, α = 0,05)."""
    from betsistem.asama2.feasibility import MODELLESS_SEASONS, feasibility_10a
    from betsistem.report import markdown_table as _md

    elig = eligible_leagues_86(conn)

    bfe_ok = set(elig.loc[elig["BFE kapanış"] >= 0.90, "lig"])

    def counts_with_reference(leagues):
        # Referans: ligde BFE kapanış doluluğu ≥ %90 ise BFE, değilse Avg kapanış (v2 Faz 11 tablosu)
        return window_bet_counts_10a(conn, leagues, {lg: "BFE" if lg in bfe_ok else "Avg" for lg in leagues})

    parts = ["# Faz 11 ön fizibilite: 10a (karar #85, #86, #89)",
             f"Oluşturulma: {datetime.now(timezone.utc).isoformat(timespec='seconds')} (UTC). Pencerede yalnızca erken "
             "fiyatlarla bahis sayısı sayıldı; oran değerleri, kapanış değerleri, sonuçlar ve CLV kullanılmadı. "
             "N, #89 önerisiyle (seçim dönemi σ, α = 0,05) hesaplandı; #89 onaylanmazsa bu sayfa geçersizdir.",
             "## Pencerede lig uygunluğu (#86, yalnızca doluluk)",
             _md(elig)]

    steps = [("Adım 1: E0 + T1", ("E0", "T1"))]
    fallback = tuple(elig.loc[elig.uygun, "lig"])
    steps.append((f"Adım 2: uygun tüm ligler ({len(fallback)})", fallback))
    verdict = None
    for title, leagues in steps:
        if not leagues:
            parts += [f"## {title}", "_Uygun lig yok._"]
            continue
        feas = feasibility_10a(conn, leagues, MODELLESS_SEASONS, alpha=0.05)
        counts = counts_with_reference(leagues)
        observed, projected = _projected_bets(counts, conn)
        ok = projected >= feas.n_required
        parts += [
            f"## {title}",
            f"σ (seçim dönemi, {feas.matches} maç) = {feas.sigma:.4f} → **N = {feas.n_required}** (α = 0,05)."
            + ("".join(f"\n- {n}" for n in feas.notes)),
            _md(counts),
            f"Referans kapanışı dolu bahis: şimdiye kadar **{observed}**, 31 Aralık 2026'ya projeksiyon **{projected}** "
            f"→ {'N’ye ulaşıyor' if ok else 'N’ye ulaşmıyor'}.",
        ]
        if ok:
            verdict = f"Ön sonuç: test kapsamı **{title}**. Kesin karar pencere verisi tamamlanınca (Ocak 2027) aynı sayımla verilir."
            break
    if verdict is None:
        verdict = "Ön sonuç: iki adımda da N'ye ulaşılmıyor; pencere tamamlanınca da ulaşılamazsa 10a 'yetersiz güç' olarak kapanır (#86)."
    parts += ["## Sonuç", verdict]
    return "\n\n".join(parts) + "\n"
