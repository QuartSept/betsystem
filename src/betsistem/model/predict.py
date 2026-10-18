"""Walk-forward tahmin: her maç, yalnızca karar anından önceki maçlarla eğitilmiş modelle tahmin edilir."""

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from betsistem.config import MODEL_SELECTION_SEASONS
from betsistem.model.poisson import fit_poisson
from betsistem.model.timeline import assert_unlocked, decision_date


@dataclass(frozen=True)
class PoissonConfig:
    l2: float = 1.0
    window_days: int = 730  # eğitim penceresi: karar gününden önceki ~2 sezon

    def key(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


def load_matches(conn: sqlite3.Connection, league: str = "E0") -> pd.DataFrame:
    df = pd.read_sql(
        """
        SELECT m.id AS match_id, m.season, m.match_date, h.name AS home, a.name AS away, m.fthg, m.ftag, m.ftr
        FROM matches m JOIN teams h ON h.id = m.home_team_id JOIN teams a ON a.id = m.away_team_id
        WHERE m.league = ? ORDER BY m.match_date, m.id
        """,
        conn,
        params=(league,),
    )
    df["match_date"] = pd.to_datetime(df["match_date"]).dt.date
    return df


def walk_forward_poisson(
    matches: pd.DataFrame, seasons=MODEL_SELECTION_SEASONS, config: PoissonConfig = PoissonConfig()
) -> pd.DataFrame:
    assert_unlocked(seasons)
    played = matches.dropna(subset=["fthg", "ftag"])
    targets = matches[matches.season.isin(seasons)].copy()
    targets["decision_date"] = targets["match_date"].map(decision_date)

    rows = []
    for dd, group in targets.groupby("decision_date", sort=True):
        start = dd - timedelta(days=config.window_days)
        train = played[(played.match_date < dd) & (played.match_date >= start)]
        if train.empty:
            continue
        model = fit_poisson(
            train.home.tolist(), train.away.tolist(), train.fthg, train.ftag, l2=config.l2
        )
        for m in group.itertuples(index=False):
            lam_h, lam_a = model.expected_goals(m.home, m.away)
            p_h, p_d, p_a = model.outcome_probabilities(m.home, m.away)
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
