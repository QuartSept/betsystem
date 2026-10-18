"""Faz 2 ölçümü: modeli marjsız piyasa olasılıklarıyla aynı maçlarda karşılaştırır.

Yalnızca model seçimi dönemi kullanılır (kilitli final sezonlarına dokunulmaz).
"""

import sqlite3
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from betsistem.config import BET_PRICE_BOOKMAKER, MODEL_SELECTION_SEASONS, season_label
from betsistem.model import metrics
from betsistem.model.market import market_prices, remove_margin
from betsistem.model.predict import ModelConfig, load_matches, save_predictions, walk_forward
from betsistem.model.timeline import assert_unlocked
from betsistem.report import markdown_table as _md

# Değerlendirmeye alınacak maçta modelin en az bu kadar eğitim maçı görmüş olması gerekir (~1 sezon).
MIN_TRAIN_MATCHES = 380
COLS = ["p_home", "p_draw", "p_away"]

# (ad, şirket kodu, zaman)
MARKET_BENCHMARKS = [
    ("Piyasa: PS erken", BET_PRICE_BOOKMAKER, "early"),
    ("Piyasa: PS kapanış", BET_PRICE_BOOKMAKER, "closing"),
    ("Piyasa: B365 erken", "B365", "early"),
    ("Piyasa: Avg erken", "Avg", "early"),
]
MODEL_NAME = "Poisson"


def _market(conn, bookmaker: str, timing: str) -> pd.DataFrame:
    prices = market_prices(conn, bookmaker)
    prices = prices[prices.index.get_level_values("timing") == timing]
    fair = remove_margin(prices).reset_index()
    return fair.rename(columns={"H": "p_home", "D": "p_draw", "A": "p_away"})[["match_id", *COLS]]


def _base_rates(matches: pd.DataFrame, preds: pd.DataFrame) -> pd.DataFrame:
    """Kıyas için en basit tahmin: karar gününe kadar oynanmış maçlardaki 1-X-2 sıklıkları."""
    played = matches.dropna(subset=["ftr"]).sort_values("match_date")
    rows = []
    for dd, group in preds.groupby("decision_date"):
        past = played[played.match_date < pd.Timestamp(dd).date()]
        freq = past.ftr.value_counts(normalize=True)
        for mid in group.match_id:
            rows.append({"match_id": mid, "p_home": freq.get("H", 1 / 3), "p_draw": freq.get("D", 1 / 3),
                         "p_away": freq.get("A", 1 / 3)})
    return pd.DataFrame(rows)


def build_evaluation(conn: sqlite3.Connection, seasons=MODEL_SELECTION_SEASONS, config=ModelConfig()):
    assert_unlocked(seasons)
    matches = load_matches(conn)
    preds = walk_forward(matches, seasons, config)
    save_predictions(conn, "poisson", config.key(), preds)

    eligible = preds[preds.train_matches >= MIN_TRAIN_MATCHES]
    base = matches[["match_id", "season", "ftr"]].merge(eligible[["match_id", "decision_date"]], on="match_id")
    base = base.dropna(subset=["ftr"])

    predictors = {MODEL_NAME: eligible[["match_id", *COLS]]}
    for name, bk, timing in MARKET_BENCHMARKS:
        predictors[name] = _market(conn, bk, timing)
    predictors["Geçmiş sıklık"] = _base_rates(matches, eligible)

    # Ortak maç kümesi: her tahmin edicinin olasılığı olan maçlar.
    common = set(base.match_id)
    for p in predictors.values():
        common &= set(p.match_id)
    base = base[base.match_id.isin(common)].sort_values("match_id").reset_index(drop=True)
    aligned = {
        name: p.set_index("match_id").loc[base.match_id, COLS].to_numpy() for name, p in predictors.items()
    }
    return base, aligned, len(preds), len(eligible)


