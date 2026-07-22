"""Requirements.md 8.3 / 10.4: idle cars should be proactively repositioned
by the Parking Scheduler on a rolling-horizon interval."""
from elevator_sim.domain.building import Building
from elevator_sim.schedulers.myopic import MyopicScheduler
from elevator_sim.schedulers.parking import ParkingScheduler
from elevator_sim.simulation.engine import EngineConfig, SimulationEngine

ELEVATOR_SPECS = dict(
    count=1,
    capacity_people=15,
    seconds_per_floor=2.5,
    start_delay_seconds=1.0,
    door_open_seconds=1.5,
    door_close_seconds=1.5,
    boarding_seconds_per_person=0.7,
    alighting_seconds_per_person=0.6,
)


def test_idle_car_is_repositioned_to_fixed_floor_with_no_passengers():
    building = Building.uniform(8, lobby_floor=1)
    parking_scheduler = ParkingScheduler(strategy="fixed_per_car", fixed_floors={"C1": 5})

    engine = SimulationEngine(
        building=building,
        elevator_specs=ELEVATOR_SPECS,
        scheduler=MyopicScheduler(),
        arrivals=[],  # no passengers at all
        engine_config=EngineConfig(
            warmup_seconds=0, duration_seconds=60, cooldown_seconds=0, reposition_interval_seconds=10
        ),
        parking_scheduler=parking_scheduler,
    )
    result = engine.run()

    car = result.cars["C1"]
    assert car.current_floor == 5
    assert car.total_distance > 0
