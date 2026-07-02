"""Virtual load helpers for YM-S1-BES."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry

from .const import CONF_ACTIVE_LOAD_ID, CONF_LOADS, LOAD_ID, LOAD_NAME


def get_loads(entry: ConfigEntry) -> list[dict[str, str]]:
    """Return configured virtual loads."""
    loads = entry.options.get(CONF_LOADS, [])
    if not isinstance(loads, list):
        return []

    valid_loads: list[dict[str, str]] = []
    for load in loads:
        if not isinstance(load, dict):
            continue
        load_id = str(load.get(LOAD_ID, "")).strip()
        name = str(load.get(LOAD_NAME, "")).strip()
        if load_id and name:
            valid_loads.append({LOAD_ID: load_id, LOAD_NAME: name})
    return valid_loads


def get_active_load_id(entry: ConfigEntry) -> str | None:
    """Return the active virtual load id."""
    active_load_id = entry.options.get(CONF_ACTIVE_LOAD_ID)
    if active_load_id is None:
        return None
    return str(active_load_id)


def load_options(loads: list[dict[str, str]]) -> dict[str, str]:
    """Build a selector mapping for configured loads."""
    return {load[LOAD_ID]: load[LOAD_NAME] for load in loads}


def options_with_loads(
    entry: ConfigEntry,
    loads: list[dict[str, str]],
    active_load_id: str | None,
) -> dict[str, Any]:
    """Return options preserving unrelated keys."""
    options = dict(entry.options)
    options[CONF_LOADS] = loads
    if active_load_id:
        options[CONF_ACTIVE_LOAD_ID] = active_load_id
    else:
        options.pop(CONF_ACTIVE_LOAD_ID, None)
    return options
