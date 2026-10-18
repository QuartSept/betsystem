# Futbol Bahis Analiz Sistemi – Yol Planı (Sürüm 2)

Oct 18, 2026 · @Can

## Amaç ve temel ilke

Sistem "hangi kupon tutar" sorusunu değil, "bahis şirketi oranı nerede yanlış koymuş" sorusunu cevaplar. Kişisel kullanım içindir ve tamamen yerel bilgisayarda çalışır.

- **Oran zaten bilgi içerir.** Geçmiş veri, puan durumu ve haberler orana yansımıştır; üstüne şirketin kâr payı (marj) eklenir.
- **Kombine kupon oynanmaz.** Her maçın marjı çarpılarak büyür.
- **Lig:** Premier League ile başlanır; veri en zengin, ama oranlar en isabetli olduğu piyasa. Sistem oturunca La Liga ve daha az takip edilen ligler eklenir.
- **İki katmanlı doğrulama:** (1) Model uluslararası piyasayı yeniyor mu? (2) Türkiye'de yasal olarak erişilebilen oranlarda da avantaj var mı? Gerçek bahis için ikisi birden gerekir.
- **Model ve strateji ayrımı:** Model başarılı olup yasal oranlarda avantaj bulunamazsa sonuç "model başarılı, strateji doğrulanamadı" olur.
- **Tahmin zorlanmaz:** Avantaj bulunmayan haftalarda sistemin çıktısı "bu hafta uygun fırsat yok" olur.

&#91;embedded content: yol haritası · 8 faz, 7 geçme şartı\]

En kritik kapı Faz 4: geriye dönük testte kapanış oranı tutarlı şekilde yenilmiyorsa sonraki fazlara geçilmez.

## Faz 0 – Kurallar (donduruldu)

Faz 0 kararları 18 Ekim 2026'da onaylandı ve donduruldu. Faz 7'ye kadar gerçek para kullanılmaz.

| Konu | Karar |
| --- | --- |
| Karar anı | football-data'nın erken oran saati: hafta sonu maçları için Cuma öğleden sonra, hafta içi maçlar için Salı. Başlangıç referansıdır; kesin zaman damgası olmadığı için dakika hassasiyetinde fiyat sayılmaz. |
| Kıyas oranı | 2024/25'e kadar Pinnacle kapanış oranı; 2025/26 ve sonrası marjı çıkarılmış piyasa ortalaması kapanış oranı. |
| Veri bölümü | Model seçimi: 2019/20–2022/23. Kilitli final test: 2023/24–2024/25. |
| Pazar | Sadece 1-X-2. |
| Bahis miktarı | Sabit 1 sanal birim. Kelly yalnızca karşılaştırma stratejisi olarak test edilir. |
| Bahis fiyatı | Ana fiyat Pinnacle erken oranı (araştırma fiyatı; Türkiye'den yasal olarak oynanamaz, uygulanabilirlik katman 2'de İddaa ile test edilir). B365 erken oranı duyarlılık testi olarak ayrıca raporlanır. Max erken oranı kararlarda kullanılmaz, en fazla "teorik üst sınır" dipnotu olur. |
| Eksik fiyat | Pinnacle erken oranı eksik maçta bahis yapılmaz; başka şirketin oranıyla doldurulmaz. Eksiklik oranı kalite raporunda gösterilir. |
| Yerel oranlar | İddaa oranları bu sezondan itibaren tarihli olarak kaydedilir. |

**Teknik düzeltmeler**

- Tarihsel erken oran testi ile gerçek zamanlı uygulanabilirlik testi ayrı değerlendirilir.
- 2024/25 ve öncesindeki Pinnacle verisinin güvenilirliği, Faz 1'de sezon ve sütun bazında doğrulanana kadar varsayımdır.
- Pinnacle ve piyasa ortalamasıyla hesaplanan CLV sonuçları ayrı raporlanır; tek kesintisiz performans serisi gibi yorumlanmaz.

