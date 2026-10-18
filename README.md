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

# İddaa oranları (elle tutulan, birikimli CSV; şablon: templates/iddaa_oranlari.csv)
.venv\Scripts\betsistem import-iddaa iddaa_oranlari.csv
```

Understat takım adları `src/betsistem/data/team_aliases.csv` ile football-data adlarına eşlenir.
Eşleşmeyen ad olursa yükleme hiçbir şey yazmadan durur; eşleşme bu dosyaya eklenir.

### İddaa kayıtları

Her satır, oranın görüldüğü anı (`recorded_at`, saat dilimiyle: `2026-10-16T15:30+03:00`) taşır.
Kayıtlar veritabanında yalnızca eklenir; aynı an ve maç için farklı oran gelirse içe aktarma durur.
Düzeltme gerekiyorsa yeni bir `recorded_at` ile yeni satır eklenir.

```text
recorded_at,match_date,kickoff_time,home_team,away_team,price_home,price_draw,price_away,note
2026-10-16T15:30+03:00,2026-10-18,17:00,Arsenal,Chelsea,1.85,3.60,4.10,
```

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
