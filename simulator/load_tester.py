# ruff: noqa
"""Temporary docstring."""

import asyncio
import time
import statistics
import random
import logging
from typing import List, cast, TYPE_CHECKING
from dotenv import load_dotenv
from .utils import create_telemetry_payload
from .config import (
    MQTT_HOST,
    MQTT_PORT,
    LOAD_TOTAL_MESSAGES,
    LOAD_CONCURRENCY,
    NUM_VIRTUAL_ROBOTS,
    YIELD_INTERVAL_MESSAGES,
    YIELD_SLEEP_DURATION,
    LATENCY_MS_MULTIPLIER,
    LOAD_TEST_ID_FORMAT,
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
logger = logging.getLogger("load_tester")

# Load load-test specific config
load_dotenv(".env.loadtest")


class LoadTester:
    """
    Simulates high-load telemetry bursts for testing backend performance.
    """

    sent_count: int
    latencies: List[float]
    start_time: float
    end_time: float

    def __init__(self) -> None:
        self.sent_count = 0
        self.latencies = []
        self.start_time = 0.0
        self.end_time = 0.0

    async def worker(self, client: "MQTTClient", messages_to_send: int) -> None:
        """
        Individual worker task that sends a batch of messages.
        """
        for i in range(messages_to_send):
            virtual_idx = i % cast(int, NUM_VIRTUAL_ROBOTS)
            robot_id = cast(str, LOAD_TEST_ID_FORMAT).format(idx=virtual_idx)
            battery = random.uniform(0, 100)
            payload = create_telemetry_payload(robot_id, battery, "LOAD_TEST")

            send_start = time.time()
            client.publish(f"robots/{robot_id}/telemetry", payload, qos=0)
            self.latencies.append(time.time() - send_start)
            self.sent_count += 1

            # Small sleep to prevent local socket exhaustion if needed
            if i % cast(int, YIELD_INTERVAL_MESSAGES) == 0:
                await asyncio.sleep(cast(float, YIELD_SLEEP_DURATION))

    async def run(self) -> None:
        """
        Main execution logic for the load test.
        """
        client = MQTTClient("load-tester")
        await client.connect(cast(str, MQTT_HOST), cast(int, MQTT_PORT))

        logger.info(f"Starting load test: {LOAD_TOTAL_MESSAGES} messages via {LOAD_CONCURRENCY} workers...")
        self.start_time = time.time()

        total_msgs = cast(int, LOAD_TOTAL_MESSAGES)
        concurrency = cast(int, LOAD_CONCURRENCY)
        msgs_per_worker = total_msgs // concurrency
        tasks = [self.worker(client, msgs_per_worker) for _ in range(concurrency)]

        await asyncio.gather(*tasks)

        self.end_time = time.time()
        await client.disconnect()
        self.report()

    def report(self) -> None:
        """
        Generates and prints a performance report.
        """
        duration = self.end_time - self.start_time
        mps = self.sent_count / duration
        avg_latency = statistics.mean(self.latencies) * cast(float, LATENCY_MS_MULTIPLIER)  # ms

        print("\n" + "=" * 40)
        print("LOAD TEST REPORT")
        print("=" * 40)
        print(f"Total Messages: {self.sent_count}")
        print(f"Total Duration: {duration:.2f} seconds")
        print(f"Throughput:     {mps:.2f} msg/sec")
        print(f"Avg Latency:    {avg_latency:.2f} ms")
        print("=" * 40)


if __name__ == "__main__":
    tester = LoadTester()
    try:
        asyncio.run(tester.run())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user.")
