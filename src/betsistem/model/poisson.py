"""Bağımsız Poisson gol modeli (Maher 1982).

log λ_ev  = μ + ev_avantajı + hücum[ev]  − savunma[dep]
log λ_dep = μ +               hücum[dep] − savunma[ev]

Parametreler ağırlıklı Poisson log-olabilirliğini maksimize ederek bulunur. Hücum ve savunma
gücüne L2 cezası uygulanır: hem modeli tanımlı kılar hem de az maçı olan (ör. lige yeni çıkmış)
takımları ortalamaya çeker. Ağırlıklar Faz 3'teki zaman ağırlığı için hazır bekler.
"""

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize
from scipy.stats import poisson

MAX_GOALS = 10


@dataclass
class PoissonModel:
    teams: list[str]
    intercept: float
    home_advantage: float
    attack: np.ndarray
    defence: np.ndarray

    def _index(self, team: str) -> int | None:
        try:
            return self.teams.index(team)
        except ValueError:
            return None  # eğitimde görülmemiş takım: ortalama güç

    def expected_goals(self, home: str, away: str) -> tuple[float, float]:
        h, a = self._index(home), self._index(away)
        att_h = self.attack[h] if h is not None else 0.0
        def_h = self.defence[h] if h is not None else 0.0
        att_a = self.attack[a] if a is not None else 0.0
        def_a = self.defence[a] if a is not None else 0.0
        lam_h = np.exp(self.intercept + self.home_advantage + att_h - def_a)
        lam_a = np.exp(self.intercept + att_a - def_h)
        return float(lam_h), float(lam_a)

    def outcome_probabilities(self, home: str, away: str) -> tuple[float, float, float]:
        return outcome_probabilities(*self.expected_goals(home, away))


def outcome_probabilities(lam_home: float, lam_away: float, max_goals: int = MAX_GOALS) -> tuple[float, float, float]:
    """Skor matrisinden 1-X-2 olasılıkları; kesilen kuyruk yeniden normalize edilir."""
    goals = np.arange(max_goals + 1)
    matrix = np.outer(poisson.pmf(goals, lam_home), poisson.pmf(goals, lam_away))
    p_home = np.tril(matrix, -1).sum()
    p_draw = np.trace(matrix)
    p_away = np.triu(matrix, 1).sum()
    total = p_home + p_draw + p_away
    return float(p_home / total), float(p_draw / total), float(p_away / total)


def fit_poisson(
    home: list[str],
    away: list[str],
    home_goals,
    away_goals,
    *,
    l2: float = 1.0,
    weights=None,
) -> PoissonModel:
    teams = sorted(set(home) | set(away))
    idx = {t: i for i, t in enumerate(teams)}
    hi = np.array([idx[t] for t in home])
    ai = np.array([idx[t] for t in away])
    hg = np.asarray(home_goals, dtype=float)
    ag = np.asarray(away_goals, dtype=float)
    w = np.ones_like(hg) if weights is None else np.asarray(weights, dtype=float)
    n = len(teams)

    def objective(theta):
        mu, home_adv = theta[0], theta[1]
        att, dfn = theta[2 : 2 + n], theta[2 + n :]
        log_lh = mu + home_adv + att[hi] - dfn[ai]
        log_la = mu + att[ai] - dfn[hi]
        lh, la = np.exp(log_lh), np.exp(log_la)
        nll = np.sum(w * (lh - hg * log_lh)) + np.sum(w * (la - ag * log_la))
        nll += l2 * (att @ att + dfn @ dfn)

        rh, ra = w * (lh - hg), w * (la - ag)
        grad = np.empty_like(theta)
        grad[0] = rh.sum() + ra.sum()
        grad[1] = rh.sum()
        grad[2 : 2 + n] = np.bincount(hi, rh, n) + np.bincount(ai, ra, n) + 2 * l2 * att
        grad[2 + n :] = -np.bincount(ai, rh, n) - np.bincount(hi, ra, n) + 2 * l2 * dfn
        return nll, grad

    theta0 = np.zeros(2 + 2 * n)
    theta0[0] = np.log(max((hg.mean() + ag.mean()) / 2, 1e-3))
    res = minimize(objective, theta0, jac=True, method="L-BFGS-B", options={"ftol": 1e-12, "gtol": 1e-6, "maxiter": 5000})
    if not res.success:
        raise RuntimeError(f"Poisson modeli yakınsamadı: {res.message}")
    th = res.x
    return PoissonModel(
        teams=teams,
        intercept=float(th[0]),
        home_advantage=float(th[1]),
        attack=th[2 : 2 + n],
        defence=th[2 + n :],
    )
