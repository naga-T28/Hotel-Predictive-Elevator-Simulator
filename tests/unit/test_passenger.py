from elevator_sim.domain.passenger import Passenger


def test_waiting_and_ride_time_calculation():
    p = Passenger(
        passenger_id="P1",
        hall_arrival_time=10.0,
        origin_floor=5,
        destination_floor=1,
    )
    p.board_time = 25.0
    p.arrival_time = 40.0

    assert p.waiting_time == 15.0
    assert p.ride_time == 15.0
    assert p.total_service_time == 30.0


def test_waiting_time_none_before_boarding():
    p = Passenger(passenger_id="P1", hall_arrival_time=10.0, origin_floor=5, destination_floor=1)
    assert p.waiting_time is None
    assert p.ride_time is None


def test_occupancy_includes_group_and_luggage():
    p = Passenger(
        passenger_id="P1",
        hall_arrival_time=0.0,
        origin_floor=1,
        destination_floor=2,
        group_size=3,
        luggage_factor=1.5,
    )
    assert p.occupancy == 4.5


def test_direction_down():
    p = Passenger(passenger_id="P1", hall_arrival_time=0.0, origin_floor=8, destination_floor=1)
    from elevator_sim.domain.passenger import Direction

    assert p.direction == Direction.DOWN
