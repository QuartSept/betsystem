# Belçika Pro League (B1): Faz 2, Faz 3 ve hareket testi

Oluşturulma: 2026-10-18T16:01:29+00:00 (UTC).

## Protokol (karar #48)

- 2019/20 ısınma; değerlendirme 2020/21, 2021/22, 2022/23 (918 maç). Kilitli final sezonları (2023/24–2024/25) yüklenmedi.
- Ayarlar yalnızca 2020/21, 2021/22'de seçildi; 2022/23 iç kontrol (karar #33).
- xG: Understat kapsamında değil, denenmedi.
- Seçilen model: `{"dixon_coles": false, "l2": 1.0, "window_days": 3650, "xg_weight": 0.0, "xi": 0.003}`. Karar: Dixon-Coles elendi, Zaman ağırlığı tutuldu.

## Faz 3 adımları (log-loss farkı, negatif = iyileşme)

| değişiklik | ayar: fark | ayar: %95 GA | iç kontrol: fark | iç kontrol: %95 GA |
| --- | --- | --- | --- | --- |
| Dixon-Coles | 0.0006 | -0.0007 … 0.0018 | -0.0001 | -0.0009 … 0.0007 |
| Zaman ağırlığı (ξ=0.003) | -0.005 | -0.0128 … 0.0026 | 0.0015 | -0.0074 … 0.0103 |

## Zaman ağırlığı ızgarası

| xi | ayar log-loss | iç kontrol log-loss |
| --- | --- | --- |
| 0.0 | 1.0291 | 0.9813 |
| 0.0005 | 1.0271 | 0.9801 |
| 0.001 | 1.0255 | 0.9797 |
| 0.0019 | 1.0235 | 0.9803 |
| 0.003 | 1.0223 | 0.9828 |
| 0.005 | 1.0225 | 0.9895 |

## Piyasa ile karşılaştırma (Faz 2 ve Faz 3)

| tahmin | ayar log-loss | iç kontrol log-loss | Brier | ECE |
| --- | --- | --- | --- | --- |
| Faz 2 Poisson | 1.028 | 0.9781 | 0.6044 | 0.03 |
| Faz 3 model | 1.0228 | 0.9787 | 0.6021 | 0.0239 |
| Piyasa: PS erken | 1.0076 | 0.9617 | 0.5918 | 0.0287 |
| Piyasa: PS kapanış | 0.9886 | 0.9652 | 0.5835 | 0.0256 |

| karşılaştırma | fark | %95 GA |
| --- | --- | --- |
| Faz 3 model − Piyasa: PS erken | 0.0158 | 0.0044 … 0.0272 |
| Faz 3 model − Piyasa: PS kapanış | 0.0273 | 0.0148 … 0.0397 |

## Hareket testi (karar #46)

914 maç, eğim 0.0471 (tek yönlü %95 alt sınır 0.0177; %95 GA 0.0124 … 0.0832): **geçti**.

Sonuç bazında (bilgi amaçlı): H: eğim +0.023, korelasyon +0.041, D: eğim +0.118, korelasyon +0.193, A: eğim +0.019, korelasyon +0.034.

## Faz 3 modelinin kalibrasyonu

| outcome | bin | n | mean_pred | observed |
| --- | --- | --- | --- | --- |
| H | 0.1-0.2 | 81 | 0.1549 | 0.1852 |
| H | 0.2-0.3 | 160 | 0.2498 | 0.2938 |
| H | 0.3-0.4 | 178 | 0.3545 | 0.3764 |
| H | 0.4-0.5 | 170 | 0.4497 | 0.4412 |
| H | 0.5-0.6 | 155 | 0.5496 | 0.4839 |
| H | 0.6-0.7 | 109 | 0.6459 | 0.6147 |
| H | 0.7-0.8 | 40 | 0.7402 | 0.675 |
| D | 0.1-0.2 | 182 | 0.1735 | 0.1648 |
| D | 0.2-0.3 | 727 | 0.2395 | 0.2407 |
| A | 0.0-0.1 | 39 | 0.0727 | 0.1026 |
| A | 0.1-0.2 | 160 | 0.1583 | 0.2 |
| A | 0.2-0.3 | 201 | 0.2493 | 0.2637 |
| A | 0.3-0.4 | 182 | 0.3474 | 0.3736 |
| A | 0.4-0.5 | 157 | 0.4494 | 0.3949 |
| A | 0.5-0.6 | 110 | 0.5461 | 0.5182 |
| A | 0.6-0.7 | 52 | 0.6486 | 0.6731 |
