"""Constants for the YM-S1-BES integration."""

from __future__ import annotations

DOMAIN = "ym_s1_bes"

CONF_MAC = "mac"
CONF_ADDRESS = "address"
CONF_POLL_INTERVAL = "poll_interval"
CONF_LOADS = "loads"
CONF_ACTIVE_LOAD_ID = "active_load_id"
CONF_CONFIGURE_LOADS = "configure_loads"
CONF_CREATE_LOAD = "create_load"
CONF_LOAD_ACTION = "load_action"
CONF_LOAD_NAME = "load_name"

LOAD_ID = "id"
LOAD_NAME = "name"

DEFAULT_POLL_INTERVAL = 30
DEFAULT_NAME = "YM-S1-BES"
DEFAULT_LOAD_ID = "default"
DEFAULT_LOAD_NAME = "Default Meter Load"

SERVICE_UUID = "49535343-fe7d-4ae5-8fa9-9fafd205e455"
NOTIFY_UUID = "49535343-1e4d-4bd9-ba61-23c647249616"
WRITE_UUID = "49535343-8841-43f4-a8d4-ecbe34729bb3"

BLE_HEAD = "YUNM"
