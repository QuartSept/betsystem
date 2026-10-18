# Hollanda Eredivisie (N1): Faz 2, Faz 3 ve hareket testi

Oluşturulma: 2026-10-18T16:01:38+00:00 (UTC).

## Protokol (karar #48)

- 2019/20 ısınma; değerlendirme 2020/21, 2021/22, 2022/23 (918 maç). Kilitli final sezonları (2023/24–2024/25) yüklenmedi.
- Ayarlar yalnızca 2020/21, 2021/22'de seçildi; 2022/23 iç kontrol (karar #33).
- xG: Understat kapsamında değil, denenmedi.
- Seçilen model: `{"dixon_coles": true, "l2": 1.0, "window_days": 730, "xg_weight": 0.0, "xi": 0.0}`. Karar: Dixon-Coles tutuldu, Zaman ağırlığı elendi.

## Faz 3 adımları (log-loss farkı, negatif = iyileşme)

| değişiklik | ayar: fark | ayar: %95 GA | iç kontrol: fark | iç kontrol: %95 GA |
| --- | --- | --- | --- | --- |
| Dixon-Coles | -0.0005 | -0.0056 … 0.0046 | 0.0007 | -0.0012 … 0.0025 |
| Zaman ağırlığı (ξ=0.0) | 0.0048 | -0.0001 … 0.0099 | 0.0109 | -0.0016 … 0.0235 |

## Zaman ağırlığı ızgarası

| xi | ayar log-loss | iç kontrol log-loss |
| --- | --- | --- |
| 0.0 | 0.9652 | 0.9516 |
| 0.0005 | 0.9641 | 0.9463 |
| 0.001 | 0.9635 | 0.9419 |
| 0.0019 | 0.9634 | 0.9363 |
| 0.003 | 0.9647 | 0.9328 |
| 0.005 | 0.9689 | 0.9323 |

## Piyasa ile karşılaştırma (Faz 2 ve Faz 3)

| tahmin | ayar log-loss | iç kontrol log-loss | Brier | ECE |
| --- | --- | --- | --- | --- |
| Faz 2 Poisson | 0.961 | 0.9401 | 0.5661 | 0.0316 |
| Faz 3 model | 0.9604 | 0.9408 | 0.566 | 0.0297 |
| Piyasa: PS erken | 0.9331 | 0.9281 | 0.5513 | 0.0178 |
| Piyasa: PS kapanış | 0.9282 | 0.9195 | 0.5476 | 0.0231 |

| karşılaştırma | fark | %95 GA |
| --- | --- | --- |
| Faz 3 model − Piyasa: PS erken | 0.0224 | 0.0113 … 0.0339 |
| Faz 3 model − Piyasa: PS kapanış | 0.0286 | 0.0165 … 0.0406 |

## Hareket testi (karar #46)

918 maç, eğim 0.0099 (tek yönlü %95 alt sınır -0.0162; %95 GA -0.0208 … 0.0390): **geçemedi**.

Sonuç bazında (bilgi amaçlı): H: eğim +0.011, korelasyon +0.023, D: eğim +0.022, korelasyon +0.050, A: eğim +0.001, korelasyon +0.002.

## Faz 3 modelinin kalibrasyonu

| outcome | bin | n | mean_pred | observed |
| --- | --- | --- | --- | --- |
| H | 0.0-0.1 | 37 | 0.0666 | 0.027 |
| H | 0.1-0.2 | 71 | 0.1514 | 0.1549 |
| H | 0.2-0.3 | 129 | 0.2521 | 0.2326 |
| H | 0.3-0.4 | 159 | 0.3519 | 0.3585 |
| H | 0.4-0.5 | 163 | 0.4507 | 0.3926 |
| H | 0.5-0.6 | 139 | 0.5482 | 0.5252 |
| H | 0.6-0.7 | 82 | 0.6487 | 0.6341 |
| H | 0.7-0.8 | 80 | 0.7492 | 0.7 |
| H | 0.8-0.9 | 42 | 0.8539 | 0.881 |
| D | 0.0-0.1 | 41 | 0.0726 | 0.1463 |
| D | 0.1-0.2 | 189 | 0.1609 | 0.1958 |
| D | 0.2-0.3 | 631 | 0.2552 | 0.2425 |
| D | 0.3-0.4 | 57 | 0.3245 | 0.3333 |
| A | 0.0-0.1 | 120 | 0.0593 | 0.0583 |
| A | 0.1-0.2 | 164 | 0.1521 | 0.1585 |
| A | 0.2-0.3 | 199 | 0.2491 | 0.3065 |
| A | 0.3-0.4 | 167 | 0.3456 | 0.3713 |
| A | 0.4-0.5 | 110 | 0.4461 | 0.3909 |
| A | 0.5-0.6 | 68 | 0.542 | 0.6765 |
| A | 0.6-0.7 | 46 | 0.6513 | 0.6957 |
| A | 0.7-0.8 | 28 | 0.7486 | 0.6071 |
