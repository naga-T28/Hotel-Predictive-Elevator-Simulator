from elevator_sim.domain.building import Building
from elevator_sim.domain.passenger import Passenger, PassengerStatus
from elevator_sim.schedulers.myopic import MyopicScheduler
from elevator_sim.simulation.engine import EngineConfig, SimulationEngine

ELEVATOR_SPECS = dict(
    count=1,
    capacity_people=2,
    seconds_per_floor=2.5,
    start_delay_seconds=1.0,
    door_open_seconds=1.5,
    door_close_seconds=1.5,
    boarding_seconds_per_person=0.7,
    alighting_seconds_per_person=0.6,
)


def test_excess_passengers_are_left_behind():
    building = Building.uniform(2, lobby_floor=1)
    # Three passengers arrive together at the same floor, but capacity is 2.
    passengers = [
        Passenger(passenger_id=f"P{i}", hall_arrival_time=1.0, origin_floor=2, destination_floor=1)
        for i in range(3)
    ]

    engine = SimulationEngine(
        building=building,
        elevator_specs=ELEVATOR_SPECS,
        scheduler=MyopicScheduler(),
        arrivals=passengers,
        engine_config=EngineConfig(warmup_seconds=0, duration_seconds=120, cooldown_seconds=60),
    )
    result = engine.run()

    statuses = [p.status for p in result.passengers.values()]
    assert statuses.count(PassengerStatus.ARRIVED) == 2
    assert statuses.count(PassengerStatus.LEFT_BEHIND) == 1

    for car in result.cars.values():
        assert car.current_load <= car.capacity_people