**Başarı ölçütleri**

- Ana erken gösterge CLV'dir, ama tek başına başarı kanıtı değildir.
- Birlikte değerlendirilenler: CLV, log-loss ve kalibrasyon, ROI ve güven aralığı.

**Minimum bahis sayısı (N)**

Yöntem burada sabitlenir; sayısal hedef Faz 1'deki veri incelemesinden sonra, yalnızca model seçimi döneminden hesaplanır. Kilitli final test verisi kullanılmaz. Formül, pozitif CLV'yi belirli bir istatistiksel güçle tespit edecek şekilde güç parametresini içerir:

**N = ((z₁₋α + z₁₋β) × σ / δ)²**

- z₁₋α: istenen güven düzeyine karşılık gelen değer
- z₁₋β: istenen istatistiksel güce karşılık gelen değer
- σ: bahis başına CLV'nin standart sapması
- δ: tespit edilmek istenen ortalama CLV

Aynı maça ait bağımlı bahisler tek gözlem sayılır.

## Faz 1 – Veri altyapısı

Önce 2022/23 sezonuyla uçtan uca çalışan bir prototip kurulur; boru hattı doğrulanınca veri 2019/20'den bugüne genişletilir. Model eğitimi için daha eski sezonlar da eklenebilir.

Prototip sezonu model seçimi döneminden seçildi. Kilitli final sezonlarında (2023/24–2024/25) Faz 1'de yalnızca veri kalitesi kontrol edilir (eksik değerler, oran sütunlarının doluluğu); model sonuçlarına veya getirilere bakılmaz.

| Veri | Kaynak | Ne için |
| --- | --- | --- |
| Maç sonuçları, erken ve kapanış oranları | football-data.co.uk (ücretsiz CSV) | Model eğitimi ve piyasa karşılaştırması |
| Gol beklentisi (xG) | Understat, FBref | Takımın gerçek gücünü ölçmek |
| Fikstür ve tarih bilgisi | Aynı kaynaklar | Dinlenme günü, yoğun takvim |
| İddaa oranları (bu sezondan itibaren) | Yöntem bu fazda netleşir | Uygulanabilirlik testi |

- **İzlenebilirlik:** Her oran kaydında kaynak, bahis şirketi, pazar, kayıt zamanı (biliniyorsa) ve veri sürümü tutulur.
- **Veri kalite raporu:** Sezon ve sütun bazında eksik değer oranı, xG kapsama oranı ve Pinnacle oranlarının tutarlılığı.
- **Doğrulama:** Erken oranların toplanma saatleri football-data'nın kendi notlarından kontrol edilir. *18 Ekim 2026'da doğrulandı: notes.txt'ye göre hafta sonu maçlarının oranları Cuma öğleden sonra, hafta içi maçlarınki Salı öğleden sonra toplanır (karar #6 ile uyumlu).*
- **Takım isimleri:** Kaynaklar arası tek bir eşleştirme tablosu ("Man United" / "Manchester United").
- **Kod yapısı:** Veri, model ve test ayrı Python modülleri; Jupyter yalnızca keşif ve raporlama için. Araçlar: Python, pandas, SQLite.
- **Geçme şartı:** Tek sezonluk prototip uçtan uca çalışıyor, veri kalite raporu hazır ve N için sayısal hedef belirlendi.

## Faz 2 – Basit model

İlk model, golleri kullanan bir Poisson modeli. Her takıma bir hücum ve bir savunma gücü atanır; bunlardan maçın 1-X-2 olasılıkları hesaplanır.

