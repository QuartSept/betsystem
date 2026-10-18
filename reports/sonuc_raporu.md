# Futbol Bahis Analiz Sistemi: Sonuç Raporu

18 Ekim 2026 · Kod: https://github.com/QuartSept/betsystem · Kararlar: `docs/yol-plani.md` (#1–#53)

## Özet

Proje, bahis şirketlerinin oranı yanlış koyduğu yerleri sistematik olarak bulup bulamayacağımızı sınadı. Cevap, kurduğumuz model ailesi için **hayır**.

- **Premier League:** Gol ve xG tabanlı model, Pinnacle'ın erken oranından anlamlı ölçüde daha kötü tahmin yaptı. Model seçimi döneminde (2020/21–2022/23) 778 sanal bahiste ortalama CLV −%1,7 çıktı. Bu, rastgele bahsin beklenen değeri olan −%1,9'dan pek farklı değil.
- **Diğer ligler:** Daha az verimli ligleri bulmak için 21 lig tarandı; Belçika ve Hollanda seçildi.
  - Hollanda'da model, piyasanın sonradan öğrendiği bilgiyi taşımadı.
  - Belçika'da küçük ama gerçek bir sinyal bulundu. Ancak 479 bahiste CLV −%2,8 kaldı: sinyal %4,1'lik marjı aşmaya yetmedi.
