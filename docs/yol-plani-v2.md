# Futbol Bahis Analiz Sistemi – Yol Planı v2 (Aşama 2)

Oct 18, 2026 · @Can · Düzeltilmiş sürüm (18 Ekim 2026): fizibilite kapısı, 10b'nin çıkarılması, α düzeltmesi, zamanlama ve #10 değişikliği eklendi (kararlar #71–#76).

## Durum ve amaç

Aşama 1 kapandı: herkese açık gol ve xG verisiyle kurulan model, Cuma günü verilen kararlarla piyasayı yenemedi (karar #53). Aşama 2'nin sorusu farklı: **Türkiye'de yasal olarak oynanabilen İddaa oranları, keskin piyasanın adil fiyatından ne zaman ve ne kadar sapıyor?**

Bu plan, Aşama 2'ye başlamak için gereken her kararı içerir. Kararlar #54'ten başlar ve `docs/yol-plani.md` numaralandırmasının devamıdır. Kod depoda yazılır; yeni kararlar önce bu plana işlenir.

- **Hedef 1 – Çalışan sistem:** Her hafta maçların olasılığını, İddaa oranını ve beklenen değeri gösteren, fırsat yoksa "fırsat yok" diyen bir panel.
- **Hedef 2 – Doğrulanmış avantaj:** İddaa'da, önceden yazılmış kurallarla ve N bahiste pozitif CLV.
- Hedef 1 her durumda teslim edilir. Hedef 2 bulunamazsa gerçek para kullanılmaz.

## Aşama 1'den öğrendiklerimiz

En isabetli olasılık bizim modelimiz değil, piyasanın marjı çıkarılmış olasılığı. Aşama 2 bu bulgunun üzerine kuruluyor.

| Bulgu | Sayı | Kaynak rapor |
| --- | --- | --- |
| Premier League log-loss: piyasa ortalaması erken / Pinnacle erken / Faz 3 modeli | 0,969 / 0,970 / 0,985–1,002 | faz2\_poisson, faz3\_model |
| Premier League Faz 4: 778 bahis, ortalama CLV (rastgele bahis ≈ −%1,9) | −%1,71 | faz4\_secim |
| Cuma'dan kapanışa piyasaya giren bilgi (log-loss farkı), Premier League / Belçika | 0,0031 / 0,0087 | lig\_taramasi |
| Hareket testi eğimi: Premier League / Hollanda / Belçika | 0,001 / 0,010 / 0,047 (yalnız Belçika geçti) | lig\_B1, lig\_N1 |
| Belçika Faz 4: 479 bahis, ortalama CLV (rastgele ≈ −%4,0) | −%2,84 | faz4\_secim\_B1 |
| Belçika beraberlik eğimi (sonradan bulunmuş alt grup) | 0,118 | lig\_B1 |

- **Neden yenemedik:** Erken oranlar zaten çok isabetli; model piyasanın bilmediği bir şey bilmiyor; marj, bulunan küçük sinyalden büyük.
- **Kilitli kalanlar:** Tüm liglerde 2023/24–2024/25 final setleri hiç açılmadı (#44).
- **Veri durumu:** Pinnacle oranları football-data'da 17 Ocak 2026'dan beri yok (Premier League'de 8 Ocak 2026'ya kadar tam; 2025/26 doluluğu %55). BFE sütunu, football-data notlarına göre (notes.txt) **Betfair Exchange**. Premier League'de BFE doluluğu: 2024/25 %100, 2025/26 %95 (360/380), 2026/27 %100; 2023/24 ve öncesinde yok.
- **Belçika 2022/23 kapanışı (ön kontrol):** Bu sezon kapanışın bilgi kazancı −0,0035 (%95 GA −0,0120…0,0050), yani sıfırdan ayırt edilemiyor. Premier League 2021/22'de de −0,0005. Tek sezonluk örnekleme gürültüsüyle uyumlu; 8.6'da veri hatası olup olmadığı ayrıca kontrol edilir.

## Değişmeyen kurallar

Aşama 1'in kuralları Aşama 2'de aynen geçerli; yalnızca bu planda açıkça yazılan değişiklikler uygulanır.

| Kural | Karar |
| --- | --- |
| Gerçek para yok; başarı ölçütü kupon değil, CLV | #1, Faz 0 |
| Kombine kupon yok; tek maç bahsi | #2 |
| Her ayar, test ve geçme şartı sonuçtan önce ayrı commit ile ön kayda alınır | Aşama 1 uygulaması |
| Tarihsel testlerde bahis fiyatı Pinnacle erken; eksikse bahis yok, başka şirketle doldurulmaz | #24, #27 |
| Max (en iyi fiyat) karar için kullanılmaz | #26 |
| Sabit 1 sanal birim; Kelly yalnızca karşılaştırma | #11 |
| Farklı kıyas oranlarıyla hesaplanan CLV ayrı raporlanır | #8 |
| N = ((z₁₋α + z₁₋β) × σ / δ)², δ = %1,5, güç %80; σ her yeni fiyat ve lig için yeniden hesaplanır; α, testin kendi α'sıdır (#72) | #14, #25, #30 |
| Faz 4 geçme şartı: en az N bağımsız bahiste ortalama CLV > 0 ve tek yönlü alt sınır > 0 | #42 |
| Sonradan bulunan alt gruplar kabul edilmez; önceden tanımlanıp yeni veride sınanır | #19 |
| Kilitli final setler (2023/24–2024/25) Aşama 2'de açılmaz | #44 |
| Model başarısı ile strateji uygulanabilirliği ayrı değerlendirilir | #5 |

**Aşama 2'de bilerek değiştirilen kurallar:**

| Eski kural | Değişiklik | Karar |
| --- | --- | --- |
| #10: alt/üst 2.5 ancak 1-X-2 doğrulandıktan sonra | 1-X-2 doğrulanmadı, buna rağmen alt/üst 2.5 Faz 10'da (10c) tarihsel olarak test edilir. Canlı (Faz 12) kural yalnızca 1-X-2 kalır | #75 |
| #24: bahis fiyatı Pinnacle erken | 10a'da bahis fiyatı B365 erken (yumuşak şirket testi) | #63 |
| #18: Streamlit Faz 4 sonrasına ertelendi | Faz 4 bittiği için erteleme kalktı | #60 |

## Yeni temel ilke ve yol haritası

Olasılık kaynağı artık marjı çıkarılmış piyasa; model ikincil. Avantaj, yumuşak bir şirketin (İddaa) bu adil fiyattan saptığı yerde aranır. Bu yaklaşımın işe yaradığı bilinen tek mekanizma, yumuşak şirketin fiyatını keskin piyasaya göre geç güncellemesidir.

Faz 8 → 9 → 10 → 11 → 12. Faz 9 ve 10 paralel yürüyebilir. En kritik faz 12: gerçekten oynanabilecek oranların ilk kez sınandığı yer. Faz 10 ve 11 bu sınavın ön koşulu değil; onu besleyen fikirleri ucuza eler.

## Fizibilite kapısı (karar #71)

Aşama 1'in dersi: bir test, geçme şartını matematiksel olarak sağlayamayacak kadar az bahis üretiyorsa çalıştırmanın anlamı yoktur, ama sonucuna bakmak yine de yanıltıcı fikirler doğurur. Bu yüzden Faz 10, 11 ve 12'deki her test, **kuralın seçtiği bahislerin CLV'sine ve maç sonuçlarına bakmadan** önce bir fizibilite kontrolünden geçer (#82):

- Değerlendirme dönemindeki beklenen bahis sayısı, testin kendi α'sıyla hesaplanan N'den küçükse test **"yetersiz güç"** olarak raporlanır ve sonuç analizi yapılmaz. Bu, başarısızlık değil, değerlendirilemezlik kaydıdır.
- Kullanılanlar: erken fiyatlar, model olasılıkları ve σ vekili. σ, N için Aşama 1 yöntemiyle (erken fiyat × marjsız kapanış − 1, maç başına tek sonuç) hesaplanır; yani kapanış oranını kullanır, ama kuralın seçtiği bahislerden bağımsızdır ve kuralın başarısını göstermez.
- Kontrolün sonucu, testin ön kayıt commit'ine yazılır.

## Faz 8 – Uygulanabilirlik kontrolleri

Amaç: Emek isteyen işlere başlamadan, İddaa'da bu stratejinin uygulanabilir olup olmadığını öğrenmek. Süre 2–3 hafta; çoğu kod gerektirmez.

| # | Kontrol | Nasıl | Çıktı |
| --- | --- | --- | --- |
| 8.1 | MBS kuralı | İddaa bültenini 2–3 hafta incele | Lig bazında tek oynanabilen (MBS 1) maç oranı |
| 8.2 | İddaa marjı | Hedef liglerde 1-X-2 oranlarını kaydet, Σ(1/oran) − 1 | Lig bazında ortalama marj; piyasa ortalaması erken marjıyla karşılaştırma |
| 8.3 | Kayıt yöntemi | İddaa'nın kullanım koşullarını oku; elle giriş veya izinli bir kaynak | Yazılı yöntem; koşullara aykırı otomatik toplama yok |
| 8.4 | Canlı referans | football-data'nın haftalık fikstür dosyasının sütunlarını, notlarını ve **güncellenme zamanını** incele | Hangi şirket sütunları var (Avg, Max, BFE); dosyanın Cuma günü ne zaman güncellendiği (sha değişimiyle izlenir). BFE'nin Betfair Exchange olduğu notes.txt'den doğrulandı |
| 8.5 | BFE doluluğu | Veri kalite raporunu Faz 11 liglerine genişlet: E0, T1, B1, F2, I2, E2, E3 | 2025/26–2026/27'de lig bazında doluluk. E0 dışındaki ligler için 2025/26 ve 2026/27 CSV'leri indirilir |
| 8.6 | Belçika 2022/23 kapanış | Erken ve kapanış farklarını, aşırı değerleri, tarih kaymalarını incele | Ön kontrol: gürültüyle uyumlu (yukarıda). Veri hatası olup olmadığı yazılı sonuç olarak eklenir |
| 8.7 | EV dağılımı | Kayıtlı her İddaa sonucu için EV = p\_adil × o\_iddaa − 1 | EV > 0, > %1, > %2 olan sonuçların oranı; Faz 12 fizibilitesinin girdisi (#76) |

**Hedef ligler (ön kayıt):** Premier League (E0) ve Süper Lig (T1). T1, lig taramasında üçüncü sırada çıktı ve yerel bir lig olarak İddaa katmanı için en anlamlı aday. Başka bir lig ancak 8.1'de MBS 1 maç oranı yeterliyse eklenir.

**Kayıt formatı (8.2 ve 8.7, #79):** tek şablon `templates/iddaa_kayit_sablonu.xlsx`: kayıt zamanı, lig, maç tarihi/saati, ev ve deplasman (football-data yazımı), İddaa 1-X-2 oranları, MBS, referans fikstür dosyasının adı. Fikstür dosyası önce `betsistem import-fixtures` ile sürümlenir (#80); kayıtlar `betsistem import-iddaa` ile yalnızca eklemeye izin veren tabloya yazılır.

**Geçme şartı:**

- En az bir hedef ligde maçların anlamlı bir kısmı MBS 1 olmalı. Hiçbir ligde tek maç oynanamıyorsa Faz 12 duraklatılır; kombine yasağı (#2) gevşetilmez.
- 8.7'de hiçbir sonuçta EV > 0 görülmezse Faz 12 duraklatılır ve Faz 10 sonuçları beklenir. Bu bir durma değil; Faz 9 ve Faz 10 devam eder.

## Faz 9 – Karar destek paneli

Panel iki iş yapar: her hafta maçların olasılıklarını ve İddaa'daki beklenen değeri dürüstçe gösterir; aynı zamanda Faz 12'nin ölçüm aletidir. Streamlit ile kurulur (#18'deki erteleme Faz 4 bittiği için kalktı).

| Ekran | Gösterilen / yapılan |
| --- | --- |
| Haftalık maçlar | Her maç için marjsız piyasa olasılığı (ana), model olasılığı (ikincil), İddaa oranı, MBS, EV |
| Fırsat listesi | Yalnızca EV önceden belirlenen eşiğin üstündeki ve MBS 1 olan sonuçlar; yoksa "Bu hafta uygun fırsat yok" |
| Referans dosyası | Haftalık fikstür dosyasının yüklenmesi; sha ve yükleme zamanı otomatik kaydedilir |
| İddaa kayıt formu | Oranların elle girişi; kayıt zamanı otomatik eklenir; referans dosyanın yüklenmesinden 2 saatten uzak kayıt uyarı verir |
| Kayıt geçmişi | Tüm kayıtlar; yalnızca ekleme, düzeltme yeni satır olarak |
| Performans | Faz 12 bahisleri: CLV, ROI, bahis sayısı / N, referansa göre ayrı raporlama |

- **Ana olasılık:** Marjı çıkarılmış piyasa ortalaması erken oranı (Faz 8.4'e göre BFE varsa o da gösterilir). Aşama 1, en isabetli olasılığın bu olduğunu gösterdi.
- **Model olasılığı:** Bilgi için gösterilir, kararı belirlemez (Faz 10'da geçen bir fikir olmadıkça).
- **Sınırlar:** Otomatik bahis yok, öneri dışı bilgi (form, haber) yok, ayar değiştirme ekranı yok. Eşik ve kurallar yalnızca bu planla değişir.
- **Erişim notu:** football-data Türkiye'den engelli; fikstür dosyası her hafta elle indirilip panele yüklenir.
- **Geçme şartı:** Panel iki hafta üst üste hatasız çalışır, her kayıt zaman damgalı ve referans dosya sürümüyle eşleşmiş olarak saklanır.

## Faz 10 – Tarihsel vekil testleri

Mevcut veriyle, üç ve yalnızca üç fikir test edilir; liste kapalıdır (#61). Her test sonuçtan önce ayrı bir commit ile ön kayda alınır ve fizibilite kapısından (#71) geçer; başarısız ve "yetersiz güç" olanlar dahil hepsi raporlanır.

**Dönem:** Model kullanan testlerde Aşama 1 ile aynı: ayar 2020/21–2021/22, iç kontrol 2022/23, 2019/20 ısınma (#32, #33). Modelsiz 10a'da ısınma gerekmediği için dönem 2019/20–2022/23'tür (#73).

**Çoklu karşılaştırma (#72):** Üç fikir denendiği için Faz 10'daki her nihai kararda tek yönlü α = 0,05 / 3 ≈ 0,0167 kullanılır: hareket testinin alt sınırında da, Faz 4 tipi CLV şartının alt sınırında da. N de bu α ile hesaplanır. Bağımsız doğrulama Faz 11'de yapılır.

| Test | Hipotez | Kural | Lig | Geçme |
| --- | --- | --- | --- | --- |
| 10a Yumuşak şirket fiyatı (modelsiz) | Tek bir yumuşak şirketin erken oranı, adil piyasa fiyatını aştığında pozitif CLV verir | Maç başına o\_B365 / o\_adil oranı en yüksek tek sonuç; oran > 1 + k ise bahis. o\_adil = marjsız piyasa ortalaması erken. k ∈ {0; 0,01; 0,02; 0,03}, #40 kuralıyla (en az N bahis verenler arasında ortalama CLV'si en yüksek) | E0 ve T1 birlikte, tek test | Faz 4 şartı (α = 0,0167), CLV Pinnacle kapanışına göre |
| 10c Alt/üst 2.5 | Skor matrisinden gelen P(>2.5), Pinnacle alt/üst kapanış hareketini öngörür | Faz 3 modeli (E0'da xG ile); bahis Pinnacle alt/üst erken oranından | E0, B1 | Önce hareket testi, sonra Faz 4 şartı (ikisi de α = 0,0167) |
| 10d Beraberlik çoğaltması | Model sapması, beraberlikte kapanış hareketini öngörür (B1'de eğim 0,118) | Faz 3 boru hattı her lige aynen uygulanır; yalnız beraberlik eğimi | T1, F2, I2, E2, E3 (hiç modellenmemiş, uygun ve bilgi kazancı en yüksek ligler) | Birleşik eğimin alt sınırı > 0 (α = 0,0167); geçerse yalnız beraberlik bahsiyle Faz 4 şartı aynı liglerde |

- **10a neden önemli:** İddaa testinin mevcut veriyle yapılabilen tarihsel vekili. Ana şirket B365; WH, BW, IW ve VC yalnızca bilgi için raporlanır. Pinnacle erken oranı referans olarak duyarlılık testinde kullanılır. Kural fiyatı B365'ten aldığı için #24'ün "bahis fiyatı Pinnacle erken" kuralı bu testte istisnadır.
- **10a ön fizibilite (yalnızca fiyat ilişkisi, sonuç ve CLV'ye bakılmadan):** 2019/20–2022/23'te E0 + T1 birlikte σ = 0,0960, α = 0,0167 ile **N = 361**. Kuralın ürettiği bahis sayısı k = 0 / 0,01 / 0,02 / 0,03 için 384 / 248 / 181 / 127. Yani yalnızca k = 0 fizibil; #40 kuralı k = 0'ı seçer. İki lig ayrı ayrı test edilseydi ikisi de fizibil olmazdı (E0 en çok 178, T1 en çok 206 bahis).
- **10b çıkarıldı (#74):** "Piyasa + model birleşimi" kurgusu gereği bahis üretemez. Belçika'da hareket eğimi 0,047; modelin tipik sapması (logit ölçeğinde std ≈ 0,35) piyasa olasılığını ancak ≈ 0,016 logit (≈ 0,4 puan) kaydırır. Pinnacle erken marjı ise %4,1. Birleşik olasılıkla EV > 0 olan sonuç neredeyse hiç çıkmaz; fizibilite kapısını geçemez. Belçika sinyali 10d'nin çoğaltma testinde ve ileride canlı veride sınanabilir.
- **10c veri kontrolü:** Pinnacle alt/üst erken (P>2.5, P<2.5) ve kapanış (PC>2.5, PC<2.5) sütunları E0, B1 ve T1 dosyalarında var; doluluk test başlamadan ölçülür. Yükleyici alt/üst pazarını da okuyacak şekilde genişletilir (#75). N alt/üst için yeniden hesaplanır.
- **Geçen fikir:** Faz 11'e gider. Hiçbiri geçmezse Faz 11 atlanır; Faz 12 yine modelsiz kuralla yürütülür.

## Faz 11 – Yeni bağımsız değerlendirme penceresi

Faz 10'u geçen her fikir, hiç kullanılmamış bir dönemde bir kez ve ayar değiştirilmeden test edilir. Kilitli final setler yerinde kalır.

| Konu | Karar |
| --- | --- |
| Pencere | 2025/26 sezonunun tamamı ve 2026/27'nin 31 Aralık 2026'ya kadar oynanan maçları. Kapanış oranları dahil veri ancak Ocak 2027'de tamamlanır; Faz 11 en erken o zaman çalıştırılır |
| Veri | E0 dışındaki liglerin 2025/26 ve 2026/27 CSV'leri indirilir; BFE doluluğu 8.5'te ölçülür |
| Referans (CLV) | Marjı çıkarılmış BFE kapanışı; ligde BFE doluluğu %90'ın altındaysa marjsız piyasa ortalaması kapanışı |
| Bahis fiyatı | 10a türü kurallarda yumuşak şirketin erken oranı; model tabanlı kurallarda BFE erken oranı (aynı kaynaktan CLV, #24'ün gerekçesiyle) |
| Borsa komisyonu | CLV komisyonsuz hesaplanır; komisyon sonrası beklenen değer ayrıca raporlanır |
| N | Formül aynı; σ bu referans ve fiyatla, yalnızca 2025/26'nın ilk yarısının fiyatlarından hesaplanır (sonuçlar kullanılmaz). α = 0,05 / Faz 11'e giren fikir sayısı |
| Fizibilite | Her fikir için #71'deki kontrol pencerede yapılır |
| Tek seferlik çalıştırma | Her fikir için bir kez; çalıştırma veritabanına kaydedilir, kod ikinci çalıştırmayı reddeder (#42'deki final set mekanizması gibi) |
| Geçme şartı | Faz 4 şartı (#42), yukarıdaki α ile |

- Pinnacle bu pencerede kullanılmaz: 2025/26'nın ortasında kesildiği için (doluluk %55) pencerenin tamamı için tutarlı bir referans değildir.
- Faz 11'i geçen fikir, Faz 12'de modelsiz kuralın yanında ikinci bir kural olarak izlenir; kararları ayrı raporlanır.

## Faz 12 – Canlı İddaa testi ve karar

Asıl sınav: gerçekten oynanabilecek oranlarla, gerçek zamanda ve henüz para olmadan. Kurallar Faz 12 başlamadan dondurulur.

| Konu | Karar |
| --- | --- |
| Karar anı | Cuma (hafta içi maçları için Salı) football-data fikstür dosyasının o haftaki güncellemesi (#6'nın canlı karşılığı) |
| Referans anı ve kayıt (#76) | Referans, o haftanın fikstür dosyasının güncellendikten sonraki ilk indirmesidir; dosyanın sha'sı ve indirme zamanı kaydedilir. İddaa oranları bu indirme zamanından en çok 2 saat önce veya sonra kaydedilir. football-data'nın oranları topladığı kesin saat bilinmediği için referansın gerçek yaşı raporda belirsizlik olarak belirtilir |
| Adil olasılık | Marjsız piyasa ortalaması erken; BFE varsa duyarlılık olarak o da |
| Bahis kuralı | EV = p\_adil × o\_iddaa − 1 > e; yalnızca MBS 1 maçlar; maç başına en yüksek EV'li tek sonuç |
| EV eşiği e (#76) | Faz 8 kayıtlarından, yalnızca fiyatlarla öngörülen sezonluk bahis sayısına göre seçilir: {%2; %1; %0} içinden, öngörülen bahis sayısının N'ye en çok iki sezonda ulaştığı en büyük e. Hiçbiri ulaşmıyorsa Faz 12 test olarak yapılmaz; panel gösterici olarak kalır |
| CLV | o\_iddaa × p\_adil\_kapanış − 1; kapanış referansı BFE (doluluk ≥ %90) yoksa marjsız piyasa ortalaması |
| N | Formül aynı (δ = %1,5, α = 0,05); σ Faz 8 kayıtlarından hesaplanır ve Faz 12 başlarken sabitlenir |
| Süre | e seçimiyle birlikte sabitlenir: N bahise kadar, en çok bir veya iki sezon. Bu sürede N'ye ulaşılmazsa sonuç "belirsiz" sayılır, para kullanılmaz |
| Geçme şartı | Faz 4 şartı (#42); ayrıca ROI ve lig bazında sonuçlar raporlanır |

**Neden e seçimi bir kurala bağlandı:** Aşama 1'deki B365 verisi, adil fiyatı %2 aşan sonuçların Premier League'de maçların yalnızca yaklaşık %5'inde görüldüğünü gösteriyor. İddaa'nın marjı B365'ten yüksekse oran daha da düşer. Sabit %2 eşiği ve bir sezonluk süreyle Faz 12'nin "belirsiz" bitmesi neredeyse kesin olurdu.

**Karar tablosu (sonuçlar görülmeden yazıldı):**

| Faz 12 (İddaa CLV) | Faz 11 (model fikri) | Karar |
| --- | --- | --- |
| Geçti | – | Küçük, önceden belirlenmiş ve sonradan artırılmayan bir kasayla başla; aylık değerlendirme, son N bahiste CLV negatife dönerse dur |
| Geçmedi | Geçti | Model başarılı, strateji İddaa'da doğrulanamadı; para yok |
| Geçmedi | Geçmedi / denenmedi | Para yok; panel haftalık olasılık gösterici olarak kalır |
| Belirsiz veya yapılmadı | – | Para yok; bir sezon daha ancak yeni bir ön kayıtla |

Modelsiz İddaa kuralında "model piyasayı yeniyor mu" sorusu yoktur; bu yüzden yalnızca Katman 2 (yasal oranlarda avantaj) aranır. #5'teki iki katmanlı kural model tabanlı stratejiler için aynen geçerlidir.

## Riskler ve dikkat edilecekler

En olası sonuç, bu yolun da avantaj göstermemesi; plan bunu yine erken ve ucuza öğrenmek üzerine kurulu.

- **İddaa marjı:** Uluslararası keskin şirketlerden yüksekse, adil fiyatı aşan oran nadir olur. Faz 8.2 bunu ilk haftalarda ölçer.
- **Bahis hacmi:** Adil fiyatı aşan oranlar seyrektir; testler N'ye ulaşamayabilir. Fizibilite kapısı (#71) bunu sonuçlara bakmadan önce yakalar.
- **MBS ve kurallar:** İddaa'nın MBS, oran ve azami kazanç kuralları değişebilir; Faz 12 boyunca her kayıtla birlikte saklanır.
- **Yasal çerçeve:** Yalnızca İddaa ve lisanslı siteler; yabancı bahis siteleri ve borsalar Türkiye'de yasa dışıdır. BFE yalnızca referans fiyat olarak kullanılır.
- **Veri kullanımı:** İddaa ve diğer sitelerin verileri kullanım koşullarına uygun toplanır (8.3).
- **Referans kalitesi ve zamanı:** Pinnacle olmadan referans daha az keskin; CLV sonuçları Pinnacle dönemiyle tek seri olarak yorumlanmaz (#8). Referans oranların toplanma saati tam bilinmez.
- **Aşırı uyum:** Faz 10'un listesi kapalı; yeni fikir ancak bu plana karar olarak eklenip ön kayda alınırsa denenir.
- **"Sonuca ulaşana kadar" tuzağı:** Yeterince fikir denenirse biri mutlaka şans eseri kârlı görünür. Bu yüzden durma kuralları, α düzeltmesi ve tek seferlik testler korunur.
- **Bağımlılık riski:** Kasa, bahis miktarı ve durma kuralı para kullanılmadan önce yazılır ve değiştirilmez. Kayıpları kovalamak için kural esnetilmez.

## Karar kaydı

Aşama 2 kararları, `docs/yol-plani.md`'deki #1–#53'ün devamı; hepsi 18 Ekim 2026'da alındı ve aynı numaralarla oraya işlendi. #77 ve sonrası uygulama kayıtlarıdır.

| # | Karar | Bölüm |
| --- | --- | --- |
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

## İlk adımlar

Sıra, en ucuz ve en belirleyici kontrollerden başlıyor.

- [x] #54–#76'yı `docs/yol-plani.md`'ye işle ve commit'le
- [ ] 8.4: Haftalık fikstür dosyasının sütunlarını doğrula; Cuma güncelleme zamanı `fixtures-log`'daki sha değişimlerinden okunacak (#80). BFE = Betfair Exchange notes.txt'den doğrulandı
- [x] Tek İddaa şablonu ve içe aktarma (#79), fikstür sürümleme (#80), Faz 11 kilidi (#81), Faz 10 tek çalıştırma kaydı (#83)
- [ ] 8.3: İddaa kullanım koşullarını oku, kayıt yöntemini yaz
- [ ] 8.1 ve 8.2: Bu Cuma'dan itibaren E0 ve T1 için İddaa oranlarını ve MBS'yi kaydetmeye başla (2–3 hafta)
- [ ] 8.5 ve 8.6: Faz 11 liglerinin 2025/26–2026/27 CSV'lerini indir; veri kalite raporuna BFE doluluğunu ve B1 2022/23 veri hatası kontrolünü ekle
- [x] Faz 10 için üç testin ön kaydını, sonuçlardan önce ayrı commit'lerle yap (10c için önce yükleyici genişletmesi)
- [ ] Faz 9 panelinin ilk sürümü: haftalık maçlar, referans dosyası yükleme ve İddaa kayıt formu

## Kaynaklar

- [Proje deposu](https://github.com/QuartSept/betsystem): Aşama 1 kodu, raporlar ve #1–#53
- [football-data.co.uk](https://football-data.co.uk/): sonuçlar ve oranlar
- [Pinnacle API dokümantasyonu](https://github.com/pinnacleapi/pinnacleapi-documentation): genel erişimin 23 Temmuz 2025'te kapanması
- [Yol Planı (Sürüm 2)](https://claude.ai/code/artifact/646ad109-df37-4b80-ae68-6fea5209d86f): Aşama 1 planı ve ilk kararlar
