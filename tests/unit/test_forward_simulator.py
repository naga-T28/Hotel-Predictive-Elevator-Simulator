from elevator_sim.domain.elevator import ElevatorCar
from elevator_sim.domain.passenger import Passenger
from elevator_sim.predictors.base import PredictedPassenger
from elevator_sim.simulation.forward_simulator import forward_simulate


def make_car(floor=1):
    car = ElevatorCar(
        car_id="C1",
        current_floor=floor,
        capacity_people=15,
        seconds_per_floor=2.5,
        start_delay_seconds=1.0,
        door_open_seconds=1.5,
        door_close_seconds=1.5,
        boarding_seconds_per_person=0.7,
        alighting_seconds_per_person=0.6,
    )
    return car


def test_forward_simulate_estimates_wait_for_assigned_passenger():
    car = make_car(floor=1)
    passenger = Passenger(passenger_id="P1", hall_arrival_time=0.0, origin_floor=3, destination_floor=1)
    car.assign_pickup(3, "P1")

    result = forward_simulate(
        car=car,
        passenger_lookup={"P1": passenger},
        future_passengers=[],
        current_time=0.0,
        horizon_seconds=60.0,
    )

    expected_travel = car.start_delay_seconds + 2 * car.seconds_per_floor
    expected_wait = expected_travel + car.door_open_seconds
    assert result.estimated_wait_times["P1"] == expected_wait
    assert result.mean_wait == expected_wait


def test_forward_simulate_respects_horizon():
    car = make_car(floor=1)
    passenger = Passenger(passenger_id="P1", hall_arrival_time=0.0, origin_floor=8, destination_floor=1)
    car.assign_pickup(8, "P1")

    result = forward_simulate(
        car=car,
        passenger_lookup={"P1": passenger},
        future_passengers=[],
        current_time=0.0,
        horizon_seconds=1.0,
    )

    assert "P1" not in result.estimated_wait_times


def test_forward_simulate_includes_future_passengers():
    car = make_car(floor=1)
    future = PredictedPassenger(
        predicted_arrival_time=5.0, origin_floor=4, destination_floor=1, probability=1.0
    )

    result = forward_simulate(
        car=car,
        passenger_lookup={},
        future_passengers=[future],
        current_time=0.0,
        horizon_seconds=60.0,
    )

    assert len(result.estimated_wait_times) == 1
    assert list(result.estimated_wait_times.values())[0] >= 0
