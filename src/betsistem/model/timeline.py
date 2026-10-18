"""Karar anı ve veri sızıntısı koruması.

Karar #6: karar anı football-data'nın erken oran saatidir. notes.txt'ye göre hafta sonu maçlarının
oranları Cuma öğleden sonra, hafta içi maçlarınki Salı öğleden sonra toplanır.

Kural: Cuma, Cumartesi, Pazar ve Pazartesi maçlarının karar günü en yakın önceki (veya aynı gün) Cuma;
Salı, Çarşamba ve Perşembe maçlarınınki en yakın önceki (veya aynı gün) Salı. Model yalnızca karar
gününden önce oynanmış maçları görür; karar günü oynanan maçlar da hariç tutulur (temkinli tercih).
"""

from datetime import date, timedelta

from betsistem.config import FINAL_TEST_SEASONS

FRIDAY, TUESDAY = 4, 1
_WEEKEND = {4, 5, 6, 0}  # Cuma, Cumartesi, Pazar, Pazartesi


class LockedSeasonError(Exception):
    """Kilitli final sezonlarına (karar #9, #20) Faz 4'teki tek seferlik çalıştırma dışında dokunulmaz."""


def decision_date(match_date: date) -> date:
    target = FRIDAY if match_date.weekday() in _WEEKEND else TUESDAY
    return match_date - timedelta(days=(match_date.weekday() - target) % 7)


class FinalSetToken:
    """Kilitli final setine tek seferlik erişim izni. Yalnızca backtest.final.open_final_set üretir;
    o fonksiyon açılışı veritabanına kalıcı olarak kaydeder ve ikinci açılışı reddeder (karar #42)."""

    def __init__(self, run_id: int):
        self.run_id = run_id


def assert_unlocked(seasons, token: FinalSetToken | None = None) -> None:
    locked = sorted(set(seasons) & set(FINAL_TEST_SEASONS))
    if locked and not isinstance(token, FinalSetToken):
        raise LockedSeasonError(f"Kilitli final sezonları kullanılamaz: {locked}")
