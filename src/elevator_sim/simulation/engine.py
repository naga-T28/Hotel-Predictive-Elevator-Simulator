"""Discrete-event simulation engine built on SimPy (requirements.md 4)."""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import simpy

from elevator_sim.domain.building import Building
from elevator_sim.domain.elevator import CarState, ElevatorCar
from elevator_sim.domain.hall_call import HallCall
from elevator_sim.domain.passenger import Direction, Passenger, PassengerStatus
from elevator_sim.schedulers.base import Scheduler
from elevator_sim.simulation.state import SimulationState


@dataclass
class EngineConfig:
    warmup_seconds: float = 300.0
    duration_seconds: float = 3600.0
    cooldown_seconds: float = 300.0
    reposition_interval_seconds: float = 30.0


@dataclass
class AssignmentLogEntry:
    time: float
    call_id: str
    passenger_id: str
    origin_floor: int
    destination_floor: int
    car_id: str


@dataclass
class EventLogEntry:
    timestamp: float
    event_type: str
    car_id: str | None = None
    floor: int | None = None
    passenger_id: str | None = None
    direction: str | None = None
    load: float | None = None


@dataclass
class SimulationResult:
    passengers: dict[str, Passenger]
    cars: dict[str, ElevatorCar]
    assignment_log: list[AssignmentLogEntry]
    event_log: list[EventLogEntry]
    warmup_seconds: float
    duration_seconds: float
    cooldown_seconds: float


