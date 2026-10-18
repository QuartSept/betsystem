import pytest

from betsistem.backtest.sample_size import required_n


def test_required_n_matches_formula():
    # (1.645 + 0.842)^2 * (0.1 / 0.02)^2 ≈ 154.6
    assert required_n(0.1, 0.02) == 155


def test_required_n_scales_with_inverse_square_of_delta():
    assert required_n(0.1, 0.01) == pytest.approx(4 * required_n(0.1, 0.02), abs=3)
