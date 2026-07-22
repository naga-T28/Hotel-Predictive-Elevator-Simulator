import numpy as np

from elevator_sim.domain.building import Building
from elevator_sim.domain.hotel_event import HotelEvent
from elevator_sim.predictors.hotel_informed import HotelInformedPredictor
from elevator_sim.simulation.state import SimulationState


def make_event(**overrides):
    defaults = dict(
        event_id="checkout_001",
        event_type="checkout",
        start_time=1800.0,
        end_time=1800.0,
        source_floors=[5],
        destination_distribution={1: 1.0},
        expected_people=200,
        spread_seconds=300.0,
        group_size=1,
        luggage_factor=1.0,
    )
    defaults.update(overrides)
    return HotelEvent(**defaults)


def make_state(time):
    building = Building.uniform(8, lobby_floor=1)
    return SimulationState(time=time, building=building, cars={}, passengers={}, hall_calls={})


def test_rate_peaks_near_event_center():
    event = make_event()
    rng = np.random.default_rng(0)
    predictor = HotelInformedPredictor(rng=rng, events=[event])

    rate_at_center, matched_event = predictor._rate_per_second(5, 1800.0)
    rate_far_away, matched_far = predictor._rate_per_second(5, 1800.0 - 5000.0)

    assert matched_event is event
    assert rate_at_center > rate_far_away


def test_predicts_more_passengers_near_event_time_than_far_away():
    event = make_event()
    rng_near = np.random.default_rng(1)
    rng_far = np.random.default_rng(1)
    predictor_near = HotelInformedPredictor(rng=rng_near, events=[event])
    predictor_far = HotelInformedPredictor(rng=rng_far, events=[event])

    state_near = make_state(time=1770.0)  # 30s before the checkout peak
    state_far = make_state(time=0.0)  # far from the event

    near = predictor_near.predict_future_passengers(current_time=1770.0, horizon_seconds=60.0, simulation_state=state_near)
    far = predictor_far.predict_future_passengers(current_time=0.0, horizon_seconds=60.0, simulation_state=state_far)

    assert len(near) > len(far)


def test_predictions_use_event_destination_distribution():
    event = make_event(destination_distribution={1: 1.0})
    rng = np.random.default_rng(2)
    predictor = HotelInformedPredictor(rng=rng, events=[event])
    state = make_state(time=1800.0)

    predictions = predictor.predict_future_passengers(current_time=1770.0, horizon_seconds=60.0, simulation_state=state)
    assert predictions  # should generate at least some near the peak
    assert all(pp.destination_floor == 1 for pp in predictions)
    assert all(pp.origin_floor == 5 for pp in predictions)


def test_prediction_time_offset_shifts_predicted_center():
    # EXPERIMENT_VALIDATION_PLAN.md 3.3: the true event time (used for demand
    # generation) and the time given to the predictor can diverge to model
    # prediction error, without touching actual passenger generation.
    true_center = 1800.0
    offset = 300.0
    event_no_offset = make_event(start_time=true_center, end_time=true_center)
    event_with_offset = make_event(
        start_time=true_center, end_time=true_center, prediction_time_offset_seconds=offset
    )
    predictor_no_offset = HotelInformedPredictor(rng=np.random.default_rng(0), events=[event_no_offset])
    predictor_with_offset = HotelInformedPredictor(rng=np.random.default_rng(0), events=[event_with_offset])

    rate_true_center_no_offset, _ = predictor_no_offset._rate_per_second(5, true_center)
    rate_true_center_with_offset, _ = predictor_with_offset._rate_per_second(5, true_center)
    rate_shifted_center_with_offset, _ = predictor_with_offset._rate_per_second(5, true_center + offset)

    assert rate_true_center_with_offset < rate_true_center_no_offset
    assert rate_shifted_center_with_offset > rate_true_center_with_offset


def test_falls_back_to_baseline_when_no_event_active():
    rng = np.random.default_rng(3)
    predictor = HotelInformedPredictor(
        rng=rng, events=[], baseline_rate_per_hour=3600.0, baseline_destination_floor=1
    )
    state = make_state(time=0.0)
    # building has floors 1-8; predictor with no events falls back to iterating building floors
    predictions = predictor.predict_future_passengers(current_time=0.0, horizon_seconds=10.0, simulation_state=state)
    assert all(pp.destination_floor == 1 for pp in predictions)