def _summary(base, aligned) -> pd.DataFrame:
    rows = []
    draw_rate = (base.ftr == "D").mean()
    for name, probs in aligned.items():
        rows.append({
            "tahmin": name,
            "maç": len(base),
            "log-loss": round(metrics.log_loss_per_match(probs, base.ftr).mean(), 4),
            "Brier": round(metrics.brier_per_match(probs, base.ftr).mean(), 4),
            "ECE": round(metrics.expected_calibration_error(probs, base.ftr), 4),
            "ort. P(X)": round(float(probs[:, 1].mean()), 4),
            "gerçek X": round(float(draw_rate), 4),
        })
    return pd.DataFrame(rows)


def _by_season(base, aligned) -> pd.DataFrame:
    rows = []
    for season, idx in base.groupby("season").groups.items():
        row = {"sezon": season_label(season), "maç": len(idx)}
        for name, probs in aligned.items():
            row[name] = round(metrics.log_loss_per_match(probs[idx], base.ftr[idx]).mean(), 4)
        rows.append(row)
    return pd.DataFrame(rows)


def _paired(base, aligned) -> pd.DataFrame:
    model_ll = metrics.log_loss_per_match(aligned[MODEL_NAME], base.ftr)
    rows = []
    for name, probs in aligned.items():
        if name == MODEL_NAME:
            continue
        diff = model_ll - metrics.log_loss_per_match(probs, base.ftr)
        mean, lo, hi = metrics.paired_bootstrap(diff)
        rows.append({"karşılaştırma": f"{MODEL_NAME} − {name}", "fark": round(mean, 4),
                     "%95 GA alt": round(lo, 4), "%95 GA üst": round(hi, 4),
                     "sonuç": "model daha iyi" if hi < 0 else ("model daha kötü" if lo > 0 else "fark belirsiz")})
    return pd.DataFrame(rows)


def render_report(conn: sqlite3.Connection, config=ModelConfig()) -> str:
    base, aligned, n_pred, n_eligible = build_evaluation(conn, config=config)
    seasons = sorted(base.season.unique())
    calib = metrics.calibration_table(aligned[MODEL_NAME], base.ftr)
    calib = calib[calib.n >= 20]

    parts = [
        "# Faz 2: Poisson modeli ve piyasa karşılaştırması",
        f"Oluşturulma: {datetime.now(timezone.utc).isoformat(timespec='seconds')} (UTC).",
        "## Kurulum",
        "\n".join([
            f"- Model: bağımsız Poisson (hücum/savunma + ev avantajı), ayarlar `{config.key()}`.",
            "- Walk-forward: her maç, karar gününden (Cuma/Salı, karar #6) önce oynanmış maçlarla eğitilen modelle tahmin edilir.",
            f"- Değerlendirme: modelin en az {MIN_TRAIN_MATCHES} eğitim maçı gördüğü maçlar; "
            f"{n_pred} tahminden {n_eligible} uygun, tüm tahmin edicilerde ortak {len(base)} maç "
            f"({', '.join(season_label(s) for s in seasons)}).",
            "- Piyasa olasılıkları: 1/oran, marj oransal olarak çıkarılmış.",
            "- Kilitli final sezonları (2023/24–2024/25) kullanılmadı.",
        ]),
        "## Genel sonuç",
        "Düşük log-loss ve Brier daha iyidir. ECE: sonuç başına ortalama kalibrasyon hatası.",
        _md(_summary(base, aligned)),
        "## Sezon bazında log-loss",
        _md(_by_season(base, aligned)),
        "## Model ile piyasa arasındaki fark (log-loss, eşleştirilmiş bootstrap)",
        "Negatif fark modelin daha iyi olduğu anlamına gelir. Güven aralığı sıfırı içeriyorsa fark belirsizdir.",
        _md(_paired(base, aligned)),
        "## Poisson kalibrasyonu",
        "Her sonuç için tahmin aralığında ortalama tahmin ile gerçekleşme sıklığı (en az 20 maçlık aralıklar).",
        _md(calib),
    ]
    return "\n\n".join(parts) + "\n"
