from elevator_sim.domain.building import Building
from elevator_sim.domain.elevator import ElevatorCar
from elevator_sim.domain.hall_call import HallCall
from elevator_sim.domain.passenger import Direction, Passenger, PassengerStatus
from elevator_sim.predictors.base import PredictedPassenger
from elevator_sim.schedulers.myopic import MyopicScheduler
from elevator_sim.schedulers.nearest_car import NearestCarScheduler
from elevator_sim.schedulers.predictive import PredictiveScheduler
from elevator_sim.simulation.state import SimulationState


def make_car(car_id, floor, capacity=15):
    return ElevatorCar(
        car_id=car_id,
        current_floor=floor,
        capacity_people=capacity,
        seconds_per_floor=2.5,
        start_delay_seconds=1.0,
        door_open_seconds=1.5,
        door_close_seconds=1.5,
        boarding_seconds_per_person=0.7,
        alighting_seconds_per_person=0.6,
    )


def make_state(cars, passenger=None, call=None):
    building = Building.uniform(8, lobby_floor=1)
    passengers = {passenger.passenger_id: passenger} if passenger else {}
    hall_calls = {call.call_id: call} if call else {}
    return SimulationState(
        time=0.0, building=building, cars=cars, passengers=passengers, hall_calls=hall_calls
    )


def make_call(origin, destination, passenger_id):
    return HallCall(
        call_id="CALL1",
        registered_at=0.0,
        origin_floor=origin,
        destination_floor=destination,
        direction=Direction.DOWN if destination < origin else Direction.UP,
        passenger_ids=[passenger_id],
    )


def test_nearest_car_prefers_closer_car():
    cars = {"C1": make_car("C1", 1), "C2": make_car("C2", 8)}
    call = make_call(origin=2, destination=1, passenger_id="P1")
    state = make_state(cars, call=call)

    scheduler = NearestCarScheduler()
    assert scheduler.assign_call(call, state) == "C1"


def test_nearest_car_tie_break_picks_first_car():
    cars = {"C1": make_car("C1", 4), "C2": make_car("C2", 4)}
    call = make_call(origin=4, destination=1, passenger_id="P1")
    state = make_state(cars, call=call)

    scheduler = NearestCarScheduler()
    assert scheduler.assign_call(call, state) == "C1"


def test_myopic_prefers_car_with_lower_projected_wait():
    cars = {"C1": make_car("C1", 1), "C2": make_car("C2", 8)}
    passenger = Passenger(passenger_id="P1", hall_arrival_time=0.0, origin_floor=2, destination_floor=1)
    call = make_call(origin=2, destination=1, passenger_id="P1")
    state = make_state(cars, passenger=passenger, call=call)

    scheduler = MyopicScheduler()
    assert scheduler.assign_call(call, state) == "C1"


def test_predictive_filters_predictions_below_probability_threshold(monkeypatch):
    captured_future_passengers = []

    def fake_forward_simulate(car, passenger_lookup, future_passengers, current_time, horizon_seconds):
        captured_future_passengers.append(list(future_passengers))
        from elevator_sim.simulation.forward_simulator import ForwardSimResult

        return ForwardSimResult(estimated_wait_times={"x": 1.0})

    monkeypatch.setattr(
        "elevator_sim.schedulers.predictive.forward_simulate", fake_forward_simulate
    )

    class StubPredictor:
        def predict_future_passengers(self, current_time, horizon_seconds, simulation_state):
            return [
                PredictedPassenger(
                    predicted_arrival_time=5.0, origin_floor=2, destination_floor=1, probability=0.1
                ),
                PredictedPassenger(
                    predicted_arrival_time=5.0, origin_floor=3, destination_floor=1, probability=0.9
                ),
            ]

    cars = {"C1": make_car("C1", 1)}
    passenger = Passenger(passenger_id="P1", hall_arrival_time=0.0, origin_floor=2, destination_floor=1)
    call = make_call(origin=2, destination=1, passenger_id="P1")
    state = make_state(cars, passenger=passenger, call=call)

    scheduler = PredictiveScheduler(predictor=StubPredictor(), probability_threshold=0.5)
    scheduler.assign_call(call, state)

    assert captured_future_passengers, "forward_simulate was never called"
    for future_passengers in captured_future_passengers:
        assert all(pp.probability >= 0.5 for pp in future_passengers)
        assert len(future_passengers) == 1
