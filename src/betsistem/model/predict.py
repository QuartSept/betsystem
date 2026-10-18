"""Walk-forward tahmin: her maç, yalnızca karar anından önceki maçlarla eğitilmiş modelle tahmin edilir."""

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from betsistem.config import MODEL_SELECTION_SEASONS
from betsistem.model.poisson import fit_poisson, fit_rho
from betsistem.model.timeline import assert_unlocked, decision_date


@dataclass(frozen=True)
class ModelConfig:
    l2: float = 1.0
    window_days: int = 730  # eğitim penceresi: karar gününden önceki gün sayısı
    xi: float = 0.0  # zaman ağırlığı: w = exp(−ξ · gün farkı); 0 = ağırlıksız
    xg_weight: float = 0.0  # hedef = (1 − a)·gol + a·xG; 0 = yalnızca gol
    dixon_coles: bool = False
    promoted_effect: bool = False  # karar #36

    def key(self) -> str:
        d = asdict(self)
        if not d["promoted_effect"]:
            d.pop("promoted_effect")  # eski tahminlerin anahtarı değişmesin
        return json.dumps(d, sort_keys=True)


def load_matches(conn: sqlite3.Connection, league: str = "E0") -> pd.DataFrame:
    df = pd.read_sql(
        """
        SELECT m.id AS match_id, m.season, m.match_date, h.name AS home, a.name AS away, m.fthg, m.ftag, m.ftr,
               x.home_xg, x.away_xg
        FROM matches m JOIN teams h ON h.id = m.home_team_id JOIN teams a ON a.id = m.away_team_id
        LEFT JOIN match_xg x ON x.match_id = m.id AND x.source = 'understat'
        WHERE m.league = ? ORDER BY m.match_date, m.id
        """,
        conn,
        params=(league,),
    )
    df["match_date"] = pd.to_datetime(df["match_date"]).dt.date
    return df


def _previous_season(code: str) -> str:
    start = int(code[:2])
    return f"{(start - 1) % 100:02d}{start:02d}"


def promoted_flags(matches: pd.DataFrame) -> pd.DataFrame:
    """Maç başına ev/deplasman takımının o sezon yeni çıkan olup olmadığı (karar #36).

    Bir önceki sezon veride yoksa (ilk sezon) kimse yeni çıkan sayılmaz. Hangi takımların ligde
    olduğu sezon başında bilinir; bu bilgi sızıntı değildir.
    """
    teams = {
        season: set(g.home) | set(g.away) for season, g in matches.groupby("season")
    }
    promoted = {
        season: (members - teams[_previous_season(season)]) if _previous_season(season) in teams else set()
        for season, members in teams.items()
    }
    return pd.DataFrame({
        "home_promoted": [h in promoted[s] for h, s in zip(matches.home, matches.season)],
        "away_promoted": [a in promoted[s] for a, s in zip(matches.away, matches.season)],
    }, index=matches.index)


def _targets(train: pd.DataFrame, xg_weight: float) -> tuple[np.ndarray, np.ndarray]:
    """Eğitim hedefi. xG'si olmayan maçta gol kullanılır."""
    hg, ag = train.fthg.to_numpy(float), train.ftag.to_numpy(float)
    if xg_weight == 0:
        return hg, ag
    hx = train.home_xg.fillna(train.fthg).to_numpy(float)
    ax = train.away_xg.fillna(train.ftag).to_numpy(float)
    return (1 - xg_weight) * hg + xg_weight * hx, (1 - xg_weight) * ag + xg_weight * ax


def walk_forward(
    matches: pd.DataFrame, seasons=MODEL_SELECTION_SEASONS, config: ModelConfig = ModelConfig()
) -> pd.DataFrame:
    assert_unlocked(seasons)
    matches = matches.join(promoted_flags(matches))
    played = matches.dropna(subset=["fthg", "ftag"])
    targets = matches[matches.season.isin(seasons)].copy()
    targets["decision_date"] = targets["match_date"].map(decision_date)

    rows = []
    for dd, group in targets.groupby("decision_date", sort=True):
        start = dd - timedelta(days=config.window_days)
        train = played[(played.match_date < dd) & (played.match_date >= start)]
        if train.empty:
            continue
        age = np.array([(dd - d).days for d in train.match_date], dtype=float)
        weights = np.exp(-config.xi * age)
        y_home, y_away = _targets(train, config.xg_weight)
        flags = {}
        if config.promoted_effect:
            flags = {"home_promoted": train.home_promoted.to_numpy(), "away_promoted": train.away_promoted.to_numpy()}
        model = fit_poisson(
            train.home.tolist(), train.away.tolist(), y_home, y_away, l2=config.l2, weights=weights, **flags
        )
        if config.dixon_coles:
            lam_h, lam_a = model.expected_goals_many(train.home, train.away)
            model.rho = fit_rho(lam_h, lam_a, train.fthg.astype(int), train.ftag.astype(int), weights)
        for m in group.itertuples(index=False):
            fh, fa = (m.home_promoted, m.away_promoted) if config.promoted_effect else (False, False)
            lam_h, lam_a = model.expected_goals(m.home, m.away, fh, fa)
            p_h, p_d, p_a = model.outcome_probabilities(m.home, m.away, fh, fa)
            rows.append(
                {
                    "match_id": m.match_id,
                    "decision_date": dd.isoformat(),
                    "train_matches": len(train),
                    "p_home": p_h,
                    "p_draw": p_d,
                    "p_away": p_a,
                    "lambda_home": lam_h,
                    "lambda_away": lam_a,
                    "rho": model.rho,
                    "promoted_attack": model.promoted_attack,
                    "promoted_defence": model.promoted_defence,
                }
            )
    return pd.DataFrame(rows)


def save_predictions(conn: sqlite3.Connection, model: str, config_key: str, preds: pd.DataFrame) -> int:
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with conn:
        conn.executemany(
            "INSERT OR REPLACE INTO predictions (model, config, match_id, decision_date, train_matches,"
            " p_home, p_draw, p_away, lambda_home, lambda_away, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (model, config_key, int(r.match_id), r.decision_date, int(r.train_matches), r.p_home, r.p_draw,
                 r.p_away, r.lambda_home, r.lambda_away, created)
                for r in preds.itertuples(index=False)
            ],
        )
    return len(preds)