class SimulationEngine:
    def __init__(
        self,
        building: Building,
        elevator_specs: dict,
        scheduler: Scheduler,
        arrivals: list[Passenger],
        engine_config: EngineConfig,
        trajectories: list | None = None,
        parking_scheduler=None,
    ) -> None:
        self.building = building
        self.elevator_specs = elevator_specs
        self.scheduler = scheduler
        self.arrivals = sorted(arrivals, key=lambda p: p.hall_arrival_time)
        self.engine_config = engine_config
        self.trajectories = trajectories or []
        self.parking_scheduler = parking_scheduler

        self.env = simpy.Environment()
        self._call_counter = itertools.count(1)

        cars = {
            f"C{i + 1}": ElevatorCar(
                car_id=f"C{i + 1}",
                current_floor=building.lobby_floor,
                capacity_people=elevator_specs["capacity_people"],
                seconds_per_floor=elevator_specs["seconds_per_floor"],
                start_delay_seconds=elevator_specs.get("start_delay_seconds", 1.0),
                door_open_seconds=elevator_specs["door_open_seconds"],
                door_close_seconds=elevator_specs["door_close_seconds"],
                boarding_seconds_per_person=elevator_specs.get("boarding_seconds_per_person", 0.7),
                alighting_seconds_per_person=elevator_specs.get("alighting_seconds_per_person", 0.6),
            )
            for i in range(elevator_specs["count"])
        }

        self.state = SimulationState(
            time=0.0,
            building=building,
            cars=cars,
            passengers={},
            hall_calls={},
            future_arrivals=list(self.arrivals),
            trajectories=list(self.trajectories),
        )

        self.assignment_log: list[AssignmentLogEntry] = []
        self.event_log: list[EventLogEntry] = []
        self.car_wake_events: dict[str, simpy.Event] = {
            car_id: self.env.event() for car_id in cars
        }

    def run(self) -> SimulationResult:
        self.env.process(self._passenger_arrival_process())
        for car_id in self.state.cars:
            self.env.process(self._car_process(car_id))
        if self.parking_scheduler is not None:
            self.env.process(self._parking_process())

        total_time = (
            self.engine_config.warmup_seconds
            + self.engine_config.duration_seconds
            + self.engine_config.cooldown_seconds
        )
        self.env.run(until=total_time)

        return SimulationResult(
            passengers=self.state.passengers,
            cars=self.state.cars,
            assignment_log=self.assignment_log,
            event_log=self.event_log,
            warmup_seconds=self.engine_config.warmup_seconds,
            duration_seconds=self.engine_config.duration_seconds,
            cooldown_seconds=self.engine_config.cooldown_seconds,
        )

    def _passenger_arrival_process(self):
        for passenger in self.arrivals:
            wait = passenger.hall_arrival_time - self.env.now
            if wait > 0:
                yield self.env.timeout(wait)

            self.state.time = self.env.now
            if self.state.future_arrivals and self.state.future_arrivals[0] is passenger:
                self.state.future_arrivals.pop(0)

            passenger.status = PassengerStatus.WAITING
            passenger.call_time = self.env.now
            self.state.passengers[passenger.passenger_id] = passenger

            call = HallCall(
                call_id=f"CALL{next(self._call_counter):06d}",
                registered_at=self.env.now,
                origin_floor=passenger.origin_floor,
                destination_floor=passenger.destination_floor,
                direction=passenger.direction,
                passenger_ids=[passenger.passenger_id],
            )
            self.state.hall_calls[call.call_id] = call

            car_id = self.scheduler.assign_call(call, self.state)
            self.state.assign(call, car_id)
            passenger.status = PassengerStatus.ASSIGNED

            self.assignment_log.append(
                AssignmentLogEntry(
                    time=self.env.now,
                    call_id=call.call_id,
                    passenger_id=passenger.passenger_id,
                    origin_floor=passenger.origin_floor,
                    destination_floor=passenger.destination_floor,
                    car_id=car_id,
                )
            )
            self.event_log.append(
                EventLogEntry(
                    timestamp=self.env.now,
                    event_type="hall_call_assigned",
                    car_id=car_id,
                    floor=passenger.origin_floor,
                    passenger_id=passenger.passenger_id,
                )
            )

            if not self.car_wake_events[car_id].triggered:
                self.car_wake_events[car_id].succeed()

    def _car_process(self, car_id: str):
        car = self.state.cars[car_id]
        while True:
            if not car.stop_queue:
                car.direction = Direction.IDLE
                car.state = CarState.IDLE
                idle_start = self.env.now
                wake_event = self.car_wake_events[car_id]
                yield wake_event
                car.idle_seconds += self.env.now - idle_start
                self.car_wake_events[car_id] = self.env.event()
                continue

            target = car.stop_queue.pop(0)
            diff = target - car.current_floor
            if diff != 0:
                car.direction = Direction.UP if diff > 0 else Direction.DOWN
                car.state = (
                    CarState.MOVING_UP if car.direction == Direction.UP else CarState.MOVING_DOWN
                )
                travel_time = car.travel_time(target)
                car.load_area_seconds += car.current_load * travel_time
                car.busy_seconds += travel_time
                yield self.env.timeout(travel_time)
                car.total_distance += abs(diff)
                if not car.passengers:
                    car.empty_distance += abs(diff)
                car.current_floor = target
                car.position = float(target)

            self.state.time = self.env.now
            car.state = CarState.DOOR_OPENING
            car.load_area_seconds += car.current_load * car.door_open_seconds
            car.busy_seconds += car.door_open_seconds
            yield self.env.timeout(car.door_open_seconds)
            car.door_open_count += 1
            car.state = CarState.DOOR_OPEN

            alighting = [p for p in car.passengers if p.destination_floor == target]
            if alighting:
                car.state = CarState.ALIGHTING
                alighting_duration = car.alighting_seconds_per_person * len(alighting)
                car.load_area_seconds += car.current_load * alighting_duration
                car.busy_seconds += alighting_duration
                yield self.env.timeout(alighting_duration)
                for passenger in alighting:
                    passenger.arrival_time = self.env.now
                    passenger.status = PassengerStatus.ARRIVED
                    car.current_load -= passenger.occupancy
                    self.event_log.append(
                        EventLogEntry(
                            timestamp=self.env.now,
                            event_type="alight",
                            car_id=car_id,
                            floor=target,
                            passenger_id=passenger.passenger_id,
                            load=car.current_load,
                        )
                    )
                car.passengers = [p for p in car.passengers if p.destination_floor != target]

            pending_ids = car.assigned_pickups.pop(target, [])
            pending = sorted(
                (self.state.passengers[pid] for pid in pending_ids),
                key=lambda p: p.hall_arrival_time,
            )
            boarded = []
            for passenger in pending:
                if car.can_accept(passenger.occupancy):
                    car.current_load += passenger.occupancy
                    car.passengers.append(passenger)
                    passenger.board_time = self.env.now
                    passenger.status = PassengerStatus.ONBOARD
                    car.add_stop(passenger.destination_floor)
                    boarded.append(passenger)
                else:
                    passenger.status = PassengerStatus.LEFT_BEHIND
                    self.event_log.append(
                        EventLogEntry(
                            timestamp=self.env.now,
                            event_type="left_behind",
                            car_id=car_id,
                            floor=target,
                            passenger_id=passenger.passenger_id,
                        )
                    )
            if boarded:
                car.state = CarState.BOARDING
                boarding_duration = car.boarding_seconds_per_person * len(boarded)
                car.load_area_seconds += car.current_load * boarding_duration
                car.busy_seconds += boarding_duration
                yield self.env.timeout(boarding_duration)
                for passenger in boarded:
                    self.event_log.append(
                        EventLogEntry(
                            timestamp=passenger.board_time,
                            event_type="board",
                            car_id=car_id,
                            floor=target,
                            passenger_id=passenger.passenger_id,
                            load=car.current_load,
                        )
                    )

            car.state = CarState.DOOR_CLOSING
            car.load_area_seconds += car.current_load * car.door_close_seconds
            car.busy_seconds += car.door_close_seconds
            yield self.env.timeout(car.door_close_seconds)
            car.stop_count += 1

    def _parking_process(self):
        """Rolling-horizon repositioning of idle cars (requirements.md 8.3,
        10.4): every `reposition_interval_seconds`, send any car that is
        currently idle with an empty stop queue toward the Parking
        Scheduler's chosen target floor."""
        while True:
            yield self.env.timeout(self.engine_config.reposition_interval_seconds)
            self.state.time = self.env.now
            for car_id, car in self.state.cars.items():
                if car.state != CarState.IDLE or car.stop_queue:
                    continue
                target = self.parking_scheduler.target_floor_for_car(car_id, self.state)
                if target == car.current_floor or not self.building.is_valid_floor(target):
                    continue
                car.add_stop(target)
                if not self.car_wake_events[car_id].triggered:
                    self.car_wake_events[car_id].succeed()
