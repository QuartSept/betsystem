# Faz 4: model seçimi döneminde geriye dönük test

Oluşturulma: 2026-10-18T15:43:03+00:00 (UTC).

## Kurallar (ön kayıt: karar #38–#42)

- Model: `{"dixon_coles": false, "l2": 1.0, "window_days": 3650, "xg_weight": 0.5, "xi": 0.001}` (karar #35), walk-forward, karar günü Cuma/Salı.
- Dönem: 2020/21, 2021/22, 2022/23 (2019/20 ısınma).
- Maç başına değeri en yüksek tek sonuç; değer = model olasılığı × Pinnacle erken oranı − 1.
- CLV = bahis oranı × marjsız Pinnacle kapanış olasılığı − 1. ROI sabit 1 birimle.
- Eşik seçimi: en az 202 bahis verenler arasında ortalama CLV'si en yüksek eşik.

## Eşik ızgarası

|  | bahis | ort. CLV | CLV alt (tek yönlü %95) | CLV %95 GA | ROI | ROI %95 GA | en büyük düşüş (birim) | ¼ Kelly kasa (100'den) | ¼ Kelly en büyük düşüş |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| eşik 0 | 1116 | -0.0188 | -0.0241 | -0.0252 … -0.0125 | -0.0289 | -0.1432 … 0.0955 | 96.8 | 6.4 | 96.4% |
| eşik 0.01 | 1094 | -0.0191 | -0.0243 | -0.0252 … -0.0124 | -0.0289 | -0.1482 … 0.1027 | 100.5 | 6.4 | 96.4% |
| eşik 0.02 | 1068 | -0.0188 | -0.0243 | -0.0252 … -0.0121 | -0.0225 | -0.1442 … 0.1107 | 96.4 | 6.7 | 96.3% |
| eşik 0.03 | 1042 | -0.0188 | -0.0243 | -0.0252 … -0.0118 | -0.0205 | -0.1471 … 0.1144 | 90.2 | 7.2 | 96.2% |
| eşik 0.05 | 951 | -0.0173 | -0.0234 | -0.0248 … -0.0100 | -0.0377 | -0.1710 … 0.1046 | 98.0 | 7.2 | 96.4% |
| eşik 0.075 | 858 | -0.0173 | -0.0238 | -0.0251 … -0.0093 | -0.0308 | -0.1754 … 0.1234 | 98.5 | 7.7 | 96.5% |
| eşik 0.1 | 778 | -0.0171 | -0.0242 | -0.0256 … -0.0088 | -0.0252 | -0.1799 … 0.1339 | 88.3 | 8.1 | 95.9% |

## Seçilen eşik: 0.1

|  | bahis | ort. CLV | CLV alt (tek yönlü %95) | CLV %95 GA | ROI | ROI %95 GA | en büyük düşüş (birim) | ¼ Kelly kasa (100'den) | ¼ Kelly en büyük düşüş |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tüm dönem | 778 | -0.0171 | -0.0242 | -0.0256 … -0.0088 | -0.0252 | -0.1799 … 0.1339 | 88.3 | 8.1 | 95.9% |
| 2020/21 | 254 | -0.0108 | -0.024 | -0.0265 … 0.0046 | 0.2572 | -0.0274 … 0.5620 | 19.6 | 193.6 | 38.3% |
| 2021/22 | 270 | -0.0226 | -0.0336 | -0.0356 … -0.0096 | -0.1267 | -0.3824 … 0.1684 | 49.1 | 33.0 | 67.8% |
| 2022/23 | 254 | -0.0175 | -0.0299 | -0.0321 … -0.0029 | -0.1998 | -0.4343 … 0.0648 | 53.1 | 12.7 | 87.6% |

## Duyarlılık: B365 erken oranı (karar #25)

Aynı model ve eşik; bahis B365 erken oranıyla seçilir, CLV B365 kapanışına göre hesaplanır.

|  | bahis | ort. CLV | CLV alt (tek yönlü %95) | CLV %95 GA | ROI | ROI %95 GA | en büyük düşüş (birim) | ¼ Kelly kasa (100'den) | ¼ Kelly en büyük düşüş |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B365 erken, eşik 0.1 | 669 | -0.0346 | -0.0423 | -0.0438 … -0.0250 | -0.0237 | -0.1907 … 0.1473 | 73.8 | 10.0 | 93.9% |

## Geçme şartı (karar #42), seçim dönemi

En az 202 bahis, ortalama CLV > 0, tek yönlü %95 alt sınır > 0: **sağlanmadı** (778 bahis, ortalama CLV -0.0171, alt sınır -0.0242).

Kâr var ama CLV negatifse sonuç büyük ihtimalle şanstır.
