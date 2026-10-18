# Faz 2: Poisson modeli ve piyasa karşılaştırması

Oluşturulma: 2026-10-18T15:05:22+00:00 (UTC).

## Kurulum

- Model: bağımsız Poisson (hücum/savunma + ev avantajı), ayarlar `{"l2": 1.0, "window_days": 730}`.
- Walk-forward: her maç, karar gününden (Cuma/Salı, karar #6) önce oynanmış maçlarla eğitilen modelle tahmin edilir.
- Değerlendirme: modelin en az 380 eğitim maçı gördüğü maçlar; 1510 tahminden 1140 uygun, tüm tahmin edicilerde ortak 1140 maç (2020/21, 2021/22, 2022/23).
- Piyasa olasılıkları: 1/oran, marj oransal olarak çıkarılmış.
- Kilitli final sezonları (2023/24–2024/25) kullanılmadı.

## Genel sonuç

Düşük log-loss ve Brier daha iyidir. ECE: sonuç başına ortalama kalibrasyon hatası.

| tahmin | maç | log-loss | Brier | ECE | ort. P(X) | gerçek X |
| --- | --- | --- | --- | --- | --- | --- |
| Poisson | 1140 | 0.998 | 0.5939 | 0.0209 | 0.2321 | 0.2263 |
| Piyasa: PS erken | 1140 | 0.9695 | 0.5752 | 0.0242 | 0.2429 | 0.2263 |
| Piyasa: PS kapanış | 1140 | 0.9653 | 0.5726 | 0.0268 | 0.2444 | 0.2263 |
| Piyasa: B365 erken | 1140 | 0.9701 | 0.5752 | 0.0236 | 0.2416 | 0.2263 |
| Piyasa: Avg erken | 1140 | 0.9687 | 0.5747 | 0.0244 | 0.2433 | 0.2263 |
| Geçmiş sıklık | 1140 | 1.0683 | 0.6471 | 0.0054 | 0.2343 | 0.2263 |

## Sezon bazında log-loss

| sezon | maç | Poisson | Piyasa: PS erken | Piyasa: PS kapanış | Piyasa: B365 erken | Piyasa: Avg erken | Geçmiş sıklık |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2020/21 | 380 | 1.0249 | 1.0059 | 0.9971 | 1.007 | 1.0042 | 1.0791 |
| 2021/22 | 380 | 0.9574 | 0.9363 | 0.9367 | 0.9372 | 0.936 | 1.0701 |
| 2022/23 | 380 | 1.0117 | 0.9663 | 0.9622 | 0.9662 | 0.9658 | 1.0558 |

## Model ile piyasa arasındaki fark (log-loss, eşleştirilmiş bootstrap)

Negatif fark modelin daha iyi olduğu anlamına gelir. Güven aralığı sıfırı içeriyorsa fark belirsizdir.

| karşılaştırma | fark | %95 GA alt | %95 GA üst | sonuç |
| --- | --- | --- | --- | --- |
| Poisson − Piyasa: PS erken | 0.0285 | 0.0168 | 0.0403 | model daha kötü |
| Poisson − Piyasa: PS kapanış | 0.0327 | 0.0201 | 0.0452 | model daha kötü |
| Poisson − Piyasa: B365 erken | 0.0278 | 0.0163 | 0.0394 | model daha kötü |
| Poisson − Piyasa: Avg erken | 0.0293 | 0.0178 | 0.0409 | model daha kötü |
| Poisson − Geçmiş sıklık | -0.0703 | -0.0969 | -0.0452 | model daha iyi |

## Poisson kalibrasyonu

Her sonuç için tahmin aralığında ortalama tahmin ile gerçekleşme sıklığı (en az 20 maçlık aralıklar).

| outcome | bin | n | mean_pred | observed |
| --- | --- | --- | --- | --- |
| H | 0.0-0.1 | 33 | 0.0719 | 0.0909 |
| H | 0.1-0.2 | 103 | 0.1556 | 0.2039 |
| H | 0.2-0.3 | 201 | 0.2532 | 0.2488 |
| H | 0.3-0.4 | 226 | 0.3506 | 0.385 |
| H | 0.4-0.5 | 189 | 0.4512 | 0.4444 |
| H | 0.5-0.6 | 161 | 0.5481 | 0.559 |
| H | 0.6-0.7 | 118 | 0.6457 | 0.6017 |
| H | 0.7-0.8 | 76 | 0.7449 | 0.7895 |
| H | 0.8-0.9 | 25 | 0.8294 | 0.76 |
| D | 0.1-0.2 | 221 | 0.1642 | 0.1538 |
| D | 0.2-0.3 | 850 | 0.2465 | 0.2435 |
| D | 0.3-0.4 | 56 | 0.3194 | 0.2679 |
| A | 0.0-0.1 | 84 | 0.0696 | 0.1548 |
| A | 0.1-0.2 | 193 | 0.1541 | 0.1554 |
| A | 0.2-0.3 | 232 | 0.2515 | 0.2414 |
| A | 0.3-0.4 | 227 | 0.3485 | 0.37 |
| A | 0.4-0.5 | 178 | 0.4507 | 0.4719 |
| A | 0.5-0.6 | 117 | 0.5429 | 0.5214 |
| A | 0.6-0.7 | 61 | 0.6389 | 0.4918 |
| A | 0.7-0.8 | 39 | 0.7471 | 0.6667 |
