# Faz 4: model seçimi döneminde geriye dönük test (B1)

Oluşturulma: 2026-10-18T16:11:59+00:00 (UTC).

## Kurallar (ön kayıt: karar #38–#42)

- Lig: B1. Model: `{"dixon_coles": false, "l2": 1.0, "window_days": 3650, "xg_weight": 0.0, "xi": 0.003}` (karar #35 / #50), walk-forward, karar günü Cuma/Salı.
- Dönem: 2020/21, 2021/22, 2022/23 (2019/20 ısınma).
- Maç başına değeri en yüksek tek sonuç; değer = model olasılığı × Pinnacle erken oranı − 1.
- CLV = bahis oranı × marjsız Pinnacle kapanış olasılığı − 1. ROI sabit 1 birimle.
- Eşik seçimi: en az 273 bahis verenler arasında ortalama CLV'si en yüksek eşik.

## Eşik ızgarası

|  | bahis | ort. CLV | CLV alt (tek yönlü %95) | CLV %95 GA | ROI | ROI %95 GA | en büyük düşüş (birim) | ¼ Kelly kasa (100'den) | ¼ Kelly en büyük düşüş |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| eşik 0 | 816 | -0.029 | -0.0361 | -0.0375 … -0.0204 | -0.0058 | -0.1139 … 0.1039 | 94.8 | 37.8 | 75.5% |
| eşik 0.01 | 766 | -0.0303 | -0.0373 | -0.0389 … -0.0218 | -0.009 | -0.1175 … 0.1029 | 87.6 | 38.5 | 75.1% |
| eşik 0.02 | 737 | -0.0305 | -0.0377 | -0.0389 … -0.0217 | -0.0042 | -0.1187 … 0.1073 | 79.5 | 38.4 | 74.9% |
| eşik 0.03 | 691 | -0.0323 | -0.0399 | -0.0414 … -0.0230 | -0.0035 | -0.1216 … 0.1184 | 77.1 | 36.8 | 75.9% |
| eşik 0.05 | 632 | -0.0324 | -0.0404 | -0.0419 … -0.0228 | 0.0048 | -0.1223 … 0.1312 | 73.5 | 40.9 | 74.5% |
| eşik 0.075 | 553 | -0.0319 | -0.0407 | -0.0423 … -0.0212 | 0.0037 | -0.1339 … 0.1476 | 77.0 | 37.1 | 76.3% |
| eşik 0.1 | 479 | -0.0284 | -0.0377 | -0.0397 … -0.0168 | -0.0019 | -0.1512 … 0.1525 | 66.7 | 44.7 | 73.4% |

## Seçilen eşik: 0.1

|  | bahis | ort. CLV | CLV alt (tek yönlü %95) | CLV %95 GA | ROI | ROI %95 GA | en büyük düşüş (birim) | ¼ Kelly kasa (100'den) | ¼ Kelly en büyük düşüş |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tüm dönem | 479 | -0.0284 | -0.0377 | -0.0397 … -0.0168 | -0.0019 | -0.1512 … 0.1525 | 66.7 | 44.7 | 73.4% |
| 2020/21 | 181 | -0.0259 | -0.0432 | -0.0465 … -0.0040 | 0.2181 | -0.0456 … 0.5126 | 12.0 | 63.6 | 51.7% |
| 2021/22 | 178 | -0.0358 | -0.0524 | -0.0554 … -0.0154 | -0.0617 | -0.2961 … 0.1777 | 30.1 | 99.6 | 29.7% |
| 2022/23 | 120 | -0.021 | -0.0352 | -0.0379 … -0.0042 | -0.2452 | -0.4658 … -0.0041 | 39.6 | 70.5 | 49.5% |

## Duyarlılık: B365 erken oranı (karar #25)

Aynı model ve eşik; bahis B365 erken oranıyla seçilir, CLV B365 kapanışına göre hesaplanır.

|  | bahis | ort. CLV | CLV alt (tek yönlü %95) | CLV %95 GA | ROI | ROI %95 GA | en büyük düşüş (birim) | ¼ Kelly kasa (100'den) | ¼ Kelly en büyük düşüş |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B365 erken, eşik 0.1 | 403 | -0.0515 | -0.0624 | -0.0643 … -0.0385 | -0.0513 | -0.2078 … 0.1143 | 56.6 | 30.2 | 75.4% |

## Geçme şartı (karar #42), seçim dönemi

En az 273 bahis, ortalama CLV > 0, tek yönlü %95 alt sınır > 0: **sağlanmadı** (479 bahis, ortalama CLV -0.0284, alt sınır -0.0377).

Kâr var ama CLV negatifse sonuç büyük ihtimalle şanstır.
