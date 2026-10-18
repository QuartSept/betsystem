"""Proje genelindeki sabitler. Faz 0 kararları burada koda dökülür ve değiştirilmez."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "db" / "betsistem.sqlite"

# Sezon kodları football-data biçiminde: "2223" = 2022/23.
# Karar #9: model seçimi 2019/20–2022/23, kilitli final test 2023/24–2024/25.
MODEL_SELECTION_SEASONS = ("1920", "2021", "2122", "2223")
FINAL_TEST_SEASONS = ("2324", "2425")
PROTOTYPE_SEASON = "2223"  # Karar #15
# Karar #65, #81: Faz 11 bağımsız değerlendirme penceresi. Kod kilidiyle korunur; 8.5 için yalnızca doluluk.
FAZ11_WINDOW_SEASONS = ("2526", "2627")

# Karar #3: Premier League ile başlanır. Diğerleri lig taraması (karar #47) için yüklenir.
LEAGUES = {
    "E0": "İngiltere Premier League", "E1": "İngiltere Championship", "E2": "İngiltere League One",
    "E3": "İngiltere League Two", "EC": "İngiltere National League",
    "SC0": "İskoçya Premiership", "SC1": "İskoçya Championship", "SC2": "İskoçya League One",
    "SC3": "İskoçya League Two",
    "D1": "Almanya Bundesliga", "D2": "Almanya 2. Bundesliga",
    "I1": "İtalya Serie A", "I2": "İtalya Serie B",
    "SP1": "İspanya La Liga", "SP2": "İspanya Segunda",
    "F1": "Fransa Ligue 1", "F2": "Fransa Ligue 2",
    "N1": "Hollanda Eredivisie", "B1": "Belçika Pro League", "P1": "Portekiz Primeira Liga",
    "T1": "Türkiye Süper Lig", "G1": "Yunanistan Super League",
}

# Karar #10: yalnızca 1-X-2. Karar #75: alt/üst 2.5 tarihsel testte (10c).
MARKET_1X2 = "1X2"
MARKET_OU25 = "OU25"
MARKET_OUTCOMES = {MARKET_1X2: ("H", "D", "A"), MARKET_OU25: ("O", "U")}  # O = 2.5 üst, U = 2.5 alt

# Karar #24–#26: bahis fiyatı rolleri (football-data şirket kodları, erken oran).
BET_PRICE_BOOKMAKER = "PS"  # ana fiyat; eksikse bahis yok (karar #27)
SENSITIVITY_BOOKMAKERS = ("B365",)  # ayrıca raporlanır
UPPER_BOUND_BOOKMAKER = "Max"  # yalnızca teorik üst sınır dipnotu

# Minimum bağımsız bahis sayısı (δ = %1,5): karar #30 (E0), karar #51 (B1).
N_TARGET = 202
N_TARGETS = {"E0": N_TARGET, "B1": 273}


def season_label(code: str) -> str:
    """'2223' -> '2022/23'."""
    if len(code) != 4 or not code.isdigit():
        raise ValueError(f"Geçersiz sezon kodu: {code!r}")
    start = int(code[:2])
    century = 1900 if start >= 90 else 2000
    return f"{century + start}/{code[2:]}"


def season_of(d) -> str:
    """Tarihin düştüğü sezon kodu. Sezon Temmuz'da başlar: 2026-10-18 -> '2627'."""
    start = d.year if d.month >= 7 else d.year - 1
    return f"{start % 100:02d}{(start + 1) % 100:02d}"


def is_final_test_season(code: str) -> bool:
    return code in FINAL_TEST_SEASONS
