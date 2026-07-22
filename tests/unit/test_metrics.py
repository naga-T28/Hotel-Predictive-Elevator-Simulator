from elevator_sim.domain.passenger import Passenger, PassengerStatus
from elevator_sim.metrics.passenger_metrics import compute_passenger_metrics


def make_served(pid, hall_arrival, board, arrival):
    p = Passenger(passenger_id=pid, hall_arrival_time=hall_arrival, origin_floor=5, destination_floor=1)
    p.board_time = board
    p.arrival_time = arrival
    p.status = PassengerStatus.ARRIVED
    return p


def test_compute_passenger_metrics_basic():
    passengers = {
        "P1": make_served("P1", 10.0, 20.0, 30.0),  # wait 10, ride 10
        "P2": make_served("P2", 10.0, 40.0, 50.0),  # wait 30, ride 10
    }
    summary = compute_passenger_metrics(passengers, warmup_seconds=0.0, duration_seconds=3600.0)

    assert summary.average_waiting_time == 20.0
    assert summary.transported_count == 2
    assert summary.left_behind_count == 0
    assert summary.pct_waited_over_30s == 0.5


def test_compute_passenger_metrics_excludes_warmup():
    early = make_served("P1", 5.0, 10.0, 15.0)  # before warmup, excluded
    late = make_served("P2", 100.0, 110.0, 115.0)  # within window

    summary = compute_passenger_metrics(
        {"P1": early, "P2": late}, warmup_seconds=50.0, duration_seconds=3600.0
    )

    assert summary.evaluated_passenger_count == 1
    assert summary.transported_count == 1


def test_compute_passenger_metrics_left_behind_rate():
    left = Passenger(passenger_id="P1", hall_arrival_time=10.0, origin_floor=5, destination_floor=1)
    left.status = PassengerStatus.LEFT_BEHIND
    served = make_served("P2", 10.0, 20.0, 30.0)

    summary = compute_passenger_metrics(
        {"P1": left, "P2": served}, warmup_seconds=0.0, duration_seconds=3600.0
    )

    assert summary.left_behind_count == 1
    assert summary.left_behind_rate == 0.5
