"""Minimum bağımsız bahis sayısı N (Faz 0): N = ((z_{1-α} + z_{1-β}) · σ / δ)².

σ, bahis başına CLV'nin standart sapmasıdır. Model henüz yokken σ, model seçimi dönemindeki
tüm 1-X-2 sonuçları üzerinden bir vekil (proxy) ile tahmin edilir:

    CLV = erken oran / marjsız kapanış oranı - 1

Marjsız kapanış oranı, kıyas şirketinin (karar #7: 2024/25'e kadar Pinnacle) kapanış oranlarından
oransal yöntemle marj çıkarılarak bulunur. Gerçek bahisler modelin seçtiği alt kümeden oluşacağı
için bu bir yaklaşıklıktır; varsayım raporda açıkça belirtilir.

Aynı maça ait bahisler tek gözlem sayılır (Faz 0), bu yüzden σ maç başına tek sonuçla hesaplanır:
her maçtan sabit tohumla rastgele seçilen bir sonuç alınır.
"""

import math
import sqlite3
from dataclasses import dataclass
from statistics import NormalDist

import numpy as np
import pandas as pd

from betsistem.config import (
    BET_PRICE_BOOKMAKER,
    FINAL_TEST_SEASONS,
    MODEL_SELECTION_SEASONS,
    SENSITIVITY_BOOKMAKERS,
    UPPER_BOUND_BOOKMAKER,
)
from betsistem.model.market import fair_probabilities

ALPHA = 0.05  # tek yönlü: CLV > 0
POWER = 0.80
TARGET_DELTA = 0.015  # karar #30: tespit edilmek istenen ortalama CLV
DELTAS = (0.01, TARGET_DELTA, 0.02, 0.03)  # tabloda karşılaştırma için
SEED = 20261018


def required_n(sigma: float, delta: float, alpha: float = ALPHA, power: float = POWER) -> int:
    z = NormalDist().inv_cdf
    return math.ceil(((z(1 - alpha) + z(power)) * sigma / delta) ** 2)


@dataclass
class ClvSigma:
    bet_bookmaker: str
    seasons: tuple[str, ...]
    matches: int
    mean_clv: float
    sigma: float


def clv_proxy(conn: sqlite3.Connection, bet_bookmaker: str, benchmark: str = "PS") -> pd.DataFrame:
    """Model seçimi dönemi için maç x sonuç başına CLV vekili."""
    seasons = MODEL_SELECTION_SEASONS
    assert not set(seasons) & set(FINAL_TEST_SEASONS), "Kilitli final sezonları kullanılamaz"

    fair = fair_probabilities(conn, benchmark)
    fair = fair[(fair.timing == "closing") & fair.season.isin(seasons)]
    fair = fair.melt(id_vars=["match_id", "season"], value_vars=["H", "D", "A"], var_name="outcome", value_name="p")

    placeholders = ",".join("?" for _ in seasons)
    early = pd.read_sql(
        "SELECT o.match_id, o.outcome, o.price FROM odds o JOIN matches m ON m.id = o.match_id"
        f" WHERE o.market = '1X2' AND o.bookmaker = ? AND o.timing = 'early' AND m.season IN ({placeholders})",
        conn,
        params=(bet_bookmaker, *seasons),
    )
    df = early.merge(fair, on=["match_id", "outcome"])
    df["clv"] = df["price"] * df["p"] - 1.0
    return df


def estimate_sigma(conn: sqlite3.Connection, bet_bookmaker: str) -> ClvSigma:
    df = clv_proxy(conn, bet_bookmaker)
    rng = np.random.default_rng(SEED)
    one_per_match = df.groupby("match_id", group_keys=False).apply(
        lambda g: g.iloc[[rng.integers(len(g))]], include_groups=False
    )
    return ClvSigma(
        bet_bookmaker=bet_bookmaker,
        seasons=tuple(sorted(df["season"].unique())),
        matches=len(one_per_match),
        mean_clv=round(float(one_per_match["clv"].mean()), 4),
        sigma=round(float(one_per_match["clv"].std(ddof=1)), 4),
    )


def render_report(conn: sqlite3.Connection) -> str:
    """Karar #28: N ana bahis fiyatı (Pinnacle erken) üzerinden belirlenir.

    B365 duyarlılık için (karar #25), Max yalnızca teorik üst sınır dipnotu olarak (karar #26) gösterilir.
    """
    z = NormalDist().inv_cdf
    roles = [(BET_PRICE_BOOKMAKER, "ana fiyat")] + [(bk, "duyarlılık") for bk in SENSITIVITY_BOOKMAKERS]
    rows = [(estimate_sigma(conn, bk), role) for bk, role in roles]
    upper = estimate_sigma(conn, UPPER_BOUND_BOOKMAKER)
    main = rows[0][0]

    header = "| Bahis oranı | Rol | Sezonlar | Maç | Ortalama CLV | σ | " + " | ".join(
        f"N (δ={d:.1%})" for d in DELTAS
    ) + " |"
    lines = [
        "# Minimum bahis sayısı (N)",
        "",
        f"N = ((z₁₋α + z₁₋β) · σ / δ)², α = {ALPHA} (tek yönlü, z = {z(1 - ALPHA):.3f}), "
        f"güç = {POWER} (z = {z(POWER):.3f}).",
        "",
        "σ vekili: erken oran / marjsız Pinnacle kapanış oranı − 1; maç başına tek sonuç (sabit tohum). "
        "Yalnızca model seçimi dönemi kullanılır. Model seçtiği bahislerde σ farklı olabilir; "
        "Faz 4'te gerçek bahis dağılımıyla yeniden kontrol edilir.",
        "",
        "## Hedef",
        "",
        f"**N = {required_n(main.sigma, TARGET_DELTA)}** bağımsız bahis (karar #30: δ = {TARGET_DELTA:.1%}). "
        f"Ana fiyat {BET_PRICE_BOOKMAKER} erken, σ = {main.sigma} ({main.matches} maç).",
        "",
        "## Tablo",
        "",
        header,
        "| --- | --- | --- | --- | --- | --- | " + " | ".join("---" for _ in DELTAS) + " |",
    ]
    for s, role in rows:
        if s.matches == 0:
            continue
        ns = " | ".join(str(required_n(s.sigma, d)) for d in DELTAS)
        lines.append(
            f"| {s.bet_bookmaker} erken | {role} | {', '.join(s.seasons)} | {s.matches} | {s.mean_clv} | {s.sigma} | {ns} |"
        )
    lines += [
        "",
        f"Dipnot (teorik üst sınır, kararlarda kullanılmaz): {UPPER_BOUND_BOOKMAKER} erken oranında modelsiz "
        f"ortalama CLV {upper.mean_clv}, σ {upper.sigma}. Yalnızca en iyi fiyatı seçmek pozitif CLV üretir; "
        "bu yüzden ana fiyat olamaz.",
    ]
    return "\n".join(lines) + "\n"
