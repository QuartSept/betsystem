"""Poisson gol modeli (Maher 1982) ve Dixon-Coles düşük skor düzeltmesi (1997).

log λ_ev  = μ + ev_avantajı + hücum[ev]  − savunma[dep]
log λ_dep = μ +               hücum[dep] − savunma[ev]

Parametreler ağırlıklı Poisson log-olabilirliğini maksimize ederek bulunur. Hücum ve savunma
gücüne L2 cezası uygulanır: hem modeli tanımlı kılar hem de az maçı olan (ör. lige yeni çıkmış)
takımları ortalamaya çeker. Ağırlıklar zaman ağırlığı içindir. Gol yerine xG gibi tam sayı olmayan
hedefler de kullanılabilir (yarı-Poisson olabilirlik; gradyan aynı).

Dixon-Coles: 0-0, 1-0, 0-1, 1-1 skorlarının olasılığı τ ile düzeltilir:
τ(0,0) = 1 − λ_ev·λ_dep·ρ, τ(0,1) = 1 + λ_ev·ρ, τ(1,0) = 1 + λ_dep·ρ, τ(1,1) = 1 − ρ.
ρ iki aşamada bulunur: önce hücum/savunma Poisson ile, sonra ρ gerçek skorlar üzerinden
tek boyutlu maksimum olabilirlikle (λ'lar sabit tutulur).
"""

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize, minimize_scalar
from scipy.stats import poisson

MAX_GOALS = 10


@dataclass
class PoissonModel:
    teams: list[str]
    intercept: float
    home_advantage: float
    attack: np.ndarray
    defence: np.ndarray
    rho: float = 0.0
    # Karar #36: yeni çıkan takımın o sezon hücumuna/savunmasına eklenen sabit kayma.
    promoted_attack: float = 0.0
    promoted_defence: float = 0.0

    def expected_goals_many(self, home, away, home_promoted=None, away_promoted=None) -> tuple[np.ndarray, np.ndarray]:
        """Vektörel λ'lar; eğitimde görülmemiş takımın kendi gücü 0 (ortalama)."""
        idx = {t: i for i, t in enumerate(self.teams)}
        att = np.append(self.attack, 0.0)
        dfn = np.append(self.defence, 0.0)
        hi = np.array([idx.get(t, -1) for t in home])
        ai = np.array([idx.get(t, -1) for t in away])
        fh = np.zeros(len(hi)) if home_promoted is None else np.asarray(home_promoted, dtype=float)
        fa = np.zeros(len(ai)) if away_promoted is None else np.asarray(away_promoted, dtype=float)
        pa, pd_ = self.promoted_attack, self.promoted_defence
        lam_h = np.exp(self.intercept + self.home_advantage + att[hi] + pa * fh - dfn[ai] - pd_ * fa)
        lam_a = np.exp(self.intercept + att[ai] + pa * fa - dfn[hi] - pd_ * fh)
        return lam_h, lam_a

    def expected_goals(self, home: str, away: str, home_promoted=False, away_promoted=False) -> tuple[float, float]:
        lam_h, lam_a = self.expected_goals_many([home], [away], [home_promoted], [away_promoted])
        return float(lam_h[0]), float(lam_a[0])

    def outcome_probabilities(self, home: str, away: str, home_promoted=False, away_promoted=False):
        return outcome_probabilities(*self.expected_goals(home, away, home_promoted, away_promoted), rho=self.rho)


RHO_BOUNDS = (-0.3, 0.3)


def dixon_coles_tau(hg, ag, lam_h, lam_a, rho):
    """Skor başına düzeltme çarpanı τ (dizi girdileri)."""
    hg, ag = np.asarray(hg), np.asarray(ag)
    tau = np.ones(np.broadcast(hg, ag, lam_h, lam_a).shape)
    tau = np.where((hg == 0) & (ag == 0), 1 - lam_h * lam_a * rho, tau)
    tau = np.where((hg == 0) & (ag == 1), 1 + lam_h * rho, tau)
    tau = np.where((hg == 1) & (ag == 0), 1 + lam_a * rho, tau)
    tau = np.where((hg == 1) & (ag == 1), 1 - rho, tau)
    return tau


