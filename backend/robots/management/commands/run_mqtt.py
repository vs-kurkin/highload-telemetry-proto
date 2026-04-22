# ruff: noqa
"""Temporary docstring."""

import asyncio

from django.core.management.base import BaseCommand

from robots.mqtt_handler import MQTTHandler


class Command(BaseCommand):
    help = "Runs the MQTT consumer and telemetry buffer flusher"

    def handle(self, *args: object, **options: object) -> None:
        self.stdout.write(self.style.SUCCESS("Starting MQTT Consumer..."))

        async def main() -> None:
            handler = MQTTHandler()
            await handler.connect()

            # Run two main processes concurrently:
            # 1. MQTT listening (handled in background by gmqtt)
            # 2. Database flush loop
            await handler.flush_buffer_loop()

        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Stopped by user"))