- **Faz 7 kararı (#53):** Katman 1 "Hayır", proje durduruldu, gerçek para kullanılmadı.
- **Final setler:** Kilitli final setleri (2023/24–2024/25) hiçbir ligde açılmadı. İleride önceden kaydedilmiş yeni bir model için bağımsız doğrulama verisi olarak duruyorlar.

Plan, bu sonucu erken ve ucuza öğrenmek üzerine kurulmuştu. Bu açıdan amacına ulaştı.

## 1. Soru ve kurallar

Sistem "hangi kupon tutar" sorusunu değil, "oran nerede yanlış" sorusunu sordu. Kurallar sonuçlar görülmeden yazıldı ve değiştirilmedi.

**Ana ölçüt CLV.** Bahsin alındığı oran ile kapanış oranı karşılaştırılır. Kâr şansa bağlı olabilir; kapanış oranını tutarlı biçimde yenmek ise gerçek bir avantajın en erken göstergesidir.

**Fiyatlar:**
- Bahis Pinnacle'ın erken oranından yapılmış sayıldı (#24). Bu oran, football-data'nın erken oranı topladığı anda alınabilecek fiyattı: hafta sonu maçları için Cuma, hafta içi maçlar için Salı öğleden sonra.
- CLV, marjı çıkarılmış Pinnacle kapanış oranına göre ölçüldü (#39).
- B365 duyarlılık testi olarak raporlandı. En iyi fiyat (Max) karar için hiç kullanılmadı: modelsiz en iyi fiyat seçimi bile pozitif CLV verdiği için yanıltıcıdır (#26).

**Veri bölümü (#9, #32, #33):**
- 2019/20 ısınma sezonu.
- 2020/21–2021/22 ayar sezonları.
- 2022/23 iç kontrol sezonu.
- 2023/24–2024/25 kilitli final set.

**Ön kayıt.** Her yeni ayar, test ve geçme şartı, sonuçtan önce ayrı bir commit ile kayda alındı:

| Commit | Ön kayda alınan |
| --- | --- |
| 8d134ba | Yeni çıkan takım ayarı |
| 50f5973 | Faz 4 bahis kuralı, CLV, eşik seçimi ve geçme şartı |
| 0bb2df8 | Hareket testi, lig taraması ve yeni lig protokolü |

**Faz 4 geçme şartı (#42).** En az N bağımsız bahiste ortalama CLV pozitif olmalı ve tek yönlü %95 alt sınırı sıfırın üstünde kalmalı. Aynısı kilitli final sette de tutmalı.

## 2. Veri

**Premier League:**
- 2019/20–2026/27 arası 8 sezon, 2.720 maç.
- 16 şirket ve zaman diliminde 1-X-2 oranları.
- Understat xG ve npxG ile tam eşleşme.

**Diğer ligler:** football-data sezon paketleriyle 21 lig daha yüklendi (2019/20–2022/23). Toplam 30.067 maç ve 1,43 milyon oran kaydı oldu.

**Erişim:** football-data.co.uk Türkiye'den engelli olduğu için dosyalar elle indirildi. Her ham dosya sha256 ile bir veri sürümü olarak saklandı.

**Önemli bulgu:** Pinnacle oranları football-data'da 17 Ocak 2026'dan beri yok. Model seçimi ve final dönemleri bundan etkilenmedi (eksiklik %0). Ama canlı test (Faz 6) için ana fiyat artık bulunmuyor.

**N (#30, #51).** Gereken bağımsız bahis sayısı, δ = %1,5, α = 0,05 ve güç = 0,80 ile hesaplandı:

| Lig | σ | N |
| --- | --- | --- |
| Premier League | 0,0856 | 202 |
| Belçika | 0,0995 | 273 |

## 3. Model: Premier League (Faz 2–3)

**Değerlendirme:** 1.140 maç, 2020/21–2022/23, walk-forward. Her maç, yalnızca karar gününden önceki veriyle tahmin edildi.

| Tahmin | Log-loss | Not |
| --- | --- | --- |
| Pinnacle kapanış | 0,965 | Kıyas tavanı |
| Pinnacle erken | 0,970 | Bahis anındaki piyasa |
| Faz 3 modeli | 0,985 / 1,002 (ayar / iç kontrol) | Poisson, zaman ağırlığı ξ = 0,001, hedefin yarısı xG (#35) |
| Faz 2 Poisson | 0,998 | Hücum, savunma ve ev avantajı |
| Geçmiş sıklık | 1,068 | En basit kıyas |

**Faz 3 değişiklikleri** (#33–#37; ayar sezonlarında iyileştirme getirmeyen elendi):

| Değişiklik | Log-loss etkisi | Karar |
| --- | --- | --- |
| Dixon-Coles | +0,0013 | Elendi |
| Zaman ağırlığı | −0,003 | Tutuldu |
| xG | −0,003 | Tutuldu |
| Yeni çıkan takım ayarı (ön kayıtlı) | +0,0029 | Elendi |

**Sonuç:**
- Model geçmiş sıklıktan açıkça iyi. Ama Pinnacle erken oranından anlamlı ölçüde kötü: fark +0,021 (%95 GA 0,011–0,032).
- Kalibrasyon iyi: ECE 0,020, Pinnacle erken oranında 0,024.

## 4. Geriye dönük test: Premier League (Faz 4)

Kurala göre seçilen eşik 0,10 (#38–#42):

| | Değer |
| --- | --- |
| Bahis | 778 |
| Ortalama CLV | −%1,71 (tek yönlü alt sınır −%2,42) |
| ROI | −%2,5 (%95 GA −%18 … +%13) |
| Çeyrek Kelly kasası | 100 birimden 8 birime |
| B365 duyarlılığı | CLV −%3,5 |

- Bütün eşiklerde CLV −%1,7 ile −%1,9 arasında kaldı, yani rastgele seçim düzeyinde. **Geçme şartı sağlanmadı (#43).**
- 2020/21'de +%26 ROI var, ama CLV o sezonda da negatif. Plandaki uyarı tam bu durumu tarif ediyor: kâr var ama CLV negatifse sonuç şanstır.
- Kelly'nin kasayı eritmesinin nedeni, modelin kendinden fazla emin olup büyük paylar önermesi.

**Hareket teşhisi (#45):** Modelin erken orandan sapması ile oranın kapanışa kadarki hareketi arasında korelasyon yok (−0,02 … +0,07). Model, piyasanın Cuma'dan sonra öğrendiği bir şeyi bilmiyor.

## 5. Modele geri dönüş: başka ligler

**Lig taraması (#47, #49).** Model kurmadan, yalnızca oranlara bakılarak "Cuma'dan sonra piyasaya ne kadar bilgi giriyor" ölçüldü (erken ile kapanış arasındaki log-loss farkı):

| Lig | Bilgi kazancı | Erken marj | Durum |
| --- | --- | --- | --- |
| Yunanistan | 0,0105 | %5,6 | Uygun değil (az maç) |
| **Belçika** | **0,0087** | %4,1 | **Seçildi** |
| **Hollanda** | **0,0075** | %3,3 | **Seçildi** |
| Türkiye | 0,0058 | %3,4 | Üçüncü sırada |
| Premier League | 0,0031 | %2,7 | Referans |

Büyük ligler (La Liga, Bundesliga, Serie A, Ligue 1) Premier League kadar verimli çıktı.

**Hareket testi (#46, #50).** Bir ligin Faz 4'e girmesi için önce bu testi geçmesi gerekiyordu: modelin sapması, kapanış hareketini öngörüyor mu?

| Lig | Eğim | Tek yönlü alt sınır | Sonuç |
| --- | --- | --- | --- |
| Premier League | 0,001 | −0,018 | Geçemedi |
| Hollanda | 0,010 | −0,016 | Geçemedi |
| Belçika | 0,047 | 0,018 | **Geçti** |

Belçika'da eğim üç sezonda da pozitif çıktı (0,010; 0,062; 0,091). En güçlü olduğu yer, ayar seçiminde kullanılmayan iç kontrol sezonuydu. Etkinin büyük kısmı beraberliklerden geliyor (eğim 0,118).

**Belçika Faz 4 (#52).** Seçilen eşik 0,10, 479 bahis, ortalama CLV −%2,84 (alt sınır −%3,77), ROI −%0,2. Üç sezonda da CLV negatif. **Geçme şartı sağlanmadı.**
- Rastgele bahsin beklenen CLV'si −%4,0. Model sinyali bunu 1,2 puan iyileştiriyor, ama marjı aşmak için kabaca 3–4 kat güçlü olması gerekirdi.

## 6. Neden yenemedik?

1. **Erken oranlar zaten çok isabetli.** Premier League'de kapanış oranı, erken orana göre log-loss'u sezon başına yalnızca 0,000–0,009 iyileştiriyor. Cuma'dan sonra piyasaya giren bilgi az, dolayısıyla yakalanacak hata da az.
2. **Model, piyasanın bilmediği bir şeyi bilmiyor.** Gol ve xG gibi herkese açık geçmiş veriler, oranlara zaten yansımış durumda. Modelin piyasadan sapmaları büyük ölçüde gürültü.
3. **Marj, küçük sinyalden büyük.** Belçika'daki gerçek sinyal bile %4'lük marjın altında kaldı. Daha az verimli liglerde marj da yükseliyor; iki etki birbirini dengeliyor.
4. **Piyasanın sonradan öğrendiği bilgi** (kadro, sakatlık, son dakika haberi) karar anında, Cuma günü, henüz yok. Bu bilgiyi kullanmak, karar anını maça yaklaştırmayı ve o anın tarihli fiyatlarını gerektiriyor. Elimizde böyle tarihsel fiyat yok.

## 7. Ne kaldı, ne korunuyor?

**Kilitli final setler.** Premier League ve Belçika'nın 2023/24–2024/25 sezonları hiç açılmadı. Belçika'nın bu sezonları indirilmedi bile. Final set açılışları veritabanında lig başına tek seferlik kaydediliyor ve kod ikinci açılışı reddediyor (#42, `final_set_runs`).

**Altyapı yeniden kullanılabilir:**
- Veri sürümleme, lig bazlı yükleme, walk-forward model, metrikler, hareket testi, backtest motoru.
- 53 test.
- Bütün raporlar tek komutla yeniden üretilebiliyor (README).

**Test edilmeyenler:**
- Katman 2 (İddaa oranları): İddaa kayıt şablonu ve yalnızca eklemeye izin veren tablo hazır, ama hiç veri girilmedi.
- Faz 5 ek verileri.
- Faz 6 canlı test.
- Alt/üst pazarı.

## 8. İleride devam edilirse

Bunlar öneri; yeni bir ön kayıt olmadan uygulanmamalı.

- **Belçika beraberlik hipotezi.** Bu sonradan bulunmuş bir alt grup, karar #19 seçim dönemi verisiyle peşine düşmeyi yasaklıyor. Önceden kayda alınıp yalnızca yeni veriyle, yani canlı testte sınanabilir.
- **İleriye dönük kayıt.** Kadro ve sakatlık bilgisini yayın saatiyle, aynı anın fiyatlarıyla birlikte kaydetmek. Asıl zorluk, tarihli oran için yasal ve erişilebilir bir kaynak bulmak; Pinnacle'ın genel API'si 2025'te kapandı.
- **Kilitli final setler** yalnızca bu adımlarla seçim döneminde geçme şartını sağlayan bir model için açılmalı.

## 9. Sınırlamalar

- Her ligde değerlendirme üç sezonla sınırlı. 2019/20 ısınma sezonu oldu, çünkü elimizde daha eski veri yoktu.
- Erken oran zamanı dakika hassasiyetinde değil; football-data'nın genel toplama saatine dayanıyor (#6).
- Yalnızca 1-X-2 pazarı ve yalnızca Pinnacle tabanlı CLV test edildi.
- Lig taramasında yalnızca iki lig seçildi. Üçüncü sıradaki Süper Lig ve diğer adaylar modellenmedi.
- Her şey Pinnacle'ın erişilebilir olduğu döneme dayanıyor. 2026 sonrası için aynı ölçüm altyapısı daha zayıf bir kıyas oranıyla çalışmak zorunda.

## Raporlar

| Konu | Dosya |
| --- | --- |
| Veri kalitesi | `reports/veri_kalite.md` |
| N hesabı | `reports/n_hedefi.md` |
| Faz 2 | `reports/faz2_poisson.md` |
| Faz 3 | `reports/faz3_model.md`, `reports/faz3_yeni_cikan.md` |
| Faz 4, Premier League | `reports/faz4_secim.md`, `reports/faz4_secim.json` |
| Lig taraması | `reports/lig_taramasi.md` |
| Belçika ve Hollanda | `reports/lig_B1.md`, `reports/lig_N1.md` |
| Faz 4, Belçika | `reports/faz4_secim_B1.md`, `reports/faz4_secim_B1.json` |
