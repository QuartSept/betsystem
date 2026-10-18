"""Faz 3 deneyleri: Dixon-Coles, zaman ağırlığı ve xG'nin katkısı ayrı ayrı ölçülür.

Protokol (karar #33): yalnızca model seçimi dönemi kullanılır. Ayarlar (ξ, xG payı) ayar sezonlarında
(2020/21–2021/22) seçilir; 2022/23 iç kontrol olarak yalnızca raporlanır, seçimde kullanılmaz.
2019/20 ısınma sezonudur (karar #32): eğitimde kullanılır, değerlendirilmez.
"""

import sqlite3
from dataclasses import replace
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from betsistem.config import season_label
from betsistem.model import metrics
from betsistem.model.evaluation import COLS, _market
from betsistem.model.predict import ModelConfig, load_matches, promoted_flags, save_predictions, walk_forward
from betsistem.model.timeline import assert_unlocked
from betsistem.report import markdown_table as _md

TUNING_SEASONS = ("2021", "2122")
CHECK_SEASONS = ("2223",)
EVAL_SEASONS = TUNING_SEASONS + CHECK_SEASONS

LONG_WINDOW = 3650  # zaman ağırlığı varken tüm geçmiş kullanılır, ağırlık eskiyi söndürür
XI_GRID = (0.0, 0.0005, 0.001, 0.0019, 0.003, 0.005)  # gün başına; 0.0019 ≈ 1 yıllık yarı ömür
XG_GRID = (0.25, 0.5, 0.75, 1.0)


class Experiment:
    def __init__(self, conn: sqlite3.Connection):
        assert_unlocked(EVAL_SEASONS)
        self.conn = conn
        self.matches = load_matches(conn)
        self.results = self.matches.set_index("match_id")
        self._cache: dict[str, pd.DataFrame] = {}

    def predictions(self, config: ModelConfig) -> pd.DataFrame:
        key = config.key()
        if key not in self._cache:
            preds = walk_forward(self.matches, EVAL_SEASONS, config)
            preds = preds.join(self.results[["season", "ftr"]], on="match_id").sort_values("match_id")
            self._cache[key] = preds.reset_index(drop=True)
        return self._cache[key]

    def log_loss(self, config: ModelConfig, seasons) -> np.ndarray:
        p = self.predictions(config)
        p = p[p.season.isin(seasons)]
        return metrics.log_loss_per_match(p[COLS].to_numpy(), p.ftr)

    def tune(self, configs) -> tuple[ModelConfig, pd.DataFrame]:
        rows = []
        for cfg in configs:
            rows.append({"config": cfg, "ayar log-loss": self.log_loss(cfg, TUNING_SEASONS).mean(),
                         "iç kontrol log-loss": self.log_loss(cfg, CHECK_SEASONS).mean()})
        table = pd.DataFrame(rows)
        best = table.loc[table["ayar log-loss"].idxmin(), "config"]
        return best, table


def _diff_row(exp: Experiment, name: str, new: ModelConfig, old: ModelConfig) -> dict:
    row = {"değişiklik": name}
    for label, seasons in (("ayar", TUNING_SEASONS), ("iç kontrol", CHECK_SEASONS)):
        diff = exp.log_loss(new, seasons) - exp.log_loss(old, seasons)
        mean, lo, hi = metrics.paired_bootstrap(diff)
        row[f"{label}: fark"] = round(mean, 4)
        row[f"{label}: %95 GA"] = f"{lo:.4f} … {hi:.4f}"
    return row


def run(conn: sqlite3.Connection) -> dict:
    exp = Experiment(conn)
    base = ModelConfig()

    # Her adımda önceki model de adaydır: iyileştirmeyen değişiklik ayar sezonlarında elenir.
    dc_candidate = replace(base, dixon_coles=True)
    after_dc, _ = exp.tune([base, dc_candidate])
    best_time, time_table = exp.tune(
        [replace(after_dc, window_days=LONG_WINDOW, xi=xi) for xi in XI_GRID] + [after_dc]
    )
    best_xg, xg_table = exp.tune([replace(best_time, xg_weight=a) for a in XG_GRID] + [best_time])

    cumulative = [
        ("Dixon-Coles", dc_candidate, base),
        (f"Zaman ağırlığı (ξ={best_time.xi})", replace(after_dc, window_days=LONG_WINDOW, xi=best_time.xi), after_dc),
        (f"xG (pay={best_xg.xg_weight})", replace(best_time, xg_weight=best_xg.xg_weight or XG_GRID[-1]), best_time),
    ]
    alone = [
        ("Yalnız Dixon-Coles", dc_candidate),
        ("Yalnız zaman ağırlığı", replace(base, window_days=LONG_WINDOW, xi=best_time.xi)),
        ("Yalnız xG", replace(base, xg_weight=best_xg.xg_weight or XG_GRID[-1])),
    ]
    kept = {
        "Dixon-Coles": after_dc.dixon_coles,
        "Zaman ağırlığı": best_time != after_dc,
        "xG": best_xg != best_time,
    }
    return {
        "exp": exp,
        "base": base,
        "final": best_xg,
        "time_table": time_table,
        "xg_table": xg_table,
        "cumulative": pd.DataFrame([_diff_row(exp, n, new, old) for n, new, old in cumulative]),
        "alone": pd.DataFrame([_diff_row(exp, n, cfg, base) for n, cfg in alone]),
        "kept": kept,
    }


