import numpy as np

from elevator_sim.domain.building import Building
from elevator_sim.traffic.poisson import PoissonTrafficGenerator


def test_down_peak_generates_only_upper_to_lobby():
    building = Building.uniform(8, lobby_floor=1)
    rng = np.random.default_rng(1)
    gen = PoissonTrafficGenerator(rng, building, "down_peak", total_arrival_rate_per_hour=453.6)
    passengers = gen.generate(3600)

    assert len(passengers) > 0
    for p in passengers:
        assert p.destination_floor == 1
        assert p.origin_floor != 1

    # sorted by arrival time
    times = [p.hall_arrival_time for p in passengers]
    assert times == sorted(times)


def test_reproducibility_with_fixed_seed():
    building = Building.uniform(8, lobby_floor=1)
    gen1 = PoissonTrafficGenerator(np.random.default_rng(7), building, "down_peak", 453.6)
    gen2 = PoissonTrafficGenerator(np.random.default_rng(7), building, "down_peak", 453.6)

    p1 = gen1.generate(1800)
    p2 = gen2.generate(1800)

    assert [p.hall_arrival_time for p in p1] == [p.hall_arrival_time for p in p2]
    assert [p.origin_floor for p in p1] == [p.origin_floor for p in p2]


def test_arrival_rate_is_approximately_correct():
    building = Building.uniform(8, lobby_floor=1)
    rng = np.random.default_rng(123)
    rate_per_hour = 453.6
    gen = PoissonTrafficGenerator(rng, building, "down_peak", total_arrival_rate_per_hour=rate_per_hour)
    duration = 3600.0 * 10
    passengers = gen.generate(duration)

    observed_rate_per_hour = len(passengers) / (duration / 3600.0)
    assert abs(observed_rate_per_hour - rate_per_hour) / rate_per_hour < 0.05