def fit_rho(lam_h, lam_a, home_goals, away_goals, weights=None) -> float:
    """λ'lar sabitken ρ'nun ağırlıklı maksimum olabilirlik tahmini (yalnızca τ terimi ρ'ya bağlıdır)."""
    hg = np.asarray(home_goals)
    ag = np.asarray(away_goals)
    low = (hg <= 1) & (ag <= 1)
    w = np.ones(len(hg)) if weights is None else np.asarray(weights, dtype=float)
    lh, la, hg, ag, w = np.asarray(lam_h)[low], np.asarray(lam_a)[low], hg[low], ag[low], w[low]

    def nll(rho):
        return -np.sum(w * np.log(np.clip(dixon_coles_tau(hg, ag, lh, la, rho), 1e-10, None)))

    return float(minimize_scalar(nll, bounds=RHO_BOUNDS, method="bounded").x)


def outcome_probabilities(
    lam_home: float, lam_away: float, max_goals: int = MAX_GOALS, rho: float = 0.0
) -> tuple[float, float, float]:
    """Skor matrisinden 1-X-2 olasılıkları; kesilen kuyruk yeniden normalize edilir."""
    goals = np.arange(max_goals + 1)
    matrix = np.outer(poisson.pmf(goals, lam_home), poisson.pmf(goals, lam_away))
    if rho:
        matrix[:2, :2] *= dixon_coles_tau(goals[:2, None], goals[None, :2], lam_home, lam_away, rho)
        matrix = np.clip(matrix, 0, None)
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
    home_promoted=None,
    away_promoted=None,
) -> PoissonModel:
    """home_promoted/away_promoted verilirse yeni çıkan takım kayması (cezasız) da tahmin edilir."""
    teams = sorted(set(home) | set(away))
    idx = {t: i for i, t in enumerate(teams)}
    hi = np.array([idx[t] for t in home])
    ai = np.array([idx[t] for t in away])
    hg = np.asarray(home_goals, dtype=float)
    ag = np.asarray(away_goals, dtype=float)
    w = np.ones_like(hg) if weights is None else np.asarray(weights, dtype=float)
    fh = np.zeros_like(hg) if home_promoted is None else np.asarray(home_promoted, dtype=float)
    fa = np.zeros_like(hg) if away_promoted is None else np.asarray(away_promoted, dtype=float)
    n = len(teams)
    k = 4  # μ, ev avantajı, yeni çıkan hücum kayması, yeni çıkan savunma kayması

    def objective(theta):
        mu, home_adv, pa, pd_ = theta[:k]
        att, dfn = theta[k : k + n], theta[k + n :]
        log_lh = mu + home_adv + att[hi] + pa * fh - dfn[ai] - pd_ * fa
        log_la = mu + att[ai] + pa * fa - dfn[hi] - pd_ * fh
        lh, la = np.exp(log_lh), np.exp(log_la)
        nll = np.sum(w * (lh - hg * log_lh)) + np.sum(w * (la - ag * log_la))
        nll += l2 * (att @ att + dfn @ dfn)

        rh, ra = w * (lh - hg), w * (la - ag)
        grad = np.empty_like(theta)
        grad[0] = rh.sum() + ra.sum()
        grad[1] = rh.sum()
        grad[2] = rh @ fh + ra @ fa
        grad[3] = -(rh @ fa) - (ra @ fh)
        grad[k : k + n] = np.bincount(hi, rh, n) + np.bincount(ai, ra, n) + 2 * l2 * att
        grad[k + n :] = -np.bincount(ai, rh, n) - np.bincount(hi, ra, n) + 2 * l2 * dfn
        return nll, grad

    theta0 = np.zeros(k + 2 * n)
    theta0[0] = np.log(max((hg.mean() + ag.mean()) / 2, 1e-3))
    res = minimize(
        objective, theta0, jac=True, method="L-BFGS-B", options={"ftol": 1e-12, "gtol": 1e-6, "maxiter": 5000}
    )
    if not res.success:
        raise RuntimeError(f"Poisson modeli yakınsamadı: {res.message}")
    th = res.x
    return PoissonModel(
        teams=teams,
        intercept=float(th[0]),
        home_advantage=float(th[1]),
        attack=th[k : k + n],
        defence=th[k + n :],
        promoted_attack=float(th[2]),
        promoted_defence=float(th[3]),
    )
