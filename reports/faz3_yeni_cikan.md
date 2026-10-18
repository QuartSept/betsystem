# Yeni çıkan takım ayarı (karar #36)

Oluşturulma: 2026-10-18T15:39:03+00:00 (UTC).

## Tanım (ön kayıt, sonuçlardan önce commit edildi)

- Bir takım, bir önceki sezon veride Premier League'de yoksa o sezon boyunca yeni çıkan sayılır.
- Modele yeni çıkan takımın hücumuna ve savunmasına iki sabit kayma eklenir; cezasızdır ve eğitim penceresindeki yeni çıkan takımlardan öğrenilir. Elle seçilen sayı veya ızgara yoktur.
- Temel: Faz 3 modeli `{"dixon_coles": false, "l2": 1.0, "window_days": 3650, "xg_weight": 0.5, "xi": 0.001}`. Ayar sezonlarında log-loss düşmezse elenir (karar #33).
- Karar: **elendi**.

## Katkı (log-loss farkı, negatif = iyileşme)

| değişiklik | ayar: fark | ayar: %95 GA | iç kontrol: fark | iç kontrol: %95 GA |
| --- | --- | --- | --- | --- |
| Yeni çıkan takım ayarı (tüm maçlar) | 0.0029 | -0.0000 … 0.0062 | 0.0011 | -0.0003 … 0.0025 |
| Tanı: yeni çıkan takımın oynadığı maçlar | 0.0096 | -0.0002 … 0.0205 (n=216) | 0.0017 | -0.0013 … 0.0050 (n=108) |

## Öğrenilen kaymalar (sezon içi karar günlerinin ortalaması)

Negatif hücum kayması daha az gol atmak, negatif savunma kayması daha çok gol yemek demektir. 2020/21'in başında eğitim verisinde yeni çıkan takım bulunmadığı için kayma sıfırdan başlar (2019/20 ilk sezon, öncesi veride yok).

| season | promoted_attack | promoted_defence |
| --- | --- | --- |
| 2020/21 | -0.215 | -0.297 |
| 2021/22 | 0.025 | 0.013 |
| 2022/23 | -0.057 | -0.019 |

## Piyasa ile karşılaştırma

| tahmin | ayar log-loss | iç kontrol log-loss | Brier | ECE |
| --- | --- | --- | --- | --- |
| Faz 3 model | 0.9854 | 1.0019 | 0.5899 | 0.0195 |
| Faz 3 + yeni çıkan | 0.9883 | 1.003 | 0.5913 | 0.0192 |
| Piyasa: PS erken | 0.9711 | 0.9663 | 0.5752 | 0.0242 |
| Piyasa: PS kapanış | 0.9669 | 0.9622 | 0.5726 | 0.0268 |

| karşılaştırma | fark | %95 GA |
| --- | --- | --- |
| Faz 3 + yeni çıkan − Piyasa: PS erken | 0.0237 | 0.0126 … 0.0347 |
| Faz 3 + yeni çıkan − Piyasa: PS kapanış | 0.0279 | 0.0162 … 0.0391 |