def _grid_md(table: pd.DataFrame, field: str) -> str:
    t = table.assign(**{field: table.config.map(lambda c: getattr(c, field))})
    t = t[[field, "ayar log-loss", "iç kontrol log-loss"]].round(4).drop_duplicates(subset=[field])
    return _md(t.sort_values(field))


def _vs_market(exp: Experiment, configs: dict[str, ModelConfig]) -> tuple[pd.DataFrame, pd.DataFrame]:
    markets = {"Piyasa: PS erken": _market(exp.conn, "PS", "early"),
               "Piyasa: PS kapanış": _market(exp.conn, "PS", "closing")}
    ids = exp.predictions(next(iter(configs.values()))).match_id
    for m in markets.values():
        ids = ids[ids.isin(m.match_id)]
    ftr = exp.results.loc[ids, "ftr"]
    season = exp.results.loc[ids, "season"]

    probs = {name: exp.predictions(cfg).set_index("match_id").loc[ids, COLS].to_numpy() for name, cfg in configs.items()}
    probs |= {name: m.set_index("match_id").loc[ids, COLS].to_numpy() for name, m in markets.items()}

    rows = []
    for name, p in probs.items():
        row = {"tahmin": name}
        for label, seasons in (("ayar", TUNING_SEASONS), ("iç kontrol", CHECK_SEASONS)):
            mask = season.isin(seasons).to_numpy()
            row[f"{label} log-loss"] = round(metrics.log_loss_per_match(p[mask], ftr[mask]).mean(), 4)
        row["Brier"] = round(metrics.brier_per_match(p, ftr).mean(), 4)
        row["ECE"] = round(metrics.expected_calibration_error(p, ftr), 4)
        rows.append(row)

    final_name = list(configs)[-1]
    gaps = []
    for name in markets:
        diff = metrics.log_loss_per_match(probs[final_name], ftr) - metrics.log_loss_per_match(probs[name], ftr)
        mean, lo, hi = metrics.paired_bootstrap(diff)
        gaps.append({"karşılaştırma": f"{final_name} − {name}", "fark": round(mean, 4),
                     "%95 GA": f"{lo:.4f} … {hi:.4f}"})
    return pd.DataFrame(rows), pd.DataFrame(gaps)


def render_report(conn: sqlite3.Connection) -> str:
    r = run(conn)
    exp, base, final = r["exp"], r["base"], r["final"]
    save_predictions(conn, "poisson", final.key(), exp.predictions(final))

    summary, gaps = _vs_market(exp, {"Faz 2 Poisson": base, "Faz 3 model": final})
    fp = exp.predictions(final)
    calib = metrics.calibration_table(fp[COLS].to_numpy(), fp.ftr)
    calib = calib[calib.n >= 20]
    rho = fp.rho.describe()

    parts = [
        "# Faz 3: gelişmiş model",
        f"Oluşturulma: {datetime.now(timezone.utc).isoformat(timespec='seconds')} (UTC).",
        "## Protokol",
        "\n".join([
            f"- Ayar sezonları: {', '.join(season_label(s) for s in TUNING_SEASONS)}. Ayarlar yalnızca burada seçildi.",
            f"- İç kontrol: {', '.join(season_label(s) for s in CHECK_SEASONS)}. Seçimde kullanılmadı, yalnızca raporlandı.",
            "- 2019/20 ısınma sezonu; kilitli final sezonları (2023/24–2024/25) kullanılmadı.",
            "- Değişiklikler sırayla eklendi: Dixon-Coles → zaman ağırlığı → xG. Her adımın katkısı bir önceki "
            "modele göre ve ayrıca yalnız başına temel modele eklendiğinde ölçüldü.",
            f"- Seçilen model: `{final.key()}`.",
            "- Ayar sezonlarında iyileştirme getirmeyen değişiklik elenir. Karar: "
            + ", ".join(f"{k} {'tutuldu' if v else 'elendi'}" for k, v in r["kept"].items()) + ".",
        ]),
        "## Adım adım katkı (log-loss farkı, negatif = iyileşme)",
        _md(r["cumulative"]),
        "## Yalnız başına katkı (temel Poisson'a eklendiğinde)",
        _md(r["alone"]),
        "## Zaman ağırlığı ızgarası (Dixon-Coles açık, tüm geçmiş)",
        "ξ gün başına; yarı ömür = ln 2 / ξ gün. ξ = 0 ağırlıksız tüm geçmiş demektir.",
        _grid_md(r["time_table"], "xi"),
        "## xG payı ızgarası (seçilen ξ ile)",
        "Hedef = (1 − pay)·gol + pay·xG.",
        _grid_md(r["xg_table"], "xg_weight"),
        "## Piyasa ile karşılaştırma",
        _md(summary),
        _md(gaps),
        "## Faz 3 modelinin kalibrasyonu",
        (f"Dixon-Coles ρ: ortalama {rho['mean']:.3f}, aralık {rho['min']:.3f} … {rho['max']:.3f}."
         if final.dixon_coles else "Dixon-Coles elendiği için seçilen modelde ρ = 0."),
        _md(calib),
    ]
    return "\n\n".join(parts) + "\n"


