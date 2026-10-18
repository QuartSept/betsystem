# Faz 11 ön fizibilite: 10a (karar #85, #86, #89)

Oluşturulma: 2026-10-18T17:51:01+00:00 (UTC). Pencerede yalnızca erken fiyatlarla bahis sayısı sayıldı; oran değerleri, kapanış değerleri, sonuçlar ve CLV kullanılmadı. N, #89 önerisiyle (seçim dönemi σ, α = 0,05) hesaplandı; #89 onaylanmazsa bu sayfa geçersizdir.

## Pencerede lig uygunluğu (#86, yalnızca doluluk)

| lig | maç | B365 erken | Avg erken | BFE kapanış | uygun |
| --- | --- | --- | --- | --- | --- |
| B1 | 383 | 0.992 | 1.0 | 0.945 | True |
| D1 | 351 | 1.0 | 1.0 | 0.949 | True |
| D2 | 369 | 1.0 | 1.0 | 0.943 | True |
| E0 | 440 | 1.0 | 1.0 | 0.95 | True |
| E1 | 671 | 1.0 | 1.0 | 0.946 | True |
| E2 | 654 | 1.0 | 1.0 | 0.95 | True |
| E3 | 666 | 1.0 | 1.0 | 0.961 | True |
| EC | 707 | 0.983 | 0.983 | 0.982 | True |
| F1 | 360 | 1.0 | 1.0 | 0.947 | True |
| F2 | 378 | 0.997 | 1.0 | 0.95 | True |
| G1 | 278 | 0.971 | 1.0 | 0.953 | True |
| I1 | 440 | 1.0 | 1.0 | 0.952 | True |
| I2 | 440 | 1.0 | 1.0 | 0.952 | True |
| N1 | 378 | 1.0 | 1.0 | 0.95 | True |
| P1 | 377 | 1.0 | 1.0 | 0.942 | True |
| SC0 | 276 | 1.0 | 1.0 | 0.957 | True |
| SC1 | 228 | 1.0 | 1.0 | 0.952 | True |
| SC2 | 229 | 1.0 | 1.0 | 0.956 | True |
| SC3 | 230 | 1.0 | 1.0 | 0.957 | True |
| SP1 | 458 | 1.0 | 1.0 | 0.932 | True |
| SP2 | 561 | 1.0 | 1.0 | 0.954 | True |
| T1 | 369 | 1.0 | 1.0 | 0.949 | True |

## Adım 1: E0 + T1

σ (seçim dönemi, 2929 maç) = 0.0960 → **N = 254** (α = 0,05).

| lig | sezon | pencere maçı | B365+Avg erken dolu | bahis (k=0) | referans | bahis, ref. kapanış dolu |
| --- | --- | --- | --- | --- | --- | --- |
| E0 | 2526 | 380 | 380 | 25 | BFE | 22 |
| E0 | 2627 | 60 | 60 | 4 | BFE | 4 |
| T1 | 2526 | 306 | 306 | 37 | BFE | 36 |
| T1 | 2627 | 63 | 63 | 9 | BFE | 9 |

Referans kapanışı dolu bahis: şimdiye kadar **71**, 31 Aralık 2026'ya projeksiyon **89** → N’ye ulaşmıyor.

## Adım 2: uygun tüm ligler (22)

σ (seçim dönemi, 30073 maç) = 0.0956 → **N = 252** (α = 0,05).

| lig | sezon | pencere maçı | B365+Avg erken dolu | bahis (k=0) | referans | bahis, ref. kapanış dolu |
| --- | --- | --- | --- | --- | --- | --- |
| B1 | 2526 | 311 | 308 | 12 | BFE | 12 |
| B1 | 2627 | 72 | 72 | 3 | BFE | 3 |
| D1 | 2526 | 306 | 306 | 25 | BFE | 25 |
| D1 | 2627 | 45 | 45 | 9 | BFE | 9 |
| D2 | 2526 | 306 | 306 | 24 | BFE | 24 |
| D2 | 2627 | 63 | 63 | 2 | BFE | 2 |
| E0 | 2526 | 380 | 380 | 25 | BFE | 22 |
| E0 | 2627 | 60 | 60 | 4 | BFE | 4 |
| E1 | 2526 | 552 | 552 | 33 | BFE | 28 |
| E1 | 2627 | 119 | 119 | 7 | BFE | 7 |
| E2 | 2526 | 552 | 552 | 21 | BFE | 15 |
| E2 | 2627 | 102 | 102 | 7 | BFE | 7 |
| E3 | 2526 | 552 | 552 | 23 | BFE | 19 |
| E3 | 2627 | 114 | 114 | 3 | BFE | 3 |
| EC | 2526 | 552 | 540 | 14 | BFE | 14 |
| EC | 2627 | 155 | 155 | 3 | BFE | 3 |
| F1 | 2526 | 306 | 306 | 31 | BFE | 29 |
| F1 | 2627 | 54 | 54 | 9 | BFE | 9 |
| F2 | 2526 | 306 | 305 | 7 | BFE | 7 |
| F2 | 2627 | 72 | 72 | 1 | BFE | 1 |
| G1 | 2526 | 236 | 228 | 96 | BFE | 93 |
| G1 | 2627 | 42 | 42 | 15 | BFE | 15 |
| I1 | 2526 | 380 | 380 | 50 | BFE | 45 |
| I1 | 2627 | 60 | 60 | 13 | BFE | 13 |
| I2 | 2526 | 380 | 380 | 61 | BFE | 57 |
| I2 | 2627 | 60 | 60 | 7 | BFE | 7 |
| N1 | 2526 | 306 | 306 | 43 | BFE | 40 |
| N1 | 2627 | 72 | 72 | 25 | BFE | 25 |
| P1 | 2526 | 306 | 306 | 61 | BFE | 55 |
| P1 | 2627 | 71 | 71 | 15 | BFE | 14 |
| SC0 | 2526 | 228 | 228 | 31 | BFE | 30 |
| SC0 | 2627 | 48 | 48 | 8 | BFE | 8 |
| SC1 | 2526 | 180 | 180 | 3 | BFE | 3 |
| SC1 | 2627 | 48 | 48 | 1 | BFE | 1 |
| SC2 | 2526 | 180 | 180 | 4 | BFE | 3 |
| SC2 | 2627 | 49 | 49 | 1 | BFE | 1 |
| SC3 | 2526 | 180 | 180 | 5 | BFE | 5 |
| SC3 | 2627 | 50 | 50 | 0 | BFE | 0 |
| SP1 | 2526 | 380 | 380 | 29 | BFE | 26 |
| SP1 | 2627 | 78 | 78 | 14 | BFE | 14 |
| SP2 | 2526 | 462 | 462 | 37 | BFE | 33 |
| SP2 | 2627 | 99 | 99 | 24 | BFE | 23 |
| T1 | 2526 | 306 | 306 | 37 | BFE | 36 |
| T1 | 2627 | 63 | 63 | 9 | BFE | 9 |

Referans kapanışı dolu bahis: şimdiye kadar **799**, 31 Aralık 2026'ya projeksiyon **971** → N’ye ulaşıyor.

## Sonuç

Ön sonuç: test kapsamı **Adım 2: uygun tüm ligler (22)**. Kesin karar pencere verisi tamamlanınca (Ocak 2027) aynı sayımla verilir.
