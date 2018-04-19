import random

from future.builtins import range
from pytest import approx, raises

from clkhash.stats import OnlineMeanVariance


def test_empty():
    stats = OnlineMeanVariance()
    assert stats.mean() == 0
    assert stats.variance() == 0


def test_one_element():
    x = [7.5]
    stats = OnlineMeanVariance()
    stats.update(x)
    assert stats.mean() == x[0]
    assert stats.variance() == 0


def test_same_entry():
    x = [3.1428 for _ in range(20)]
    stats = OnlineMeanVariance()
    stats.update(x)
    assert stats.mean() == approx(x[0])
    assert stats.variance() == approx(0)


def test_nan():
    with raises(ValueError):
        stats = OnlineMeanVariance()
        stats.update([float('nan')])


def test_random_order():
    x = [i for i in range(1000)]
    stats_orig = OnlineMeanVariance()
    stats_orig.update(x)
    random.shuffle(x)
    stats_shuffle = OnlineMeanVariance()
    stats_shuffle.update(x)
    assert stats_orig.mean() == stats_shuffle.mean()
    assert stats_orig.variance() == stats_shuffle.variance()


def test_online_ness():
    x = [i for i in range(1000)]
    stats_orig = OnlineMeanVariance()
    stats_orig.update(x)
    random.shuffle(x)
    d = 50
    xs = [x[i*d:i*d+d] for i in range(20)]
    stats = OnlineMeanVariance()
    for xi in xs:
        stats.update(xi)
    assert stats_orig.mean() == approx(stats.mean())
    assert stats_orig.variance() == approx(stats.variance())


def test_online_floats():
    x = [random.gauss(mu=42, sigma=12.3) for _ in range(100000)]
    stats_orig = OnlineMeanVariance()
    stats_orig.update(x)
    assert abs(stats_orig.mean() - 42) < 1
    assert abs(stats_orig.std() - 12.3) < 1
    random.shuffle(x)
    d = 50
    xs = [x[i * d:i * d + d] for i in range(2000)]
    stats = OnlineMeanVariance()
    for xi in xs:
        stats.update(xi)
    assert stats_orig.mean() == approx(stats.mean())
    assert stats_orig.variance() == approx(stats.variance())
