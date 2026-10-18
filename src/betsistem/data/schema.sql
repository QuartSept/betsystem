-- Betsistem SQLite şeması. Tüm tablolar idempotent oluşturulur.

-- Her ham dosya bir veri sürümüdür (izlenebilirlik: kaynak + sha256 + indirme zamanı).
CREATE TABLE IF NOT EXISTS data_versions (
    id            INTEGER PRIMARY KEY,
    source        TEXT NOT NULL,              -- 'football-data'
    league        TEXT NOT NULL,              -- 'E0'
    season        TEXT NOT NULL,              -- '2223'
    origin        TEXT NOT NULL,              -- indirme URL'si veya 'manual:<dosya adı>'
    file_path     TEXT NOT NULL,              -- proje köküne göre göreli yol
    sha256        TEXT NOT NULL,
    acquired_at   TEXT NOT NULL,              -- ISO 8601, UTC
    UNIQUE (source, league, season, sha256)
);

-- Kanonik takım adları. Kaynaklara özgü yazımlar team_aliases'ta.
CREATE TABLE IF NOT EXISTS teams (
    id    INTEGER PRIMARY KEY,
    name  TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS team_aliases (
    source   TEXT NOT NULL,                   -- 'football-data', 'understat', ...
    alias    TEXT NOT NULL,
    team_id  INTEGER NOT NULL REFERENCES teams(id),
    PRIMARY KEY (source, alias)
);

CREATE TABLE IF NOT EXISTS matches (
    id               INTEGER PRIMARY KEY,
    league           TEXT NOT NULL,
    season           TEXT NOT NULL,
    match_date       TEXT NOT NULL,           -- YYYY-MM-DD
    kickoff_time     TEXT,                    -- HH:MM, İngiltere saati (football-data); yoksa NULL
    home_team_id     INTEGER NOT NULL REFERENCES teams(id),
    away_team_id     INTEGER NOT NULL REFERENCES teams(id),
    fthg             INTEGER,
    ftag             INTEGER,
    ftr              TEXT CHECK (ftr IN ('H', 'D', 'A')),
    hthg             INTEGER,
    htag             INTEGER,
    referee          TEXT,
    home_shots       INTEGER,
    away_shots       INTEGER,
    home_shots_on_target INTEGER,
    away_shots_on_target INTEGER,
    data_version_id  INTEGER NOT NULL REFERENCES data_versions(id),
    UNIQUE (league, season, home_team_id, away_team_id)
);

-- Uzun biçim oran tablosu: satır başına tek fiyat.
-- timing: 'early' = football-data'nın erken oran saati (hafta sonu için Cuma öğleden sonra,
-- hafta içi için Salı; karar #6), 'closing' = kapanış.
-- recorded_at: kesin kayıt zamanı biliniyorsa; football-data için NULL.
CREATE TABLE IF NOT EXISTS odds (
    id               INTEGER PRIMARY KEY,
    match_id         INTEGER NOT NULL REFERENCES matches(id),
    source           TEXT NOT NULL,
    bookmaker        TEXT NOT NULL,           -- kaynaktaki kod: 'PS', 'B365', 'Avg', 'Max', ...
    market           TEXT NOT NULL,           -- '1X2' veya 'OU25' (2.5 alt/üst, karar #75)
    outcome          TEXT NOT NULL CHECK (outcome IN ('H', 'D', 'A', 'O', 'U')),
    timing           TEXT NOT NULL CHECK (timing IN ('early', 'closing')),
    price            REAL NOT NULL CHECK (price > 1.0),
    recorded_at      TEXT,
    data_version_id  INTEGER NOT NULL REFERENCES data_versions(id),
    UNIQUE (match_id, source, bookmaker, market, outcome, timing)
);

CREATE INDEX IF NOT EXISTS idx_matches_season ON matches (league, season);
CREATE INDEX IF NOT EXISTS idx_odds_match ON odds (match_id);

-- Maç başına gol beklentisi. npxG penaltısız xG'dir.
CREATE TABLE IF NOT EXISTS match_xg (
    match_id         INTEGER NOT NULL REFERENCES matches(id),
    source           TEXT NOT NULL,           -- 'understat'
    external_id      TEXT,                    -- kaynaktaki maç id'si
    home_xg          REAL NOT NULL,
    away_xg          REAL NOT NULL,
    home_npxg        REAL,
    away_npxg        REAL,
    data_version_id  INTEGER NOT NULL REFERENCES data_versions(id),
    PRIMARY KEY (match_id, source)
);

-- İddaa oranları (karar #12, #79). Tek kaynak: templates/iddaa_kayit_sablonu.xlsx. Yalnızca eklenir.
-- Takım adları football-data yazımıyla girilir ve referans fikstür dosyasındaki maçla eşleşmek zorundadır.
CREATE TABLE IF NOT EXISTS iddaa_odds_log (
    id                   INTEGER PRIMARY KEY,
    recorded_at          TEXT NOT NULL,       -- oranın görüldüğü an, ISO 8601, Türkiye saati (+03:00)
    league               TEXT NOT NULL,       -- football-data lig kodu: 'E0', 'T1'
    match_date           TEXT NOT NULL,       -- YYYY-MM-DD
    kickoff_time         TEXT,                -- HH:MM, Türkiye saati
    home_team            TEXT NOT NULL,       -- football-data yazımı
    away_team            TEXT NOT NULL,
    price_home           REAL NOT NULL CHECK (price_home > 1.0),
    price_draw           REAL NOT NULL CHECK (price_draw > 1.0),
    price_away           REAL NOT NULL CHECK (price_away > 1.0),
    mbs                  INTEGER NOT NULL CHECK (mbs >= 1),
    fixtures_version_id  INTEGER NOT NULL REFERENCES data_versions(id),  -- referans fikstür dosyası
    note                 TEXT,
    data_version_id      INTEGER NOT NULL REFERENCES data_versions(id),  -- kaydın geldiği Excel dosyası
    UNIQUE (recorded_at, home_team, away_team)
);

CREATE TRIGGER IF NOT EXISTS iddaa_odds_log_no_update BEFORE UPDATE ON iddaa_odds_log
BEGIN SELECT RAISE(ABORT, 'iddaa_odds_log yalnızca eklenir'); END;

CREATE TRIGGER IF NOT EXISTS iddaa_odds_log_no_delete BEFORE DELETE ON iddaa_odds_log
BEGIN SELECT RAISE(ABORT, 'iddaa_odds_log yalnızca eklenir'); END;

-- Model tahminleri. config, modelin tüm ayarlarını içeren JSON'dur; aynı ayarla yeniden
-- üretilen tahmin eskisinin yerine geçer (üretim deterministik).
CREATE TABLE IF NOT EXISTS predictions (
    model            TEXT NOT NULL,           -- 'poisson'
    config           TEXT NOT NULL,
    match_id         INTEGER NOT NULL REFERENCES matches(id),
    decision_date    TEXT NOT NULL,           -- modelin veri gördüğü son gün (hariç)
    train_matches    INTEGER NOT NULL,
    p_home           REAL NOT NULL,
    p_draw           REAL NOT NULL,
    p_away           REAL NOT NULL,
    lambda_home      REAL,
    lambda_away      REAL,
    created_at       TEXT NOT NULL,
    PRIMARY KEY (model, config, match_id)
);

-- Kilitli final setinin açılış kaydı (karar #42). Lig başına tek satır; satır silinemez,
-- sonuç alanı yalnızca bir kez yazılabilir.
CREATE TABLE IF NOT EXISTS final_set_runs (
    league       TEXT PRIMARY KEY,
    opened_at    TEXT NOT NULL,
    config       TEXT NOT NULL,
    threshold    REAL NOT NULL,
    git_commit   TEXT,
    result_json  TEXT
);

CREATE TRIGGER IF NOT EXISTS final_set_runs_no_delete BEFORE DELETE ON final_set_runs
BEGIN SELECT RAISE(ABORT, 'final_set_runs silinemez'); END;

CREATE TRIGGER IF NOT EXISTS final_set_runs_result_once BEFORE UPDATE ON final_set_runs
WHEN OLD.result_json IS NOT NULL OR NEW.league IS NOT OLD.league OR NEW.opened_at IS NOT OLD.opened_at
     OR NEW.config IS NOT OLD.config OR NEW.threshold IS NOT OLD.threshold
BEGIN SELECT RAISE(ABORT, 'final_set_runs yalnızca sonucu bir kez yazmak için güncellenebilir'); END;

-- football-data haftalık fikstür dosyası indirmeleri (karar #80). Aynı içerik tek veri sürümüdür;
-- her indirme ayrıca kaydedilir, böylece dosyanın ne zaman değiştiği sha karşılaştırmasıyla bulunur (8.4).
CREATE TABLE IF NOT EXISTS fixture_downloads (
    id               INTEGER PRIMARY KEY,
    data_version_id  INTEGER NOT NULL REFERENCES data_versions(id),
    file_name        TEXT NOT NULL UNIQUE,
    downloaded_at    TEXT NOT NULL,           -- ISO 8601, Türkiye saati
    imported_at      TEXT NOT NULL
);

-- Faz 11 penceresinin (2025/26–2026/27) fikir başına tek seferlik açılışı (karar #81).
CREATE TABLE IF NOT EXISTS faz11_runs (
    idea         TEXT PRIMARY KEY,
    opened_at    TEXT NOT NULL,
    config       TEXT NOT NULL,
    git_commit   TEXT,
    result_json  TEXT
);

CREATE TRIGGER IF NOT EXISTS faz11_runs_no_delete BEFORE DELETE ON faz11_runs
BEGIN SELECT RAISE(ABORT, 'faz11_runs silinemez'); END;

CREATE TRIGGER IF NOT EXISTS faz11_runs_result_once BEFORE UPDATE ON faz11_runs
WHEN OLD.result_json IS NOT NULL OR NEW.idea IS NOT OLD.idea OR NEW.opened_at IS NOT OLD.opened_at
     OR NEW.config IS NOT OLD.config
BEGIN SELECT RAISE(ABORT, 'faz11_runs yalnızca sonucu bir kez yazmak için güncellenebilir'); END;

-- Faz 10 testlerinin tek seferlik çalıştırma kaydı (karar #83).
CREATE TABLE IF NOT EXISTS faz10_runs (
    test         TEXT PRIMARY KEY,
    run_at       TEXT NOT NULL,
    git_commit   TEXT,
    result       TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS faz10_runs_no_delete BEFORE DELETE ON faz10_runs
BEGIN SELECT RAISE(ABORT, 'faz10_runs silinemez'); END;

CREATE TRIGGER IF NOT EXISTS faz10_runs_no_update BEFORE UPDATE ON faz10_runs
BEGIN SELECT RAISE(ABORT, 'faz10_runs değiştirilemez'); END;