- **Piyasa olasılığı:** Oranlar 1/oran ile olasılığa çevrilir, toplamı 100'ü aşan kısım (marj) çıkarılır.
- **Karşılaştırma çıtası:** Marjı çıkarılmış piyasa olasılıklarının kendisi. Model bu çıtaya göre ölçülür.
- **Ölçüm:** Aynı maçlarda log-loss, Brier skoru ve kalibrasyon.
- **Beklenti:** Piyasa muhtemelen daha iyi çıkacak. Bu normal; amaç aradaki farkı sayıyla görmek.
- **Geçme şartı:** Ölçüm altyapısı çalışıyor, modelin piyasaya göre konumu biliniyor.
- **Sonuç (18 Ekim 2026):** 2020/21–2022/23'teki 1.140 maçta Poisson log-loss 0,998, Pinnacle erken 0,970, Pinnacle kapanış 0,965. Model piyasadan anlamlı ölçüde kötü (fark +0,029, %95 GA 0,017–0,040), geçmiş sıklık tahmininden anlamlı ölçüde iyi (−0,070). Uç olasılıklarda aşırı güvenli. Ayrıntı: `reports/faz2_poisson.md`.

## Faz 3 – Gelişmiş model

Basit model üç yönde geliştirilir; her değişiklik yalnızca model seçimi döneminde (2019/20–2022/23) test edilir.

1. **Dixon-Coles düzeltmesi:** Poisson'un düşük skorlu maçlardaki (0-0, 1-0, 1-1) hatasını düzeltir.
2. **Zaman ağırlığı:** Yakın tarihli maçlar daha fazla etkiler; ağırlık katsayısı testle seçilir.
3. **xG kullanımı:** Takım gücü gerçek goller yerine gol beklentisiyle (veya ikisinin karışımıyla) hesaplanır.

