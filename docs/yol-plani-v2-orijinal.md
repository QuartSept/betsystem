# Futbol Bahis Analiz Sistemi – Yol Planı v2 (Aşama 2)

Oct 18, 2026 · @Can

## Durum ve amaç

Aşama 1 kapandı: herkese açık gol ve xG verisiyle kurulan model, Cuma günü verilen kararlarla piyasayı yenemedi (karar #53). Aşama 2'nin sorusu farklı: **Türkiye'de yasal olarak oynanabilen İddaa oranları, keskin piyasanın adil fiyatından ne zaman ve ne kadar sapıyor?**

Bu plan, Aşama 2'ye başlamak için gereken her kararı içerir. Kararlar #54'ten başlar ve depodaki `docs/yol-plani.md` numaralandırmasının devamıdır. Kod depoda yazılır; yeni kararlar önce bu plana işlenir.

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
- **Veri durumu:** Pinnacle oranları football-data'da 17 Ocak 2026'dan beri yok; 2025/26'da doluluk %55. Betfair borsası olduğu düşünülen BFE sütunu 2024/25'ten beri dolu (2025/26'da %94–95).
- **Kontrol edilecek tutarsızlık:** Belçika 2022/23'te Pinnacle kapanışının log-loss'u (0,9652), erken oranınkinden (0,9617) kötü. CLV'nin dayandığı "kapanış daha isabetli" varsayımı bu sezonda tutmuyor.

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
| N = ((z₁₋α + z₁₋β) × σ / δ)², δ = %1,5, α = 0,05, güç %80; σ her yeni fiyat ve lig için yeniden hesaplanır | #14, #25, #30 |
| Faz 4 geçme şartı: en az N bağımsız bahiste ortalama CLV > 0 ve tek yönlü %95 alt sınır > 0 | #42 |
| Sonradan bulunan alt gruplar kabul edilmez; önceden tanımlanıp yeni veride sınanır | #19 |
| Kilitli final setler (2023/24–2024/25) Aşama 2'de açılmaz | #44 |
| Model başarısı ile strateji uygulanabilirliği ayrı değerlendirilir | #5 |

## Yeni temel ilke ve yol haritası

Olasılık kaynağı artık marjı çıkarılmış piyasa; model ikincil. Avantaj, yumuşak bir şirketin (İddaa) bu adil fiyattan saptığı yerde aranır. Bu yaklaşımın işe yaradığı bilinen tek mekanizma, yumuşak şirketin fiyatını keskin piyasaya göre geç güncellemesidir.

&#91;embedded content: Aşama 2 yol haritası · 5 faz ve karar\]

En kritik faz 12: gerçekten oynanabilecek oranların ilk kez sınandığı yer. Faz 10 ve 11 bu sınavın ön koşulu değil; onu besleyen fikirleri ucuza eler.

## Faz 8 – Uygulanabilirlik kontrolleri

Amaç: Emek isteyen işlere başlamadan, İddaa'da bu stratejinin uygulanabilir olup olmadığını öğrenmek. Süre 2–3 hafta; çoğu kod gerektirmez.

| # | Kontrol | Nasıl | Çıktı |
| --- | --- | --- | --- |
| 8.1 | MBS kuralı | İddaa bültenini 2–3 hafta incele | Lig bazında tek oynanabilen (MBS 1) maç oranı |
| 8.2 | İddaa marjı | Hedef liglerde 1-X-2 oranlarını kaydet, Σ(1/oran) − 1 | Lig bazında ortalama marj; piyasa ortalaması erken marjıyla karşılaştırma |
| 8.3 | Kayıt yöntemi | İddaa'nın kullanım koşullarını oku; elle giriş veya izinli bir kaynak | Yazılı yöntem; koşullara aykırı otomatik toplama yok |
| 8.4 | Canlı referans | football-data'nın haftalık fikstür dosyasının sütunlarını ve notlarını incele | Hangi şirket sütunları var (Avg, Max, BFE); BFE'nin Betfair borsası olduğu doğrulandı |
| 8.5 | BFE doluluğu | Veri kalite raporunu hedef liglere genişlet | 2025/26–2026/27'de lig bazında doluluk |
| 8.6 | Belçika 2022/23 kapanış | Erken ve kapanış oranı farklarını, aşırı değerleri, tarih kaymalarını incele | Veri hatası mı, şans mı: yazılı sonuç |
| 8.7 | EV dağılımı | Kayıtlı her İddaa sonucu için EV = p\_adil × o\_iddaa − 1 | EV > 0 olan sonuçların oranı ve EV dağılımı |

**Hedef ligler (ön kayıt):** Premier League (E0) ve Süper Lig (T1). T1, lig taramasında üçüncü sırada çıktı ve yerel bir lig olarak İddaa katmanı için en anlamlı aday. Başka bir lig ancak 8.1'de MBS 1 maç oranı yeterliyse eklenir.

**Kayıt formatı (8.2 ve 8.7):** maç, lig, kayıt zamanı, İddaa 1-X-2 oranları, MBS, aynı andaki referans oranları. Depodaki yalnızca eklemeye izin veren İddaa tablosu kullanılır.

**Geçme şartı:**

- En az bir hedef ligde maçların anlamlı bir kısmı MBS 1 olmalı. Hiçbir ligde tek maç oynanamıyorsa Faz 12 duraklatılır; kombine yasağı (#2) gevşetilmez.
- 8.7'de hiçbir sonuçta EV > 0 görülmezse Faz 12 duraklatılır ve Faz 10 sonuçları beklenir. Bu bir durma değil; Faz 9 ve Faz 10 devam eder.

## Faz 9 – Karar destek paneli

Panel iki iş yapar: her hafta maçların olasılıklarını ve İddaa'daki beklenen değeri dürüstçe gösterir; aynı zamanda Faz 12'nin ölçüm aletidir. Streamlit ile kurulur (#18'deki erteleme Faz 4 bittiği için kalktı).

| Ekran | Gösterilen / yapılan |
| --- | --- |
| Haftalık maçlar | Her maç için marjsız piyasa olasılığı (ana), model olasılığı (ikincil), İddaa oranı, MBS, EV |
| Fırsat listesi | Yalnızca EV önceden belirlenen eşiğin üstündeki ve MBS 1 olan sonuçlar; yoksa "Bu hafta uygun fırsat yok" |
| İddaa kayıt formu | Oranların elle girişi; kayıt zamanı otomatik eklenir |
| Kayıt geçmişi | Tüm kayıtlar; yalnızca ekleme, düzeltme yeni satır olarak |
| Performans | Faz 12 bahisleri: CLV, ROI, bahis sayısı / N, referansa göre ayrı raporlama |

- **Ana olasılık:** Marjı çıkarılmış piyasa ortalaması erken oranı (Faz 8.4'e göre BFE varsa o da gösterilir). Aşama 1, en isabetli olasılığın bu olduğunu gösterdi.
- **Model olasılığı:** Bilgi için gösterilir, kararı belirlemez (Faz 10'da geçen bir fikir olmadıkça).
- **Sınırlar:** Otomatik bahis yok, öneri dışı bilgi (form, haber) yok, ayar değiştirme ekranı yok. Eşik ve kurallar yalnızca bu planla değişir.
- **Geçme şartı:** Panel iki hafta üst üste hatasız çalışır, her kayıt zaman damgalı ve referans oranla eşleşmiş olarak saklanır.

## Faz 10 – Tarihsel vekil testleri

Mevcut veriyle, dört ve yalnızca dört fikir test edilir; liste kapalıdır. Dönem Aşama 1 ile aynı: ayar 2020/21–2021/22, iç kontrol 2022/23, 2019/20 ısınma (#32, #33). Her test sonuçtan önce ayrı bir commit ile ön kayda alınır; başarısız olanlar dahil hepsi raporlanır.

**Çoklu karşılaştırma:** Dört fikir denendiği için hareket testinde tek yönlü α = 0,0125 (0,05 / 4) kullanılır. Faz 4 şartı (#42) değişmez; bağımsız doğrulama Faz 11'de yapılır.

| Test | Hipotez | Kural | Lig | Geçme |
| --- | --- | --- | --- | --- |
| 10a Yumuşak şirket fiyatı (modelsiz) | Tek bir yumuşak şirketin erken oranı, adil piyasa fiyatını aştığında pozitif CLV verir | o\_B365 erken > o\_adil × (1 + k) ise bahis; o\_adil = marjsız piyasa ortalaması erken; k ayar sezonlarında en az N bahis veren eşikler arasından seçilir | E0, T1 | Faz 4 şartı, CLV Pinnacle kapanışına göre |
| 10b Piyasa + model birleşimi | Model, piyasa olasılığına küçük bir düzeltme olarak eklenince kapanış hareketini öngörür | Girdileri logit(p\_piyasa) ve logit(p\_model) olan çok terimli lojistik regresyon; ayar sezonlarında eğitilir, walk-forward | B1 | Önce hareket testi, sonra Faz 4 şartı |
| 10c Alt/üst 2.5 | Skor matrisinden gelen P(>2.5), Pinnacle alt/üst kapanış hareketini öngörür | Faz 3 modeli (E0'da xG ile); bahis Pinnacle alt/üst erken oranından | E0, B1 | Önce hareket testi, sonra Faz 4 şartı |
| 10d Beraberlik çoğaltması | Model sapması, beraberlikte kapanış hareketini öngörür (B1'de eğim 0,118) | Faz 3 boru hattı her lige aynen uygulanır; yalnız beraberlik eğimi | T1, F2, I2, E2, E3 (hiç modellenmemiş, uygun ve bilgi kazancı en yüksek ligler) | Birleşik eğimin alt sınırı > 0; geçerse yalnız beraberlik bahsiyle Faz 4 şartı aynı liglerde |

- **10a neden önemli:** İddaa testinin mevcut veriyle yapılabilen tarihsel vekili. Ana şirket B365; WH, BW, IW ve VC yalnızca bilgi için raporlanır. Pinnacle erken oranı referans olarak duyarlılık testinde kullanılır. Kural fiyatı B365'ten aldığı için #24'ün "bahis fiyatı Pinnacle erken" kuralı bu testte istisnadır.
- **10c veri kontrolü:** Pinnacle alt/üst erken ve kapanış sütunlarının doluluğu test başlamadan kontrol edilir; N alt/üst için yeniden hesaplanır.
- **Geçen fikir:** Faz 11'e gider. Hiçbiri geçmezse Faz 11 atlanır; Faz 12 yine modelsiz kuralla yürütülür.

## Faz 11 – Yeni bağımsız değerlendirme penceresi

Faz 10'u geçen her fikir, hiç kullanılmamış bir dönemde bir kez ve ayar değiştirilmeden test edilir. Kilitli final setler yerinde kalır.

| Konu | Karar |
| --- | --- |
| Pencere | 2025/26 sezonunun tamamı ve 2026/27'nin 31 Aralık 2026'ya kadar oynanan maçları |
| Referans (CLV) | Marjı çıkarılmış BFE kapanışı; ligde BFE doluluğu %90'ın altındaysa marjsız piyasa ortalaması kapanışı |
| Bahis fiyatı | 10a türü kurallarda yumuşak şirketin erken oranı; model tabanlı kurallarda BFE erken oranı (aynı kaynaktan CLV, #24'ün gerekçesiyle) |
| Borsa komisyonu | CLV komisyonsuz hesaplanır; komisyon sonrası beklenen değer ayrıca raporlanır |
| N | Formül aynı; σ bu referans ve fiyatla, yalnızca 2025/26'nın ilk yarısından hesaplanır |
| Tek seferlik çalıştırma | Her fikir için bir kez; çalıştırma veritabanına kaydedilir, kod ikinci çalıştırmayı reddeder (#42'deki final set mekanizması gibi) |
| Geçme şartı | Faz 4 şartı (#42) |

- Pinnacle 2025/26'da kısmen var (%55) ama Temmuz 2025'ten sonra güvenilir değil; bu pencerede Pinnacle kullanılmaz.
- Faz 11'i geçen fikir, Faz 12'de modelsiz kuralın yanında ikinci bir kural olarak izlenir; kararları ayrı raporlanır.

## Faz 12 – Canlı İddaa testi ve karar

Asıl sınav: gerçekten oynanabilecek oranlarla, gerçek zamanda ve henüz para olmadan. Kurallar Faz 12 başlamadan dondurulur.

| Konu | Karar |
| --- | --- |
| Karar anı | Cuma öğleden sonra (hafta içi maçları için Salı), football-data erken oran saatiyle aynı (#6) |
| Kayıt | İddaa oranı ve referans oran, aralarında en çok 2 saat farkla, panelden |
| Adil olasılık | Marjsız piyasa ortalaması erken; BFE varsa duyarlılık olarak o da |
| Bahis kuralı | EV = p\_adil × o\_iddaa − 1 > e, e = %2; yalnızca MBS 1 maçlar; maç başına en yüksek EV'li tek sonuç |
| CLV | o\_iddaa × p\_adil\_kapanış − 1; kapanış referansı BFE (doluluk ≥ %90) yoksa marjsız piyasa ortalaması |
| N | Formül aynı (δ = %1,5); σ Faz 8 kayıtlarından hesaplanır ve Faz 12 başlarken sabitlenir |
| Süre | N bağımsız bahise kadar, en çok bir sezon. Bir sezonda N'ye ulaşılmazsa sonuç "belirsiz" sayılır, para kullanılmaz |
| Geçme şartı | Faz 4 şartı (#42); ayrıca ROI ve lig bazında sonuçlar raporlanır |

**Karar tablosu (sonuçlar görülmeden yazıldı):**

| Faz 12 (İddaa CLV) | Faz 11 (model fikri) | Karar |
| --- | --- | --- |
| Geçti | – | Küçük, önceden belirlenmiş ve sonradan artırılmayan bir kasayla başla; aylık değerlendirme, son N bahiste CLV negatife dönerse dur |
| Geçmedi | Geçti | Model başarılı, strateji İddaa'da doğrulanamadı; para yok |
| Geçmedi | Geçmedi / denenmedi | Para yok; panel haftalık olasılık gösterici olarak kalır |
| Belirsiz | – | Para yok; bir sezon daha ancak yeni bir ön kayıtla |

Modelsiz İddaa kuralında "model piyasayı yeniyor mu" sorusu yoktur; bu yüzden yalnızca Katman 2 (yasal oranlarda avantaj) aranır. #5'teki iki katmanlı kural model tabanlı stratejiler için aynen geçerlidir.

## Riskler ve dikkat edilecekler

En olası sonuç, bu yolun da avantaj göstermemesi; plan bunu yine erken ve ucuza öğrenmek üzerine kurulu.

- **İddaa marjı:** Uluslararası keskin şirketlerden yüksekse, adil fiyatı aşan oran nadir olur. Faz 8.2 bunu ilk haftalarda ölçer.
- **MBS ve kurallar:** İddaa'nın MBS, oran ve azami kazanç kuralları değişebilir; Faz 12 boyunca her kayıtla birlikte saklanır.
- **Yasal çerçeve:** Yalnızca İddaa ve lisanslı siteler; yabancı bahis siteleri ve borsalar Türkiye'de yasa dışıdır. BFE yalnızca referans fiyat olarak kullanılır.
- **Veri kullanımı:** İddaa ve diğer sitelerin verileri kullanım koşullarına uygun toplanır (8.3).
- **Referans kalitesi:** Pinnacle olmadan referans daha az keskin; CLV sonuçları Pinnacle dönemiyle tek seri olarak yorumlanmaz (#8).
- **Aşırı uyum:** Faz 10'un listesi kapalı; yeni fikir ancak bu plana karar olarak eklenip ön kayda alınırsa denenir.
- **"Sonuca ulaşana kadar" tuzağı:** Yeterince fikir denenirse biri mutlaka şans eseri kârlı görünür. Bu yüzden durma kuralları ve tek seferlik testler korunur.
- **Bağımlılık riski:** Kasa, bahis miktarı ve durma kuralı para kullanılmadan önce yazılır ve değiştirilmez. Kayıpları kovalamak için kural esnetilmez.

## Karar kaydı

Aşama 2 kararları, depodaki #1–#53'ün devamı; hepsi 18 Ekim 2026'da alındı. Depodaki `docs/yol-plani.md`'ye aynı numaralarla işlenmeli.

| # | Karar | Bölüm |
| --- | --- | --- |
| 54 | Aşama 2 başladı; olasılık kaynağı marjsız piyasa, model ikincil | Temel ilke |
| 55 | Faz sırası 8 → 12 ve geçme şartları bu plandaki gibi; Faz 9 ve 10 paralel yürüyebilir | Yol haritası |
| 56 | Hedef ligler E0 ve T1; başka lig ancak MBS 1 maç oranı yeterliyse | Faz 8 |
| 57 | MBS 1 olmayan maçta bahis yok; kombine yasağı (#2) korunur | Faz 8, 12 |
| 58 | İddaa oranları yalnızca kullanım koşullarına uygun yöntemle ve yalnızca eklenen tabloya kaydedilir | Faz 8, 9 |
| 59 | Belçika 2022/23 kapanış verisi Faz 8'de kontrol edilir | Faz 8 |
| 60 | Panel Streamlit ile kurulur; ana olasılık marjsız piyasa, model bilgi için; eşik altında "fırsat yok"; otomatik bahis yok | Faz 9 |
| 61 | Faz 10 test listesi kapalı: 10a, 10b, 10c, 10d | Faz 10 |
| 62 | Faz 10 hareket testinde tek yönlü α = 0,0125 | Faz 10 |
| 63 | 10a: ana şirket B365, referans marjsız piyasa ortalaması erken, ligler E0 ve T1; bu testte #24 istisnası | Faz 10 |
| 64 | 10d çoğaltma ligleri: T1, F2, I2, E2, E3 | Faz 10 |
| 65 | Faz 11 penceresi 2025/26 ve 2026/27'nin 31 Aralık 2026'ya kadarki maçları; referans BFE (≥ %90 doluluk), yoksa piyasa ortalaması; her fikir bir kez | Faz 11 |
| 66 | Faz 12 kuralı: Cuma/Salı karar anı, kayıtlar arası en çok 2 saat, EV eşiği e = %2, en çok bir sezon | Faz 12 |
| 67 | Faz 12 N'si δ = %1,5 ile, σ Faz 8 kayıtlarından hesaplanıp sabitlenir | Faz 12 |
| 68 | Karar tablosu bu plandaki gibi; modelsiz İddaa kuralında yalnızca Katman 2 aranır | Faz 12 |
| 69 | Kilitli final setler (#44) Aşama 2'de açılmaz | Kurallar |
| 70 | Çalışma düzeni: kararlar ve planlama Claude ile bu planda; kod depoda; her yeni karar önce bu kayda eklenir | Genel |

## İlk adımlar

Sıra, en ucuz ve en belirleyici kontrollerden başlıyor.

- [ ] \#54–#70'i depodaki `docs/yol-plani.md`'ye işle ve commit'le
- [ ] 8.4: football-data notlarından BFE'nin anlamını ve haftalık fikstür dosyasının sütunlarını doğrula
- [ ] 8.3: İddaa kullanım koşullarını oku, kayıt yöntemini yaz
- [ ] 8.1 ve 8.2: Bu Cuma'dan itibaren E0 ve T1 için İddaa oranlarını ve MBS'yi kaydetmeye başla (2–3 hafta)
- [ ] 8.5 ve 8.6: Veri kalite raporuna BFE doluluğunu ve B1 2022/23 kapanış kontrolünü ekle
- [ ] Faz 10 için dört testin ön kaydını, sonuçlardan önce ayrı commit'lerle yap
- [ ] Faz 9 panelinin ilk sürümü: haftalık maçlar ve İddaa kayıt formu

## Kaynaklar

- [Proje deposu](https://github.com/QuartSept/betsystem): Aşama 1 kodu, raporlar ve #1–#53
- [football-data.co.uk](https://football-data.co.uk/): sonuçlar ve oranlar
- [Pinnacle API dokümantasyonu](https://github.com/pinnacleapi/pinnacleapi-documentation): genel erişimin 23 Temmuz 2025'te kapanması
- [Yol Planı (Sürüm 2)](https://claude.ai/code/artifact/646ad109-df37-4b80-ae68-6fea5209d86f): Aşama 1 planı ve ilk kararlar
