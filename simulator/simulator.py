# ruff: noqa
"""Temporary docstring."""

import asyncio
import random
import logging
from typing import List, cast, TYPE_CHECKING
from .utils import create_telemetry_payload
from .config import (
    MQTT_HOST,
    MQTT_PORT,
    NUM_ROBOTS,
    UPDATE_INTERVAL,
    BATTERY_DRAIN_MIN,
    BATTERY_DRAIN_MAX,
    BATTERY_INITIAL_MIN,
    BATTERY_INITIAL_MAX,
    CRITICAL_BATTERY_LEVEL,
    ROBOT_ID_FORMAT,
)

if TYPE_CHECKING:
    from gmqtt import Client as MQTTClient  # type: ignore[import-untyped]
else:
    try:
        from gmqtt import Client as MQTTClient  # type: ignore[import-untyped]
    except ImportError:
        MQTTClient = object  # type: ignore

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("simulator")


class RobotSimulator:
    robot_id: str
    battery: float
    status: str
    is_charging: bool

    def __init__(self, robot_id: str) -> None:
        self.robot_id = robot_id
        self.battery = random.uniform(cast(float, BATTERY_INITIAL_MIN), cast(float, BATTERY_INITIAL_MAX))
        self.status = "OK"
        self.is_charging = False

    async def run(self, client: "MQTTClient") -> None:
        while True:
            if self.is_charging:
                # Плавная зарядка (быстрее чем разрядка)
                charge_speed = random.uniform(0.5, 1.5)
                self.battery = min(100.0, self.battery + charge_speed)
                self.status = "CHARGING"
                if self.battery >= 100.0:
                    self.is_charging = False
                    self.status = "OK"
            else:
                # Постепенная разрядка
                drain = random.uniform(cast(float, BATTERY_DRAIN_MIN), cast(float, BATTERY_DRAIN_MAX))
                self.battery = max(0.0, self.battery - drain)

                if self.battery <= 20.0:  # Порог начала зарядки
                    self.is_charging = True

                if self.battery < cast(float, CRITICAL_BATTERY_LEVEL):
                    self.status = "CRITICAL_LOW_BATTERY"
                else:
                    self.status = "OK"

            payload = create_telemetry_payload(self.robot_id, self.battery, self.status)
            client.publish(f"robots/{self.robot_id}/telemetry", payload)
            await asyncio.sleep(cast(float, UPDATE_INTERVAL))


async def main() -> None:
    client = MQTTClient("robot-simulator-fleet")
    await client.connect(cast(str, MQTT_HOST), cast(int, MQTT_PORT))

    simulators: List[RobotSimulator] = [
        RobotSimulator(cast(str, ROBOT_ID_FORMAT).format(i=i)) for i in range(cast(int, NUM_ROBOTS))
    ]

    logger.info(f"Starting smooth simulation for {NUM_ROBOTS} robots...")
    await asyncio.gather(*[s.run(client) for s in simulators])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Simulation stopped by user.")