# Karar #35: Faz 3'te seçilen model.
FAZ3_MODEL = ModelConfig(window_days=LONG_WINDOW, xi=0.001, xg_weight=0.5)


def render_promoted_report(conn: sqlite3.Connection) -> str:
    """Karar #36: yeni çıkan takım ayarının Faz 3 protokolüyle (karar #33) değerlendirilmesi."""
    exp = Experiment(conn)
    base = FAZ3_MODEL
    candidate = replace(base, promoted_effect=True)
    kept_cfg, _ = exp.tune([base, candidate])
    kept = kept_cfg == candidate

    rows = [_diff_row(exp, "Yeni çıkan takım ayarı (tüm maçlar)", candidate, base)]

    # Tanı: yalnızca yeni çıkan takımın oynadığı maçlar (bahis alt grubu değildir).
    flags = exp.matches.join(promoted_flags(exp.matches)).set_index("match_id")
    involved = set(flags.index[flags.home_promoted | flags.away_promoted])
    diag = {"değişiklik": "Tanı: yeni çıkan takımın oynadığı maçlar"}
    for label, seasons in (("ayar", TUNING_SEASONS), ("iç kontrol", CHECK_SEASONS)):
        p_new, p_old = exp.predictions(candidate), exp.predictions(base)
        mask = (p_new.season.isin(seasons) & p_new.match_id.isin(involved)).to_numpy()
        diff = (metrics.log_loss_per_match(p_new.loc[mask, COLS].to_numpy(), p_new.ftr[mask])
                - metrics.log_loss_per_match(p_old.loc[mask, COLS].to_numpy(), p_old.ftr[mask]))
        mean, lo, hi = metrics.paired_bootstrap(diff)
        diag[f"{label}: fark"] = round(mean, 4)
        diag[f"{label}: %95 GA"] = f"{lo:.4f} … {hi:.4f} (n={int(mask.sum())})"
    rows.append(diag)

    shifts = (exp.predictions(candidate).groupby("season")[["promoted_attack", "promoted_defence"]].mean()
              .round(3).reset_index())
    shifts["season"] = shifts.season.map(season_label)

    final = candidate if kept else base
    save_predictions(conn, "poisson", final.key(), exp.predictions(final))
    summary, gaps = _vs_market(exp, {"Faz 3 model": base, "Faz 3 + yeni çıkan": candidate})

    parts = [
        "# Yeni çıkan takım ayarı (karar #36)",
        f"Oluşturulma: {datetime.now(timezone.utc).isoformat(timespec='seconds')} (UTC).",
        "## Tanım (ön kayıt, sonuçlardan önce commit edildi)",
        "\n".join([
            "- Bir takım, bir önceki sezon veride Premier League'de yoksa o sezon boyunca yeni çıkan sayılır.",
            "- Modele yeni çıkan takımın hücumuna ve savunmasına iki sabit kayma eklenir; cezasızdır ve eğitim "
            "penceresindeki yeni çıkan takımlardan öğrenilir. Elle seçilen sayı veya ızgara yoktur.",
            f"- Temel: Faz 3 modeli `{base.key()}`. Ayar sezonlarında log-loss düşmezse elenir (karar #33).",
            f"- Karar: **{'tutuldu' if kept else 'elendi'}**.",
        ]),
        "## Katkı (log-loss farkı, negatif = iyileşme)",
        _md(pd.DataFrame(rows)),
        "## Öğrenilen kaymalar (sezon içi karar günlerinin ortalaması)",
        "Negatif hücum kayması daha az gol atmak, negatif savunma kayması daha çok gol yemek demektir. "
        "2020/21'in başında eğitim verisinde yeni çıkan takım bulunmadığı için kayma sıfırdan başlar "
        "(2019/20 ilk sezon, öncesi veride yok).",
        _md(shifts),
        "## Piyasa ile karşılaştırma",
        _md(summary),
        _md(gaps),
    ]
    return "\n\n".join(parts) + "\n"

