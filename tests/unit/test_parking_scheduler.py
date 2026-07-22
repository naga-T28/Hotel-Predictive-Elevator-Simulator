from elevator_sim.domain.building import Building
from elevator_sim.domain.elevator import ElevatorCar
from elevator_sim.schedulers.parking import ParkingScheduler
from elevator_sim.simulation.state import SimulationState


def make_car(car_id, floor):
    return ElevatorCar(
        car_id=car_id,
        current_floor=floor,
        capacity_people=15,
        seconds_per_floor=2.5,
        start_delay_seconds=1.0,
        door_open_seconds=1.5,
        door_close_seconds=1.5,
        boarding_seconds_per_person=0.7,
        alighting_seconds_per_person=0.6,
    )


def make_state(cars, time=0.0):
    building = Building.uniform(8, lobby_floor=1)
    return SimulationState(time=time, building=building, cars=cars, passengers={}, hall_calls={})


def test_all_to_lobby_strategy():
    scheduler = ParkingScheduler(strategy="all_to_lobby", lobby_floor=1)
    state = make_state({"C1": make_car("C1", 5)})
    assert scheduler.target_floor_for_car("C1", state) == 1


def test_fixed_per_car_strategy():
    scheduler = ParkingScheduler(strategy="fixed_per_car", fixed_floors={"C1": 3, "C2": 6})
    state = make_state({"C1": make_car("C1", 1), "C2": make_car("C2", 1)})
    assert scheduler.target_floor_for_car("C1", state) == 3
    assert scheduler.target_floor_for_car("C2", state) == 6


def test_zoned_strategy_distributes_cars():
    scheduler = ParkingScheduler(strategy="zoned", zone_floors=[1, 4, 8])
    cars = {"C1": make_car("C1", 1), "C2": make_car("C2", 1), "C3": make_car("C3", 1)}
    state = make_state(cars)
    targets = {car_id: scheduler.target_floor_for_car(car_id, state) for car_id in cars}
    assert set(targets.values()) == {1, 4, 8}


def test_demand_weighted_strategy_picks_highest_weight_floor():
    scheduler = ParkingScheduler(strategy="demand_weighted", demand_weights={2: 0.1, 5: 0.7, 8: 0.2})
    state = make_state({"C1": make_car("C1", 1)})
    assert scheduler.target_floor_for_car("C1", state) == 5


def test_demand_weighted_uses_dynamic_source_when_provided():
    def source(time):
        return {3: 0.9, 6: 0.1}

    scheduler = ParkingScheduler(strategy="demand_weighted", demand_source=source)
    state = make_state({"C1": make_car("C1", 1)}, time=42.0)
    assert scheduler.target_floor_for_car("C1", state) == 3


def test_assign_call_delegates_to_nearest_car_logic():
    from elevator_sim.domain.hall_call import HallCall
    from elevator_sim.domain.passenger import Direction

    scheduler = ParkingScheduler()
    cars = {"C1": make_car("C1", 1), "C2": make_car("C2", 8)}
    state = make_state(cars)
    call = HallCall(
        call_id="CALL1", registered_at=0.0, origin_floor=2, destination_floor=1, direction=Direction.DOWN
    )
    assert scheduler.assign_call(call, state) == "C1"
