"""Komut satırı: betsistem <komut> ..."""

import argparse
import sys
from pathlib import Path

from betsistem.config import DB_PATH, LEAGUES, PROJECT_ROOT, PROTOTYPE_SEASON, season_label
from betsistem.data.db import UnknownTeamError, connect, init_db
from betsistem.data.football_data import load_football_data
from betsistem.data.iddaa import import_iddaa
from betsistem.backtest import sample_size
from betsistem.data import quality
from betsistem.model import evaluation, experiments
from betsistem.data.raw import RawDataError, download_football_data, import_football_data
from betsistem.data.understat import fetch_understat, load_understat


def _print_load(season: str, version_id: int, result) -> None:
    print(
        f"{season_label(season)}: veri sürümü #{version_id}, {result.matches} maç, {result.odds} oran"
        f" ({len(result.odds_columns)} oran sütunu, {result.skipped_invalid_prices} geçersiz fiyat atlandı)"
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="betsistem")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="SQLite dosyası")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="Şemayı oluştur")

    p_fetch = sub.add_parser("fetch", help="football-data CSV'sini indir ve yükle")
    p_fetch.add_argument("--league", default="E0", choices=sorted(LEAGUES))
    p_fetch.add_argument("--season", nargs="+", default=[PROTOTYPE_SEASON], help="Örn. 2223 2324")

    p_import = sub.add_parser("import-raw", help="Elle indirilmiş football-data CSV'sini ekle ve yükle")
    p_import.add_argument("file", type=Path)
    p_import.add_argument("--league", default="E0", choices=sorted(LEAGUES))
    p_import.add_argument("--season", required=True, help="Örn. 2223")

    p_xg = sub.add_parser("fetch-xg", help="Understat xG verisini indir ve yükle (önce football-data yüklenmeli)")
    p_xg.add_argument("--league", default="E0", choices=sorted(LEAGUES))
    p_xg.add_argument("--season", nargs="+", default=[PROTOTYPE_SEASON])

    p_q = sub.add_parser("quality-report", help="Veri kalite raporunu yaz")
    p_q.add_argument("--out", type=Path, default=PROJECT_ROOT / "reports" / "veri_kalite.md")

    p_n = sub.add_parser("sample-size", help="Minimum bahis sayısı N raporunu yaz (model seçimi dönemi)")
    p_n.add_argument("--out", type=Path, default=PROJECT_ROOT / "reports" / "n_hedefi.md")

    p_iddaa = sub.add_parser("import-iddaa", help="Elle tutulan İddaa oran CSV'sini ekle (templates/iddaa_oranlari.csv)")
    p_iddaa.add_argument("file", type=Path)

    p_m = sub.add_parser("model-report", help="Faz 2: walk-forward Poisson tahmini ve piyasa karşılaştırma raporu")
    p_m.add_argument("--out", type=Path, default=PROJECT_ROOT / "reports" / "faz2_poisson.md")

    p_m3 = sub.add_parser("faz3-report", help="Faz 3: Dixon-Coles, zaman ağırlığı ve xG katkı raporu")
    p_m3.add_argument("--out", type=Path, default=PROJECT_ROOT / "reports" / "faz3_model.md")

    args = parser.parse_args(argv)
    conn = connect(args.db)
    init_db(conn)

    try:
        if args.command == "init-db":
            print(f"Şema hazır: {args.db}")
        elif args.command == "fetch":
            for season in args.season:
                version_id = download_football_data(conn, args.league, season)
                _print_load(season, version_id, load_football_data(conn, version_id))
        elif args.command == "import-raw":
            version_id = import_football_data(conn, args.league, args.season, args.file)
            _print_load(args.season, version_id, load_football_data(conn, version_id))
        elif args.command == "fetch-xg":
            for season in args.season:
                version_id = fetch_understat(conn, args.league, season)
                res = load_understat(conn, version_id)
                print(
                    f"{season_label(season)}: xG veri sürümü #{version_id}, {res.matched} maç eşleşti,"
                    f" {res.not_played} oynanmamış, {len(res.date_mismatches)} tarih uyuşmazlığı,"
                    f" {len(res.missing_in_football_data)} maç football-data'da yok"
                )
                for line in res.missing_in_football_data:
                    print(f"  football-data'da yok: {line}")
                for line in res.date_mismatches:
                    print(f"  tarih farkı: {line}")
        elif args.command == "quality-report":
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(quality.render_report(conn), encoding="utf-8")
            print(f"Rapor yazıldı: {args.out}")
        elif args.command == "sample-size":
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(sample_size.render_report(conn), encoding="utf-8")
            print(f"Rapor yazıldı: {args.out}")
        elif args.command == "model-report":
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(evaluation.render_report(conn), encoding="utf-8")
            print(f"Rapor yazıldı: {args.out}")
        elif args.command == "faz3-report":
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(experiments.render_report(conn), encoding="utf-8")
            print(f"Rapor yazıldı: {args.out}")
        elif args.command == "import-iddaa":
            res = import_iddaa(conn, args.file)
            print(f"İddaa: {res.added} yeni kayıt, {res.already_present} zaten vardı")
    except (RawDataError, UnknownTeamError) as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
