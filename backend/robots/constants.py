# ruff: noqa
"""Temporary docstring."""

# Redis Keys and Prefixes
TELEMETRY_BUFFER_KEY = "telemetry_buffer"
TELEMETRY_DLQ_KEY = "telemetry_buffer_dlq"
DLQ_MAX_RETRIES = 3
ALERT_LOCK_PREFIX = "alert_lock:"
ALERT_LOCK_VALUE = "1"
MQTT_RATE_LIMIT_PREFIX = "mqtt_limit:"
MQTT_RATE_LIMIT_SECONDS = 5

# Channels Group Names
OPERATORS_GROUP_NAME = "operators"

# MQTT Topics and Settings
TELEMETRY_TOPIC_FILTER = "robots/+/telemetry"
DEFAULT_QOS = 0

# Robot Statuses
STATUS_OK = "OK"
STATUS_UNKNOWN = "UNKNOWN"
STATUS_LOAD_TEST = "LOAD_TEST"
UNKNOWN_ROBOT_ID = "unknown"

# Simulation / Fallback values
DEFAULT_BATTERY_LEVEL = 0.0

# Model Field Lengths
ROBOT_ID_MAX_LENGTH = 100
STATUS_MAX_LENGTH = 50
MESSAGE_MAX_LENGTH = 500
