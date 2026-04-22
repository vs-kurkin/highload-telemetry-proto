# ruff: noqa
import json
import pytest
from simulator.utils import create_telemetry_payload, get_mqtt_config


def test_create_telemetry_payload():
    robot_id = "robot_1"
    battery = 85.5
    status = "ONLINE"

    payload_str = create_telemetry_payload(robot_id, battery, status)
    payload = json.loads(payload_str)

    assert payload["robot_id"] == robot_id
    assert payload["battery"] == 85.5
    assert payload["status"] == status
    assert "timestamp" in payload


def test_get_mqtt_config():
    host, port = get_mqtt_config()
    assert isinstance(host, str)
    assert isinstance(port, int)
