from elevator_sim.config import Config, HotelEventConfig


def test_hotel_event_config_prediction_time_offset_defaults_to_zero():
    event = HotelEventConfig(
        event_id="checkout_001",
        event_type="checkout",
        start_time=3600.0,
        source_floors=[2, 3],
        destination_distribution={1: 1.0},
        expected_people=100,
    )
    assert event.prediction_time_offset_seconds == 0.0


def test_hotel_event_config_prediction_time_offset_loads_from_yaml():
    raw = {
        "hotel_events": [
            {
                "event_id": "banquet_001",
                "event_type": "banquet_end",
                "start_time": 1800.0,
                "source_floors": [3],
                "destination_distribution": {1: 1.0},
                "expected_people": 120,
                "prediction_time_offset_seconds": 180.0,
            }
        ]
    }
    config = Config.model_validate(raw)
    assert config.hotel_events[0].prediction_time_offset_seconds == 180.0
