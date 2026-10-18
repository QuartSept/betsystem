# betsistem

Futbol bahis analiz sistemi. Amaç ve kurallar: [docs/yol-plani.md](docs/yol-plani.md).

**Durum:** Aşama 1, Faz 7 kararıyla kapandı: model piyasayı yenmiyor (karar #53, [sonuç raporu](reports/sonuc_raporu.md)). Kilitli final setleri açılmadı.
Aşama 2 başladı: İddaa oranlarının adil piyasa fiyatından sapması ([docs/yol-plani-v2.md](docs/yol-plani-v2.md), karar #54–#76).

## Kurulum

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest
```

## Veri

Ham dosyalar `data/raw/` altında değiştirilmeden, veritabanı `data/db/betsistem.sqlite` içinde tutulur (ikisi de git dışında).
Her ham dosya `data_versions` tablosuna kaynak, sha256 ve edinme zamanıyla kaydedilir.

```powershell
# Otomatik indirme (erişim varsa)
.venv\Scripts\betsistem fetch --season 2223

# Elle indirilen dosya
.venv\Scripts\betsistem import-raw C:\indirilenler\E0.csv --season 2223

# Understat xG (önce football-data yüklenmiş olmalı)
.venv\Scripts\betsistem fetch-xg --season 2223

# Raporlar: reports/veri_kalite.md ve reports/n_hedefi.md
.venv\Scripts\betsistem quality-report
.venv\Scripts\betsistem sample-size

# Faz 2: walk-forward Poisson ve piyasa karşılaştırması (reports/faz2_poisson.md)
.venv\Scripts\betsistem model-report

# Faz 3: Dixon-Coles, zaman ağırlığı, xG katkı raporu (reports/faz3_model.md)
.venv\Scripts\betsistem faz3-report

# Karar #36: yeni çıkan takım ayarı (reports/faz3_yeni_cikan.md)
.venv\Scripts\betsistem promoted-report

# Faz 4: model seçimi döneminde backtest ve eşik seçimi (reports/faz4_secim.md)
.venv\Scripts\betsistem backtest-select

# Tüm ligler: football-data sezon paketi ve lig taraması (reports/lig_taramasi.md)
.venv\Scripts\betsistem import-zip data_2122.zip --season 2122
.venv\Scripts\betsistem league-screen

# Haftalık: fikstür dosyasını sürümle, sonra İddaa kayıtlarını ekle (şablon: templates/iddaa_kayit_sablonu.xlsx)
.venv\Scripts\betsistem import-fixtures fixtures_20261023_1930.csv
.venv\Scripts\betsistem import-iddaa iddaa_kayitlari.xlsx
.venv\Scripts\betsistem fixtures-log
```

Understat takım adları `src/betsistem/data/team_aliases.csv` ile football-data adlarına eşlenir.
Eşleşmeyen ad olursa yükleme hiçbir şey yazmadan durur; eşleşme bu dosyaya eklenir.

### İddaa kayıtları

Tek şablon: `templates/iddaa_kayit_sablonu.xlsx` (karar #79). Talimatlar şablonun "Nasıl" sayfasında.

- Takım adları football-data yazımıyla girilir; her satır, `fikstur_dosyasi` sütununda adı yazılan ve önce
  `import-fixtures` ile yüklenmiş fikstür dosyasındaki bir maçla eşleşmek zorundadır. Yazım yanlışsa öneri verilir.
- Kayıt zamanı Türkiye saatidir. Ondalık için virgül ya da nokta kullanılabilir.
- Hatalı satır varsa dosyanın hiçbir satırı yazılmaz. Kayıtlar yalnızca eklenir; düzeltme yeni kayıt zamanıyla.
- Fikstür dosyalarının her indirmesi kaydedilir; `fixtures-log` içeriğin ne zaman değiştiğini gösterir (8.4).

### Erişim

football-data.co.uk Türkiye'den erişime engelli olabilir. Bu durumda `fetch` hata verir;
dosyayı (`https://www.football-data.co.uk/mmz4281/2223/E0.csv`) elle edinip `import-raw` ile eklenir.
İçerik CSV başlığı doğrulanmadan saklanmaz, böylece engel sayfası yanlışlıkla veri olarak kaydedilmez.

`tests/fixtures/E0_sample.csv` testler için hazırlanmış örnek dosyadır, gerçek veri yerine kullanılmaz.

## Yapı

- `src/betsistem/data/`: ham veri edinme, şema, yükleyiciler
- `src/betsistem/model/`: piyasa olasılıkları, karar anı, Poisson modeli, walk-forward, metrikler
- `src/betsistem/backtest/`: geriye dönük test (Faz 4)
- `notebooks/`: yalnızca keşif ve raporlama
