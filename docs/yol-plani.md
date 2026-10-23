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

- **Seçim dönemi sonucu (18 Ekim 2026):** Geçme şartı sağlanmadı (karar #43). Ayrıntı: `reports/faz4_secim.md`.

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
- **Karar (18 Ekim 2026, karar #53):** Katman 1 sonucu **Hayır**: model piyasayı yenmiyor. Premier League (karar #43) ve Belçika (karar #52) seçim dönemlerinde CLV negatif; Hollanda hareket testini geçemedi (karar #50). Tablonun kuralı uygulanır: **durdurulur**. Katman 2 (İddaa) test edilmedi, gerçek para kullanılmaz. Kilitli final setleri açılmadı ve kilitli kalır. Ayrıntılı özet: `reports/sonuc_raporu.md`.

## Karar kaydı

Projede bugüne kadar alınan tüm kararlar; hepsi 18 Ekim 2026'da kesinleşti. Yeni kararlar bu tabloya eklenir. #54–#76 Aşama 2 kararlarıdır; gerekçeleri `docs/yol-plani-v2.md`'de.

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
| 43 | Faz 4 seçim dönemi sonucu: geçme şartı **sağlanmadı**. Seçilen eşik 0,10 (778 bahis): ortalama CLV −0,0171 (tek yönlü alt sınır −0,0242), ROI −0,025. Tüm eşiklerde CLV −0,017…−0,019, yani rastgele seçimin beklenen değeri (marj) düzeyinde. Üç sezonun hepsinde negatif. B365 duyarlılığı da negatif (−0,0346). Kilitli final set açılmadı | Faz 4 |
| 44 | Kilitli final set (2023/24–2024/25) açılmadı ve kilitli kalır; seçim döneminde geçemeyen model için harcanmaz. Faz 7 kuralı uygulanır: modele geri dönülür | Faz 4, Faz 7 |
| 45 | Hareket teşhisi (seçim dönemi, bilgi amaçlı): modelin erken orandan sapması (logit) ile erken→kapanış hareketi arasında korelasyon H −0,02, X +0,07, A −0,005. Model sapmaları piyasanın sonradan öğrendiği bilgiyi taşımıyor. Premier League'de kapanış oranı erkene göre log-loss'u yalnızca 0,000–0,009 iyileştiriyor: Cuma'dan sonra piyasaya az bilgi giriyor | Faz 4 |
| 46 | Hareket testi (ön kayıt): her maç ve sonuç için x = logit(model) − logit(marjsız Pinnacle erken), y = logit(marjsız Pinnacle kapanış) − logit(marjsız Pinnacle erken). Üç sonuç birlikte, y'nin x'e regresyon eğimi hesaplanır; güven aralığı maçlar yeniden örneklenerek bootstrap ile (5.000 örnek, sabit tohum) bulunur. Geçme: eğim > 0 ve tek yönlü %95 alt sınır > 0. Sonuç bazında eğim ve korelasyon yalnızca bilgi olarak raporlanır. Yeni bir lig, model veya değişken, Faz 4 backtest'ine ancak seçim döneminde bu testi geçerse girer | Faz 3, Faz 4, Faz 5 |
| 47 | Lig taraması (ön kayıt): adaylar, football-data sezon paketlerindeki (data.zip) Premier League dışı tüm ligler. Yalnızca 2019/20–2022/23 kullanılır, model kurulmaz. Uygunluk: dört sezonda Pinnacle erken ve kapanış oranı birlikte dolu en az 900 maç ve doluluk ≥ %90. Sıralama ölçütü bilgi kazancı = log-loss(marjsız Pinnacle erken) − log-loss(marjsız Pinnacle kapanış), maç başına ortalama; bootstrap güven aralığıyla raporlanır. Uygun ligler arasında bilgi kazancı en yüksek iki lig seçilir. Marj, maç sayısı ve Understat xG varlığı yalnızca bilgi olarak raporlanır, seçimi değiştirmez | Amaç, Faz 1 |
| 48 | Yeni lig protokolü (ön kayıt): seçilen liglerde Premier League ile aynı bölüm ve kurallar uygulanır. 2019/20 ısınma, 2020/21–2022/23 seçim dönemi, 2023/24–2024/25 o ligin kilitli final seti. Model önce Faz 2 (gol) ve Faz 3 protokolüyle (karar #33) kurulur; xG yalnızca Understat'ın kapsadığı liglerde denenir. Ardından hareket testi (karar #46), geçerse Faz 4 kuralları (karar #38–#42) uygulanır. N, o ligin Pinnacle erken σ'sı ve δ = %1,5 ile yeniden hesaplanır | Faz 2–4 |
| 49 | Lig taraması sonucu (karar #47 kuralıyla): seçilen ligler **B1 Belçika Pro League** (bilgi kazancı 0,0087, %95 GA 0,0036…0,0137) ve **N1 Hollanda Eredivisie** (0,0075, 0,0030…0,0122). Premier League 0,0031. En yüksek değer Yunanistan'da (0,0105) ama 696 maçla uygunluk eşiğinin altında. Üçüncü sıradaki uygun lig Türkiye Süper Lig (0,0058). İki seçilen ligde de Understat xG yok: model gollerle kurulur. Erken marj B1'de %4,1, N1'de %3,3 (Premier League %2,7). Premier League Faz 3 modeli hareket testini geçemedi (eğim 0,0014, alt sınır −0,0178) | Amaç, Faz 1 |
| 50 | Yeni lig sonuçları (karar #48): **B1** Faz 3 modeli Poisson + zaman ağırlığı (ξ = 0,003), Dixon-Coles elendi; PS erkene göre log-loss +0,016 (%95 GA 0,004…0,027). Hareket testi **geçti**: eğim 0,047 (alt sınır 0,018). Eğim üç sezonda da pozitif (0,010; 0,062; 0,091), en güçlü olduğu yer iç kontrol sezonu 2022/23; en çok beraberlikte (eğim 0,118). **N1** Faz 3 modeli Poisson + Dixon-Coles, zaman ağırlığı elendi; PS erkene göre +0,022. Hareket testi **geçemedi**: eğim 0,010 (alt sınır −0,016). N1 için çalışma durur | Faz 2–4 |
| 51 | B1 için N (karar #48 yöntemiyle, 2019/20–2022/23, Pinnacle erken, δ = %1,5): σ = 0,0995, **N = 273**. Rastgele bahsin beklenen CLV'si −%4,0 (Premier League −%1,9) | Faz 4 |
| 52 | B1 Faz 4 seçim dönemi sonucu (karar #38–#42, N = 273): geçme şartı **sağlanmadı**. Seçilen eşik 0,10, 479 bahis: ortalama CLV −0,0284 (tek yönlü alt sınır −0,0377), ROI −0,002. Üç sezonda da CLV negatif. Rastgele bahsin beklenen CLV'si −0,040: model sinyali CLV'yi yaklaşık 1,2 puan iyileştiriyor ama %4,1'lik erken marjı aşmıyor. B365 duyarlılığı −0,0515. B1 kilitli final seti açılmadı | Faz 4 |
| 53 | Faz 7 kararı: model piyasayı yenmiyor (Katman 1: Hayır). Proje durdurulur; gerçek para yok. Premier League ve Belçika kilitli final setleri (2023/24–2024/25) açılmadı ve kilitli kalır; ileride önceden kaydedilmiş yeni bir model için bağımsız doğrulama verisi olarak saklanır. Sonuç raporu: `reports/sonuc_raporu.md` | Faz 7 |
| 54 | Aşama 2 başladı; olasılık kaynağı marjsız piyasa, model ikincil | Temel ilke |
| 55 | Faz sırası 8 → 12 ve geçme şartları bu plandaki gibi; Faz 9 ve 10 paralel yürüyebilir | Yol haritası |
| 56 | Hedef ligler E0 ve T1; başka lig ancak MBS 1 maç oranı yeterliyse | Faz 8 |
| 57 | MBS 1 olmayan maçta bahis yok; kombine yasağı (#2) korunur | Faz 8, 12 |
| 58 | İddaa oranları yalnızca kullanım koşullarına uygun yöntemle ve yalnızca eklenen tabloya kaydedilir | Faz 8, 9 |
| 59 | Belçika 2022/23 kapanış verisi Faz 8'de kontrol edilir (ön kontrol: gürültüyle uyumlu) | Faz 8 |
| 60 | Panel Streamlit ile kurulur; ana olasılık marjsız piyasa, model bilgi için; eşik altında "fırsat yok"; otomatik bahis yok | Faz 9 |
| 61 | Faz 10 test listesi kapalı: 10a, 10c, 10d (10b #74 ile çıkarıldı) | Faz 10 |
| 62 | Faz 10'daki her nihai karar (hareket testi ve CLV alt sınırı) tek yönlü α = 0,05 / 3 ≈ 0,0167 ile; N de bu α ile hesaplanır (#72 ile güncellendi) | Faz 10 |
| 63 | 10a: ana şirket B365, referans marjsız piyasa ortalaması erken, E0 ve T1 birlikte tek test; bu testte #24 istisnası | Faz 10 |
| 64 | 10d çoğaltma ligleri: T1, F2, I2, E2, E3 | Faz 10 |
| 65 | Faz 11 penceresi 2025/26 ve 2026/27'nin 31 Aralık 2026'ya kadarki maçları; referans BFE (≥ %90 doluluk), yoksa piyasa ortalaması; her fikir bir kez; en erken Ocak 2027 | Faz 11 |
| 66 | Faz 12 kuralı: Cuma/Salı fikstür dosyası güncellemesi karar anı; EV eşiği ve süre #76'daki kuralla | Faz 12 |
| 67 | Faz 12 N'si δ = %1,5 ile, σ Faz 8 kayıtlarından hesaplanıp sabitlenir | Faz 12 |
| 68 | Karar tablosu bu plandaki gibi; modelsiz İddaa kuralında yalnızca Katman 2 aranır | Faz 12 |
| 69 | Kilitli final setler (#44) Aşama 2'de açılmaz | Kurallar |
| 70 | Çalışma düzeni: kararlar ve planlama Claude ile bu planda; kod depoda; her yeni karar önce bu kayda eklenir | Genel |
| 71 | Fizibilite kapısı: Faz 10, 11 ve 12'deki her test, kuralın seçtiği bahislerin CLV'sine ve maç sonuçlarına bakmadan beklenen bahis sayısını N ile karşılaştırır (σ vekili kapanış oranını kullanır; ifade #82 ile düzeltildi); N'nin altındaysa test "yetersiz güç" olarak raporlanır ve sonuç analizi yapılmaz | Fizibilite |
| 72 | α düzeltmesi Faz 10'un tüm nihai kararlarına uygulanır (yalnız hareket testine değil); Faz 11'de α = 0,05 / giren fikir sayısı; Faz 12'de α = 0,05 | Faz 10–12 |
| 73 | 10a modelsiz olduğu için dönemi 2019/20–2022/23 (ısınma yok). Ön fizibilite: N = 361; bahis sayısı k = 0 / 0,01 / 0,02 / 0,03 için 384 / 248 / 181 / 127; yalnızca k = 0 fizibil | Faz 10 |
| 74 | 10b ("piyasa + model birleşimi") çıkarıldı: Belçika eğimiyle (0,047) birleşik olasılığın piyasadan sapması ≈ 0,4 puan, Pinnacle erken marjı %4,1; kural kurgusu gereği bahis üretemez | Faz 10 |
| 75 | #10 değişikliği: alt/üst 2.5, 1-X-2 doğrulanmadan Faz 10'da (10c) tarihsel olarak test edilir; yükleyici alt/üst sütunlarını okuyacak şekilde genişletilir. Canlı kural yalnızca 1-X-2 | Faz 10 |
| 76 | Faz 12 zamanlaması ve eşik: referans, fikstür dosyasının haftalık güncellemesinden sonraki ilk indirme (sha ve zaman kaydedilir), İddaa kaydı bu andan en çok ±2 saat; e ∈ {%2; %1; %0} içinden öngörülen bahis sayısının N'ye en çok iki sezonda ulaştığı en büyük değer; hiçbiri ulaşmazsa Faz 12 test olarak yapılmaz | Faz 12 |
| 77 | Faz 10 ön kayıtları sonuçlardan önce commit edildi: 10a `docs/on-kayit/faz10_10a.md` (3a4f8d2; N = 361, yalnız k = 0 fizibil), 10c `faz10_10c.md` (03c39d1; N = 155, tüm eşikler fizibil), 10d `faz10_10d.md` (1ade138; N = 111, tüm eşikler fizibil, sayılar Faz 2 modeliyle yaklaşık). Alt/üst oranları yükleyiciye eklendi (93a3ab0) | Faz 10 |
| 78 | Faz 10 sonuçları (`reports/faz10_sonuclar.md`): **10a geçti** (k = 0, 384 bahis, ortalama CLV +0,0391, tek yönlü alt sınır +0,0239; sekiz lig-sezonun hepsinde pozitif). Sonradan yapılan tanı: Shin ve power marj çıkarma yöntemleriyle CLV +0,0149 / +0,0062 ve alt sınır sıfırın altında; etki kısmen oransal yöntem varsayımından kaynaklanıyor olabilir. **10c geçmedi:** hareket testi geçti (eğim 0,063; B1'de 0,088, E0'da 0,015), CLV −0,0205. **10d geçmedi:** beraberlik hareket etkisi beş ligin beşinde tekrarlandı (birleşik eğim 0,057, alt sınır 0,043), CLV −0,0218. Faz 11'e yalnızca 10a gider; Faz 11 kullanıcı onayı beklenir | Faz 10 |
| 79 | Tek İddaa şablonu: `templates/iddaa_kayit_sablonu.xlsx` (Excel; Türkçe Excel'de CSV'nin ondalık virgül sorunu nedeniyle). CSV şablonu kaldırıldı. Takım adları football-data yazımıyla girilir ve her satır, `fikstur_dosyasi` sütunundaki referans fikstür dosyasında birebir bulunan bir maçla eşleşmek zorundadır. `iddaa_odds_log`'a `league`, `mbs` ve `fixtures_version_id` (referans fikstür dosyasının veri sürümü) eklendi; `data_version_id` kaydın geldiği Excel dosyasıdır. Kayıt zamanı Türkiye saati (+03:00). Hatalı satır varsa dosyanın hiçbir satırı yazılmaz. Fikstür indirmesinden 2 saatten uzak kayıt uyarıyla kaydedilir; #76 kuralı analizde uygulanır | Faz 8, 9, 12 |
| 80 | Fikstür sürümleme: her indirilen fixtures.csv `betsistem import-fixtures` ile içerik olarak `data_versions`'a (sha256), indirme olarak `fixture_downloads`'a (dosya adı, indirme zamanı) eklenir. Aynı içerik tek sürümdür, her indirme ayrı satırdır. 8.4'teki Cuma güncelleme saati `betsistem fixtures-log`'daki ardışık sha değişimlerinden okunur | Faz 8, 12 |
| 81 | Faz 11 penceresi şimdiden kilitli: 2025/26 ve 2026/27 sezonlarının tamamı (pencere 31 Aralık 2026'da bitse de ihtiyaten tüm sezon). Sonuç, CLV veya kural çıktısı üreten kod yolları (`assert_unlocked`) Faz 11 izni ister; izin fikir başına bir kez `faz11_runs`'a kaydedilerek verilir ve ikinci açılışı kod reddeder. 8.5 için yalnızca doluluk ölçülür (`window_coverage`); kalite raporundaki Pinnacle marj ve hareket istatistikleri pencereyi dışarıda bırakır | Faz 8, 11 |
| 82 | #71'in ifadesi düzeltildi: fizibilite, "kapanışa bakmadan" değil, "kuralın seçtiği bahislerin CLV'sine ve sonuçlara bakmadan" yapılır; σ vekili kapanış oranını kullanır | Fizibilite |
| 83 | Faz 10 testleri birer kez çalıştırıldı (2026-10-18 17:24 UTC, çalıştırıcı c41520b, sonuçlar 5e1e824); üçü de raporlandı. Çalıştırma `faz10_runs`'a kayıtlı, ikinci çalıştırmayı kod reddeder. Eşik aynı dönemde seçildiği için geçen sonuç iyimser olabilir (10a'da tek fizibil eşik k = 0 olduğundan seçim etkisi sınırlı; asıl risk #78'deki marj yöntemi duyarlılığı). Faz 11'e kadar hiçbir ayar değiştirilmez; sonuçlar planlamaya getirilir | Faz 10 |
| 84 | Faz 11 / 10a geçme şartı: kural aynen kalır (#83; p_adil Avg erkenden oransal yöntemle, k = 0). CLV hem oransal hem Shin yöntemiyle marjı çıkarılmış kapanışa göre hesaplanır; ikisinin de tek yönlü alt sınırı > 0 olmalı. α = 0,05 (Faz 11'e tek fikir giriyor). Power yöntemi yalnızca bilgi için raporlanır | Faz 11 |
| 85 | #81'e istisna: pencerede yalnızca erken fiyatlarla bahis sayısını saymak (sonuç, kapanış değeri ve CLV olmadan) Faz 11 izni gerektirmez ve izni tüketmez. Çıktı yalnızca sayıdır; oranların kendisi raporlanmaz | Faz 11 |
| 86 | Faz 11 kapsamı (koşullu, şimdiden sabit): önce E0 + T1 için fizibilite yapılır; bahis sayısı N'ye ulaşırsa test E0 + T1 ile yapılır. Ulaşmazsa, pencerede B365 erken, Avg erken ve BFE kapanış doluluğu %90 ve üstü olan tüm football-data ligleriyle yapılır. Bu da yetmezse 10a "yetersiz güç" olarak kapanır ve mekanizma doğrudan Faz 12'de sınanır. Pencerenin bitişi değişmez (#65) | Faz 11 |
| 87 | Kilidin kapsamı: Faz 12 kilitten muaftır. Pencerede kilitli kalanlar: B365'in adil fiyata oranı, bu oranın ürettiği kural çıktıları ve Faz 12 dışındaki tüm sonuç ve CLV istatistikleri. Panel gelecek maçlar için model olasılığını gösterebilir; pencere maçlarında model performansını göstermez | Faz 9, 11, 12 |
| 88 | Faz 12 kuralında p_adil, Avg erkenden Shin yöntemiyle hesaplanır (10a'daki oransal yöntem yanılsaması riskine karşı). Geçme şartı Faz 11'deki gibi: CLV oransal ve Shin yöntemiyle hesaplanır, ikisinin de tek yönlü alt sınırı > 0 | Faz 12 |
| 89 | **Onaylandı (18 Ekim 2026).** Faz 11'in N'si için σ, pencere dışından alınır: 10a kuralının fiyatı (B365 erken) ve seçim dönemindeki Pinnacle kapanışı vekiliyle, 2019/20–2022/23, kapsamdaki liglerde. Gerekçe: v2'deki "σ, pencerenin ilk yarısının fiyatlarından" ifadesi kapanış oranı gerektiriyor; bu, #85 ve #87'ye göre izinsiz hesaplanamaz ve #86'daki sıra (önce fizibilite, sonra kapsam) işlemez. α = 0,05 (#84) | Faz 11 |
| 90 | Veri düzeltmesi: maç anahtarı (lig, sezon, ev, deplasman) aynı eşleşmenin sezonda tekrar oynandığı liglerde ikinci maçı birincinin üzerine yazıyordu (İskoçya SC0–SC3 ve Yunanistan G1 tüm sezonlar, Belçika B1 yalnızca 2025/26 play-off'ları; toplam 1.828 maç). Anahtara eşleşmenin sezondaki sırası (`leg`) eklendi, veriler yeniden yüklendi. Aşama 1'de kullanılan E0, T1, B1 ve N1 (2019/20–2022/23) verisi etkilenmemişti. Lig taraması (#47) aynı kuralla düzeltilmiş veriyle yeniden hesaplandı: seçim değişmedi (B1, N1); G1 artık uygun ama bilgi kazancı 0,0068 ile üçüncü. Faz 11 ön fizibilitesi (#85, #86, #89 önerisiyle): E0 + T1 projeksiyonu 89 bahis < N = 254; 22 uygun lig birlikte projeksiyon 971 ≥ N = 252 → kapsam ön sonucu tüm uygun ligler (`reports/faz11_on_fizibilite.md`) | Veri, Faz 11 |
| 91 | Faz 11 / 10a ön kaydı `docs/on-kayit/faz11_10a.md`: (1) lig listesi 22 lig olarak adıyla sabitlendi; kesin sayımda doluluğu %90'ın altına düşen lig çıkarılır, yeni lig eklenmez; (2) σ yalnızca N'yi belirler, geçme kararı pencerenin kendi bootstrap alt sınırıyla verilir (oransal ve Shin, α = 0,05); (3) karar birleşik veriyle, lig bazında ve E0 + T1 sonuçları yalnızca bilgi; (4) sınırlama: pencerede Avg'ye Pinnacle girmiyor, p_adil seçim dönemine göre değişmiş olabilir; (5) gözlem: bahis sıklığı seçim döneminde %13,1, pencerede E0 %6,6–6,7, T1 %12,1–14,3; kural ve eşik değişmez | Faz 11 |
| 92 | `E01718.csv` ve `E01819.csv` (Premier League 2017/18–2018/19) yüklenmez; dondurulmuş Aşama 1 ve Faz 10 girdileri değişmesin | Veri |
| 93 | Zaman kuralı oranların toplanma anına bağlandı (#76 ve #79'daki "fikstür indirmesinden en çok ±2 saat" kuralının yerine): İddaa kaydı **Cuma 17:00–19:00 Türkiye saati** arasında yapılır (hafta içi maçlar için Salı aynı saatler). Bu aralık İngiltere saatiyle 25 Ekim'e kadar 15:00–17:00, sonrasında 14:00–16:00'ya denk gelir; ikisi de football-data'nın oran toplama zamanı olan öğleden sonranın içindedir. Toplanma saatinin kesin bilinmemesi raporlarda belirsizlik olarak yer alır. Aralık dışındaki kayıt saklanır ama teste girmez | Faz 8, 12 |
| 94 | Fikstür indirmesinde sitedeki "Latest fixtures uploaded" zamanı (İngiltere saati) da kaydedilir. Dosya, yüklendiği günden önceki en yakın Cuma veya Salı'nın oranlarını taşır. İndirme anına göre beklenen toplama gününden önce yüklenmiş dosya (yani yeni yükleme yapılmadan indirilen, önceki haftaya ait dosya) reddedilir. İlk gözlem: 17/10/26 09:35 (İngiltere saati), Cumartesi sabahı | Faz 8, 12 |
| 95 | İçe aktarmadaki "2 saatten uzak" uyarısı kaldırıldı; yerine #93 aralığı dışındaki kayıt için uyarı verilir. Ayrıca kaydın referans fikstür dosyası, kaydın yapıldığı toplama gününe ait olmalıdır; başka haftanın dosyası hata verir | Faz 8, 12 |
| 96 | Cumartesi yüklenen fikstür dosyasında referans oranla (Avg 1-X-2) yer almayan maçlar (özellikle Cuma akşamı oynanan Süper Lig ve Premier League maçları) teste girmez. Bu maçların İddaa kaydı 8.1/8.2 için saklanır ve `has_reference = 0` olarak işaretlenir. Bu kural ilk kayıttan (23 Ekim 2026) önce yazıldı | Faz 8, 12 |
| 97 | Fikstür yükleme saati ilk haftalarda `fixtures-log` ile izlenir. Saat haftadan haftaya belirgin değişirse veya hafta içi (Salı oranları) yükleme düzeni farklı çıkarsa #93–#96 yeniden konuşulur | Faz 8 |
| 98 | Referans fikstür dosyası, oranların toplandığı güne (Cuma/Salı) ait **ilk yüklemedir** (#94 ve #96'daki "Cumartesi yüklenen dosya" ifadesinin yerine). Aynı toplama gününe ait sonraki yüklemeler yalnızca izleme için sürümlenir (#97) ve İddaa kayıtlarına referans olamaz. Gözlem: yükleme zamanı haftadan haftaya değişiyor: 17/10/26 Cumartesi 09:35, 23/10/26 Cuma 14:36 (İngiltere saati). 23 Ekim dosyası Cuma akşamı maçlarını da Avg oranlarıyla içeriyor; o hafta bu maçlar referanslıdır. İlk kayıt (23 Ekim, 19 maç) bu dosyaya bağlandı | Faz 8, 12 |

## Riskler ve gerçekçi beklentiler

Bu tür sistemleri kuranların büyük çoğunluğu piyasayı uzun vadede yenemiyor; plan, bunu erken ve ucuza öğrenmek üzerine kurulu.

- **Verimli piyasa:** Premier League oranları çok isabetli; avantaj daha çok küçük liglerde ve niş pazarlarda bulunur.
- **Kıyas verisi:** Pinnacle'ın genel API erişimi 23 Temmuz 2025'te kapandı. 2025/26 sonrası kıyas oranı daha az keskin olacak.
- **Yerel oran marjı:** İddaa'nın marjı uluslararası keskin şirketlerden genelde yüksek; uluslararası piyasada bulunan avantaj yasal oranlarda kaybolabilir.
- **Yasal çerçeve:** Türkiye'de yasal seçenek İddaa ve lisanslı sitelerdir; yabancı bahis siteleri yasa dışıdır.
- **Hesap limitleri:** Sürekli kazanan hesaplar sıklıkla limitlenir.
- **Aşırı uyum:** Çok fazla değişken veya alt grup denemek, geçmişte harika, gelecekte kötü sonuç veren bir model üretir. Kilitli final set buna karşı korumadır.
- **Bağımlılık riski:** Kayıpları kovalamamak için kasa ve kurallar önceden yazılır ve değiştirilmez.

**Durum:** Proje Faz 7 kararıyla durduruldu (karar #53): model piyasayı yenmiyor. Sonuç raporu: `reports/sonuc_raporu.md`.

**Aşama 2 (18 Ekim 2026, karar #54–#76):** Yeni soru İddaa oranlarının keskin piyasanın adil fiyatından sapması. Plan: `docs/yol-plani-v2.md` (orijinal taslak: `docs/yol-plani-v2-orijinal.md`). Sıradaki: Faz 8 uygulanabilirlik kontrolleri.

- [x] Faz 0: Kurallar (donduruldu)
- [x] Faz 1: Veri altyapısı
- [x] Faz 2: Basit model
- [x] Faz 3: Gelişmiş model
- [x] Faz 4: Geriye dönük test (seçim döneminde geçme şartı sağlanmadı; final setler kilitli)
- [ ] Faz 5: Ek veriler (yapılmadı; Faz 4 kapısı geçilemedi)
- [ ] Faz 6: Canlı kâğıt testi (yapılmadı)
- [x] Faz 7: Karar – durdur (karar #53)

## Kaynaklar

- [Pinnacle API dokümantasyonu](https://github.com/pinnacleapi/pinnacleapi-documentation): genel API erişiminin 23 Temmuz 2025'te kapanması
- [football-data.co.uk](https://football-data.co.uk/): maç sonuçları, erken ve kapanış oranları
