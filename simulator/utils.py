# ruff: noqa
"""Temporary docstring."""

import json
import time
from typing import Tuple, cast
from .config import MQTT_HOST, MQTT_PORT


def create_telemetry_payload(robot_id: str, battery: float, status: str) -> str:
    """
    Creates a standard telemetry JSON payload for the robot fleet.
    """
    payload: dict[str, object] = {
        "robot_id": robot_id,
        "battery": round(battery, 2),
        "status": status,
        "timestamp": time.time(),
    }
    return json.dumps(payload)


def get_mqtt_config() -> Tuple[str, int]:
    """
    Returns basic MQTT connection parameters (from central config).
    """
    return cast(str, MQTT_HOST), cast(int, MQTT_PORT)
