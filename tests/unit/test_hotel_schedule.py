import numpy as np

from elevator_sim.domain.building import Building
from elevator_sim.domain.hotel_event import HotelEvent
from elevator_sim.traffic.hotel_schedule import HotelTrafficGenerator


def make_checkout_event(**overrides):
    defaults = dict(
        event_id="checkout_001",
        event_type="checkout",
        start_time=1800.0,
        end_time=1800.0,
        source_floors=[2, 3, 4, 5, 6, 7, 8],
        destination_distribution={1: 1.0},
        expected_people=100,
        spread_seconds=600.0,
        group_size=2,
        luggage_factor=1.5,
    )
    defaults.update(overrides)
    return HotelEvent(**defaults)


def test_checkout_event_generates_expected_people_count():
    building = Building.uniform(8, lobby_floor=1)
    rng = np.random.default_rng(0)
    event = make_checkout_event()
    gen = HotelTrafficGenerator(rng=rng, building=building, events=[event])

    arrivals = gen.generate(duration_seconds=3600.0)

    total_people = sum(p.group_size for p in arrivals)
    assert total_people == event.expected_people
    for p in arrivals:
        assert p.origin_floor in event.source_floors
        assert p.destination_floor == 1
        assert p.luggage_factor == 1.5
        assert p.group_id == "checkout_001"


def test_arrivals_are_sorted_and_clamped_to_duration():
    building = Building.uniform(8, lobby_floor=1)
    rng = np.random.default_rng(1)
    event = make_checkout_event(spread_seconds=5000.0)  # wide spread to exercise clamping
    gen = HotelTrafficGenerator(rng=rng, building=building, events=[event])

    duration = 3600.0
    arrivals = gen.generate(duration_seconds=duration)

    times = [p.hall_arrival_time for p in arrivals]
    assert times == sorted(times)
    assert all(0.0 <= t < duration for t in times)


def test_baseline_traffic_is_blended_in_when_enabled():
    building = Building.uniform(8, lobby_floor=1)
    rng = np.random.default_rng(2)
    gen = HotelTrafficGenerator(
        rng=rng, building=building, events=[], baseline_rate_per_hour=200.0, baseline_pattern="down_peak"
    )
    arrivals = gen.generate(duration_seconds=3600.0)
    assert len(arrivals) > 0
    assert all(p.destination_floor == 1 for p in arrivals)


def test_destination_never_equals_origin():
    building = Building.uniform(8, lobby_floor=1)
    rng = np.random.default_rng(3)
    event = make_checkout_event(
        source_floors=[1, 2],
        destination_distribution={1: 0.5, 2: 0.5},
        expected_people=50,
        group_size=1,
    )
    gen = HotelTrafficGenerator(rng=rng, building=building, events=[event])
    arrivals = gen.generate(duration_seconds=3600.0)
    assert all(p.origin_floor != p.destination_floor for p in arrivals)
