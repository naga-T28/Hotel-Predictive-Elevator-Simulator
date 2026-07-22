from elevator_sim.domain.elevator import ElevatorCar


def make_car(**overrides) -> ElevatorCar:
    defaults = dict(
        car_id="C1",
        current_floor=1,
        capacity_people=15,
        seconds_per_floor=2.5,
        start_delay_seconds=1.0,
        door_open_seconds=1.5,
        door_close_seconds=1.5,
        boarding_seconds_per_person=0.7,
        alighting_seconds_per_person=0.6,
    )
    defaults.update(overrides)
    return ElevatorCar(**defaults)


def test_travel_time_same_floor_is_zero():
    car = make_car()
    assert car.travel_time(1) == 0.0


def test_travel_time_formula():
    car = make_car(current_floor=1, start_delay_seconds=1.0, seconds_per_floor=2.5)
    # start_delay + floor_diff * seconds_per_floor
    assert car.travel_time(5) == 1.0 + 4 * 2.5


def test_can_accept_within_capacity():
    car = make_car(capacity_people=2)
    assert car.can_accept(1.0) is True
    assert car.can_accept(2.0) is True
    car.current_load = 2.0
    assert car.can_accept(1.0) is False


def test_add_stop_scan_order_upward():
    car = make_car(current_floor=1)
    car.add_stop(5)
    car.add_stop(3)
    car.add_stop(8)
    # moving up from floor 1: nearer stops should come first
    assert car.stop_queue == [3, 5, 8]


def test_add_stop_deduplicates():
    car = make_car(current_floor=1)
    car.add_stop(5)
    car.add_stop(5)
    assert car.stop_queue == [5]


def test_assign_pickup_adds_stop_and_records_passenger():
    car = make_car(current_floor=1)
    car.assign_pickup(4, "P1")
    assert 4 in car.stop_queue
    assert car.assigned_pickups[4] == ["P1"]
    assert car.assigned_calls == ["P1"]