- **Alt gruplar:** Belirli maç gruplarında avantaj aranacaksa grup önceden tanımlanır ve final sette ayrıca tutması gerekir. Sonradan bulunan alt gruplar kabul edilmez.
- **Pazar:** Alt/üst 2.5, 1-X-2 sistemi doğrulandıktan sonra eklenir.
- **Geçme şartı:** Olasılıklar iyi kalibre edilmiş ve her değişikliğin doğrulama dönemindeki katkısı ayrı ayrı ölçülmüş.
- **Sonuç (18 Ekim 2026):** Ayarlar 2020/21–2021/22'de seçildi, 2022/23 iç kontrol. Dixon-Coles log-loss'u kötüleştirdi (+0,0013) ve elendi. Zaman ağırlığı (ξ = 0,001/gün, yarı ömür ≈ 2 yıl) ve xG (hedefin yarısı xG) tutuldu. Faz 3 modeli Faz 2'ye göre ayar sezonlarında 0,006, iç kontrolde 0,010 daha iyi. Tek tek adımların güven aralıkları çoğunlukla sıfırı içeriyor. ECE 0,0195 (Pinnacle erken 0,0242). Piyasaya göre fark +0,021 (%95 GA 0,011–0,032): model hâlâ Pinnacle erken oranından anlamlı ölçüde kötü. Ayrıntı: `reports/faz3_model.md`.
- **Ek deneme (karar #36–#37):** Önceden tanımlanan yeni çıkan takım ayarı aynı protokolle test edildi ve elendi. Ayrıntı: `reports/faz3_yeni_cikan.md`.

## Faz 4 – Geriye dönük test

Model, 2019/20–2022/23 döneminde her maçı sanki o gün oynanıyormuş gibi, yalnızca karar anına kadarki veriyle tahmin eder (walk-forward test). Kilitli final set (2023/24–2024/25) en sonda, tek seferde ve hiçbir ayar değiştirilmeden çalıştırılır.

- **Bahis kuralı:** Model olasılığı × oran − 1 değeri önceden belirlenen eşiğin üstündeyse sanal bahis yapılır. Eşik yalnızca model seçimi döneminde seçilir.
- **Bahis miktarı:** Sabit 1 birim. Çeyrek Kelly ayrı bir strateji olarak karşılaştırılır.
- **Ölçülenler:** CLV (güven aralığıyla), log-loss ve kalibrasyon, ROI ve güven aralığı, en büyük düşüş, dönemler arası tutarlılık.
- **Gerçekçi fiyat:** Bahis yalnızca erken oran üzerinden yapılmış sayılır; erken ile kapanış arasındaki fiyatlar varsayılmaz.
- **Geçme şartı:** En az N bağımsız bahiste CLV pozitif ve güven aralığı sıfırın üstünde; sonuç kilitli final sette de tutarlı. Kâr var ama CLV negatifse büyük ihtimalle şanstır.

**Final set tek kullanımlıktır.** 2023/24–2024/25 açıldıktan sonra bu veri yeni değişken, parametre veya eşik seçmek için bir daha kullanılmaz. Sonraki model değişikliklerinin bağımsız doğrulaması Faz 6 canlı testinde yapılır.

## Faz 5 – Ek veriler

Haber ve sosyal medya fikri burada devreye girer, ama duygu puanı olarak değil, doğrulanabilir bilgi olarak. Kolay doğrulanabilen değişkenlerle başlanır.

- **İlk aşama:** Dinlenme günü, fikstür yoğunluğu, Avrupa kupası maçları, hoca değişikliği. Bunların tarihsel verisi güvenilir biçimde bulunabilir.
- **İkinci aşama:** Sakat ve cezalı oyuncular, kesinleşmiş kadrolar. Bu bilgilerin geçmişteki yayın saatleriyle birlikte bulunması pratikte çok zor; bu yüzden bugünden itibaren yayın saatiyle birlikte biz kaydederiz.
- **Yapay zekanın rolü:** Haberlerden bu bilgileri yapılandırılmış biçimde çıkarmak ("X oyuncusu sakat, maçı kaçıracak").
- **Kural:** Her değişkenin katkısı ayrı ayrı, yalnızca model seçimi döneminde test edilir; iyileştirmeyen değişken çıkarılır. Final set Faz 4'te açıldığı için güncellenen model Faz 6 canlı testinde doğrulanır.

## Faz 6 – Canlı kâğıt testi

Sistem gerçek zamanlı çalışır ama para yatırılmaz. Süre takvimle değil, bahis sayısıyla belirlenir: test, N bağımsız bahise ulaşana kadar sürer.

- Her karar anında tahminler üretilir; önerilen bahisler, uluslararası oran ve İddaa oranı birlikte kaydedilir.
- Kayıtlar yalnızca eklenir, sonradan değiştirilmez.
- Maç sonrası kapanış oranı ve sonuç eklenir. Bu dönemde CLV piyasa ortalamasına göre hesaplanır ve Faz 4 sonuçlarından ayrı raporlanır.
- Veri gecikmesi ve modelin hafta hafta kararlılığı izlenir.
- **Açık konu:** football-data verisinde Pinnacle oranları 17 Ocak 2026'dan beri yok. Canlı testte ana bahis fiyatı (karar #24) bulunamayacağı için hangi fiyatın kullanılacağı Faz 6 öncesinde karara bağlanır.
- **Geçme şartı:** Canlı sonuçlar Faz 4 ile uyumlu. Büyük fark varsa testte bir hata (örneğin veri sızıntısı) aranır.

## Faz 7 – Karar

Karar, önceden yazılmış bu kurallarla verilir; sonuçları gördükten sonra kurallar değiştirilmez.

| Katman 1: Model piyasayı yeniyor mu? | Katman 2: Yasal oranlarda avantaj var mı? | Karar |
| --- | --- | --- |
| Evet | Evet | Küçük, önceden belirlenmiş ve sonradan artırılmayan bir kasayla başla |
| Evet | Hayır | Model başarılı, strateji doğrulanamadı; para yok, başka lig veya pazar değerlendirilir |
| Hayır | – | Durdur ya da modele geri dön |

- Gerçek parayla başlanırsa aylık değerlendirme yapılır; CLV pozitif kalmazsa bahis durdurulur.
- "Piyasa bizden iyi" sonucu da değerli bir sonuçtur.

## Karar kaydı

Projede bugüne kadar alınan tüm kararlar; hepsi 18 Ekim 2026'da kesinleşti. Yeni kararlar bu tabloya eklenir.

| # | Karar | Bölüm |
| --- | --- | --- |
| 1 | Amaç kupon tahmini değil, oranın yanlış konduğu yerleri bulmak (value bet) | Amaç |
| 2 | Kombine kupon oynanmaz | Amaç |
| 3 | Premier League ile başlanır; sonra La Liga ve daha az takip edilen ligler | Amaç |
| 4 | Sistem kişisel kullanım için ve tamamen yerel bilgisayarda çalışır | Amaç |
| 5 | İki katmanlı doğrulama: model piyasayı yenmeli ve yasal oranlarda avantaj olmalı | Amaç, Faz 7 |
| 6 | Karar anı: football-data erken oran saati (Cuma öğleden sonra / Salı); başlangıç referansı, dakika hassasiyetinde fiyat değil | Faz 0 |
| 7 | Kıyas oranı: 2024/25'e kadar Pinnacle kapanış, sonrası marjı çıkarılmış piyasa ortalaması | Faz 0 |
| 8 | İki kıyas oranıyla hesaplanan CLV ayrı raporlanır | Faz 0 |
| 9 | Veri bölümü: model seçimi 2019/20–2022/23, kilitli final test 2023/24–2024/25 | Faz 0 |
| 10 | Pazar: sadece 1-X-2; alt/üst 2.5 sonra | Faz 0, Faz 3 |
| 11 | Bahis miktarı: sabit 1 sanal birim; Kelly yalnızca karşılaştırma için | Faz 0 |
| 12 | İddaa oranları bu sezondan itibaren tarihli kaydedilir | Faz 0 |
| 13 | Tarihsel erken oran testi ile gerçek zamanlı uygulanabilirlik testi ayrı değerlendirilir | Faz 0 |
| 14 | Minimum bahis sayısı güç parametresini içeren formülle, model seçimi döneminden hesaplanır | Faz 0 |
| 15 | Prototip sezonu 2022/23; final sezonlarında Faz 1'de yalnızca veri kalitesi kontrolü | Faz 1 |
| 16 | Pinnacle verisi sezon ve sütun bazında doğrulanana kadar varsayımdır | Faz 1 |
| 17 | Araçlar: Python, pandas, SQLite; ayrı modüller, Jupyter yalnızca keşif ve raporlama | Faz 1 |
| 18 | Streamlit arayüzü Faz 4 sonrasına ertelendi | Faz 1 |
| 19 | Alt gruplar önceden tanımlanır ve final sette de tutmalıdır | Faz 3 |
| 20 | Final set tek kullanımlıktır; sonraki değişiklikler Faz 6'da doğrulanır | Faz 4, Faz 5 |
| 21 | Ek verilerde önce dinlenme günü ve fikstür; sakatlık ve kadro verisi bugünden kaydedilir | Faz 5 |
| 22 | Canlı testin süresi takvimle değil, bahis sayısıyla belirlenir | Faz 6 |
| 23 | Çalışma düzeni: kodlamayı proje sahibi yapar; Claude ve ChatGPT beyin fırtınası ve inceleme için kullanılır | Genel |
| 24 | Ana bahis fiyatı Pinnacle erken oranı; erken ve kapanış aynı şirketten geldiği için CLV temiz ölçülür. Araştırma fiyatıdır, yasal uygulanabilirlik katman 2'de test edilir | Faz 0, Faz 4 |
| 25 | B365 erken oranı duyarlılık testi olarak ayrıca raporlanır; ana fiyat değildir | Faz 4 |
| 26 | Max erken oranı kararlarda kullanılmaz; modelsiz en iyi fiyat seçimi bile pozitif CLV üretir (2022/23: +%1,8). En fazla teorik üst sınır dipnotu | Faz 4 |
| 27 | Pinnacle erken oranı eksik maçta bahis yapılmaz, başka şirketle doldurulmaz; eksiklik oranı kalite raporunda izlenir. Eksiklik yüksek ve rastgele değilse karar yeniden konuşulur | Faz 1, Faz 4 |
| 28 | N, Pinnacle erken fiyatı üzerinden model seçimi döneminde (2019/20–2022/23) hesaplanır | Faz 1 |
| 29 | Karar #23 güncellendi: Claude kodu doğrudan yazar | Genel |
| 30 | N hedefi: δ = %1,5, α = 0,05 (tek yönlü), güç = 0,80, σ = 0,0856 (Pinnacle erken, 2019/20–2022/23, 1.520 maç) ile **N = 202** bağımsız bahis | Faz 0, Faz 1 |
| 31 | Karar günü kuralı: Cuma–Pazartesi maçları için en yakın önceki Cuma, Salı–Perşembe maçları için en yakın önceki Salı. Model yalnızca karar gününden önce oynanmış maçları görür | Faz 2 |
| 32 | Değerlendirmeye yalnızca modelin en az 380 eğitim maçı gördüğü maçlar girer; 2019/20 ısınma sezonu olarak kalır (2017/18–2018/19 eklenirse değerlendirmeye girer) | Faz 2 |
| 33 | Faz 3 protokolü: ayarlar yalnızca 2020/21–2021/22'de seçilir, 2022/23 iç kontrol olarak raporlanır; her adımda önceki model de aday olur, iyileştirmeyen değişiklik elenir | Faz 3 |
| 34 | Dixon-Coles elendi (ayar sezonlarında log-loss +0,0013) | Faz 3 |
| 35 | Faz 3 modeli: Poisson, L2 = 1, tüm geçmiş, zaman ağırlığı ξ = 0,001/gün, hedef = 0,5·gol + 0,5·xG. Faz 4'e bu modelle girilir | Faz 3 |
| 36 | Yeni çıkan takım ayarı (ön kayıt, sonuç görülmeden tanımlandı): bir takım, bir önceki sezon veride Premier League'de yoksa o sezon boyunca "yeni çıkan" sayılır. Modele iki ek parametre eklenir: yeni çıkan takımın hücumuna ve savunmasına sabit kayma (cezasız, eğitim penceresindeki yeni çıkan takımlardan öğrenilir). Elle seçilen sayı veya ızgara yoktur. Aday, Faz 3 modeline eklenir ve karar #33 protokolüyle değerlendirilir: ayar sezonlarında (2020/21–2021/22) log-loss düşürmezse elenir. Tanı amaçlı ayrıca yeni çıkan takımın oynadığı maçlarda fark raporlanır; bu alt grup bahis için kullanılmaz | Faz 3 |
| 37 | Karar #36 sonucu: yeni çıkan takım ayarı **elendi**. Ayar sezonlarında log-loss +0,0029 (%95 GA −0,0000…0,0062), iç kontrolde +0,0011; bozulma yeni çıkan takımların maçlarında yoğun (+0,0096, n = 216). Öğrenilen kayma sezondan sezona tutarsız (2020/21: −0,22/−0,30; 2021/22: +0,03/+0,01). Ayarın başka biçimleri sonuç görüldükten sonra denenmez (çatallanan yollar); Faz 4'e karar #35'teki modelle girilir | Faz 3 |
| 38 | Faz 4 bahis kuralı (ön kayıt): her maçta model olasılığı × Pinnacle erken oranı − 1 değeri en yüksek olan tek sonuç seçilir; değer eşiğin üstündeyse 1 sanal birim bahis. Maç başına en fazla 1 bahis. Pinnacle erken oranı eksikse bahis yok (karar #27). Model: karar #35 | Faz 4 |
| 39 | CLV (ön kayıt): bahis oranı × marjsız Pinnacle kapanış olasılığı − 1 (marj oransal çıkarılır). ROI: kazanan bahiste oran − 1, kaybedende −1. B365 duyarlılık testi (karar #25): aynı kural B365 erken oranıyla bahis seçip B365 oranından CLV hesaplanır, ayrı raporlanır | Faz 4 |
| 40 | Eşik seçimi (ön kayıt): ızgara {0; 0,01; 0,02; 0,03; 0,05; 0,075; 0,10}. Seçim dönemi 2020/21–2022/23 (2019/20 ısınma, karar #32). En az 202 bahis veren eşikler arasında ortalama CLV'si en yüksek olan seçilir; hiçbiri 202'ye ulaşmazsa en çok bahis veren (en düşük) eşik seçilir | Faz 4 |
| 41 | Güven aralıkları (ön kayıt): bahisler üzerinden bootstrap (5.000 örnek, sabit tohum). Geçme şartındaki alt sınır tek yönlü %95 (5. yüzdelik), N hesabıyla (karar #30) tutarlı; iki yönlü %95 aralık da raporlanır. Çeyrek Kelly: başlangıç kasası 100 birim, pay = 0,25 × (p·o − 1)/(o − 1), bileşik, aynı bahisler | Faz 4 |
| 42 | Faz 4 geçme şartı (ön kayıt): seçim döneminde seçilen eşikte en az 202 bahis, ortalama CLV > 0 ve alt sınır > 0; kilitli final sette aynı eşik ve modelle en az 202 bahis, ortalama CLV > 0 ve alt sınır > 0. Final set tek seferlik çalıştırılır, kod ikinci çalıştırmayı reddeder; açmadan önce proje sahibinin onayı alınır | Faz 4 |

## Riskler ve gerçekçi beklentiler

Bu tür sistemleri kuranların büyük çoğunluğu piyasayı uzun vadede yenemiyor; plan, bunu erken ve ucuza öğrenmek üzerine kurulu.

- **Verimli piyasa:** Premier League oranları çok isabetli; avantaj daha çok küçük liglerde ve niş pazarlarda bulunur.
- **Kıyas verisi:** Pinnacle'ın genel API erişimi 23 Temmuz 2025'te kapandı. 2025/26 sonrası kıyas oranı daha az keskin olacak.
- **Yerel oran marjı:** İddaa'nın marjı uluslararası keskin şirketlerden genelde yüksek; uluslararası piyasada bulunan avantaj yasal oranlarda kaybolabilir.
- **Yasal çerçeve:** Türkiye'de yasal seçenek İddaa ve lisanslı sitelerdir; yabancı bahis siteleri yasa dışıdır.
- **Hesap limitleri:** Sürekli kazanan hesaplar sıklıkla limitlenir.
- **Aşırı uyum:** Çok fazla değişken veya alt grup denemek, geçmişte harika, gelecekte kötü sonuç veren bir model üretir. Kilitli final set buna karşı korumadır.
- **Bağımlılık riski:** Kayıpları kovalamamak için kasa ve kurallar önceden yazılır ve değiştirilmez.

**Sonraki adım:** Faz 4 – geriye dönük test (eşik seçimi, CLV, ROI, kilitli final set).

- [x] Faz 0: Kurallar (donduruldu)
- [x] Faz 1: Veri altyapısı
- [x] Faz 2: Basit model
- [x] Faz 3: Gelişmiş model
- [ ] Faz 4: Geriye dönük test
- [ ] Faz 5: Ek veriler
- [ ] Faz 6: Canlı kâğıt testi
- [ ] Faz 7: Karar

## Kaynaklar

- [Pinnacle API dokümantasyonu](https://github.com/pinnacleapi/pinnacleapi-documentation): genel API erişiminin 23 Temmuz 2025'te kapanması
- [football-data.co.uk](https://football-data.co.uk/): maç sonuçları, erken ve kapanış oranları
