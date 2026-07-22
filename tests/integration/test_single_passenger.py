from elevator_sim.domain.building import Building
from elevator_sim.domain.passenger import Passenger, PassengerStatus
from elevator_sim.schedulers.myopic import MyopicScheduler
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


def test_single_passenger_reaches_destination():
    building = Building.uniform(2, lobby_floor=1)
    passenger = Passenger(passenger_id="P1", hall_arrival_time=5.0, origin_floor=2, destination_floor=1)

    engine = SimulationEngine(
        building=building,
        elevator_specs=ELEVATOR_SPECS,
        scheduler=MyopicScheduler(),
        arrivals=[passenger],
        engine_config=EngineConfig(warmup_seconds=0, duration_seconds=120, cooldown_seconds=60),
    )
    result = engine.run()

    served = result.passengers["P1"]
    assert served.status == PassengerStatus.ARRIVED
    assert served.board_time is not None
    assert served.arrival_time is not None
    assert served.board_time >= served.hall_arrival_time
    assert served.arrival_time >= served.board_time
