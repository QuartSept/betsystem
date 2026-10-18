# Minimum bahis sayısı (N)

N = ((z₁₋α + z₁₋β) · σ / δ)², α = 0.05 (tek yönlü, z = 1.645), güç = 0.8 (z = 0.842).

σ vekili: erken oran / marjsız Pinnacle kapanış oranı − 1; maç başına tek sonuç (sabit tohum). Yalnızca model seçimi dönemi kullanılır. Model seçtiği bahislerde σ farklı olabilir; Faz 4'te gerçek bahis dağılımıyla yeniden kontrol edilir.

## Hedef

**N = 202** bağımsız bahis (karar #30: δ = 1.5%). Ana fiyat PS erken, σ = 0.0856 (1520 maç).

## Tablo

| Bahis oranı | Rol | Sezonlar | Maç | Ortalama CLV | σ | N (δ=1.0%) | N (δ=1.5%) | N (δ=2.0%) | N (δ=3.0%) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PS erken | ana fiyat | 1920, 2021, 2122, 2223 | 1520 | -0.0191 | 0.0856 | 454 | 202 | 114 | 51 |
| B365 erken | duyarlılık | 1920, 2021, 2122, 2223 | 1520 | -0.0463 | 0.0888 | 488 | 217 | 122 | 55 |

Dipnot (teorik üst sınır, kararlarda kullanılmaz): Max erken oranında modelsiz ortalama CLV 0.014, σ 0.0976. Yalnızca en iyi fiyatı seçmek pozitif CLV üretir; bu yüzden ana fiyat olamaz.
