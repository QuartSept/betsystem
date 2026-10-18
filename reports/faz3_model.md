# Faz 3: gelişmiş model

Oluşturulma: 2026-10-18T15:35:15+00:00 (UTC).

## Protokol

- Ayar sezonları: 2020/21, 2021/22. Ayarlar yalnızca burada seçildi.
- İç kontrol: 2022/23. Seçimde kullanılmadı, yalnızca raporlandı.
- 2019/20 ısınma sezonu; kilitli final sezonları (2023/24–2024/25) kullanılmadı.
- Değişiklikler sırayla eklendi: Dixon-Coles → zaman ağırlığı → xG. Her adımın katkısı bir önceki modele göre ve ayrıca yalnız başına temel modele eklendiğinde ölçüldü.
- Seçilen model: `{"dixon_coles": false, "l2": 1.0, "window_days": 3650, "xg_weight": 0.5, "xi": 0.001}`.
- Ayar sezonlarında iyileştirme getirmeyen değişiklik elenir. Karar: Dixon-Coles elendi, Zaman ağırlığı tutuldu, xG tutuldu.

## Adım adım katkı (log-loss farkı, negatif = iyileşme)

| değişiklik | ayar: fark | ayar: %95 GA | iç kontrol: fark | iç kontrol: %95 GA |
| --- | --- | --- | --- | --- |
| Dixon-Coles | 0.0013 | 0.0000 … 0.0026 | 0.001 | -0.0004 … 0.0023 |
| Zaman ağırlığı (ξ=0.001) | -0.0031 | -0.0066 … 0.0003 | -0.0035 | -0.0120 … 0.0053 |
| xG (pay=0.5) | -0.0026 | -0.0085 … 0.0031 | -0.0063 | -0.0136 … 0.0009 |

## Yalnız başına katkı (temel Poisson'a eklendiğinde)

| değişiklik | ayar: fark | ayar: %95 GA | iç kontrol: fark | iç kontrol: %95 GA |
| --- | --- | --- | --- | --- |
| Yalnız Dixon-Coles | 0.0013 | 0.0000 … 0.0026 | 0.001 | -0.0004 … 0.0023 |
| Yalnız zaman ağırlığı | -0.0031 | -0.0066 … 0.0003 | -0.0035 | -0.0120 … 0.0053 |
| Yalnız xG | -0.0037 | -0.0099 … 0.0023 | -0.0099 | -0.0179 … -0.0022 |

## Zaman ağırlığı ızgarası (Dixon-Coles açık, tüm geçmiş)

ξ gün başına; yarı ömür = ln 2 / ξ gün. ξ = 0 ağırlıksız tüm geçmiş demektir.

| xi | ayar log-loss | iç kontrol log-loss |
| --- | --- | --- |
| 0.0 | 0.9888 | 1.0197 |
| 0.0005 | 0.9883 | 1.0137 |
| 0.001 | 0.988 | 1.0082 |
| 0.0019 | 0.9881 | 1.0003 |
| 0.003 | 0.9891 | 0.994 |
| 0.005 | 0.9924 | 0.9887 |

## xG payı ızgarası (seçilen ξ ile)

Hedef = (1 − pay)·gol + pay·xG.

| xg_weight | ayar log-loss | iç kontrol log-loss |
| --- | --- | --- |
| 0.0 | 0.988 | 1.0082 |
| 0.25 | 0.9858 | 1.0044 |
| 0.5 | 0.9854 | 1.0019 |
| 0.75 | 0.9868 | 1.0006 |
| 1.0 | 0.99 | 1.0005 |

## Piyasa ile karşılaştırma

| tahmin | ayar log-loss | iç kontrol log-loss | Brier | ECE |
| --- | --- | --- | --- | --- |
| Faz 2 Poisson | 0.9911 | 1.0117 | 0.5939 | 0.0209 |
| Faz 3 model | 0.9854 | 1.0019 | 0.5899 | 0.0195 |
| Piyasa: PS erken | 0.9711 | 0.9663 | 0.5752 | 0.0242 |
| Piyasa: PS kapanış | 0.9669 | 0.9622 | 0.5726 | 0.0268 |

| karşılaştırma | fark | %95 GA |
| --- | --- | --- |
| Faz 3 model − Piyasa: PS erken | 0.0214 | 0.0108 … 0.0315 |
| Faz 3 model − Piyasa: PS kapanış | 0.0256 | 0.0143 … 0.0364 |

## Faz 3 modelinin kalibrasyonu

Dixon-Coles elendiği için seçilen modelde ρ = 0.

| outcome | bin | n | mean_pred | observed |
| --- | --- | --- | --- | --- |
| H | 0.1-0.2 | 89 | 0.1534 | 0.1348 |
| H | 0.2-0.3 | 188 | 0.2534 | 0.2819 |
| H | 0.3-0.4 | 252 | 0.3502 | 0.3571 |
| H | 0.4-0.5 | 224 | 0.4501 | 0.4286 |
| H | 0.5-0.6 | 173 | 0.5462 | 0.5665 |
| H | 0.6-0.7 | 112 | 0.6458 | 0.6429 |
| H | 0.7-0.8 | 65 | 0.7458 | 0.8308 |
| D | 0.1-0.2 | 188 | 0.1683 | 0.133 |
| D | 0.2-0.3 | 923 | 0.2468 | 0.247 |
| A | 0.0-0.1 | 54 | 0.0707 | 0.1111 |
| A | 0.1-0.2 | 187 | 0.1538 | 0.1337 |
| A | 0.2-0.3 | 264 | 0.253 | 0.25 |
| A | 0.3-0.4 | 248 | 0.3494 | 0.3952 |
| A | 0.4-0.5 | 187 | 0.4445 | 0.4439 |
| A | 0.5-0.6 | 114 | 0.5415 | 0.4912 |
| A | 0.6-0.7 | 55 | 0.6472 | 0.6727 |
| A | 0.7-0.8 | 27 | 0.7452 | 0.6296 |
