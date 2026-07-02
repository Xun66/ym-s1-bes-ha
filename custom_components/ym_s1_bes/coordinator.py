"""Coordinator for YM-S1-BES meters."""

from __future__ import annotations

from datetime import timedelta
import logging

from bleak.exc import BleakError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .ble_client import YmS1BesBleClient
from .const import CONF_ADDRESS, CONF_MAC, CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL, DOMAIN
from .protocol import ClearAck, MeterReading

_LOGGER = logging.getLogger(__name__)


class YmS1BesCoordinator(DataUpdateCoordinator[MeterReading]):
    """Data update coordinator for a YM-S1-BES meter."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.config_entry = entry
        self.client = YmS1BesBleClient(
            hass,
            entry.data[CONF_MAC],
            entry.data.get(CONF_ADDRESS) or None,
        )
        interval = int(entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL))

        super().__init__(
            hass,
            _LOGGER,
            name=entry.title,
            update_interval=timedelta(seconds=interval),
        )

    async def _async_update_data(self) -> MeterReading:
        try:
            return await self.client.read_meter()
        except BleakError as exc:
            if self.last_update_success is False:
                raise UpdateFailed(str(exc)) from exc
            raise ConfigEntryNotReady(str(exc)) from exc
        except Exception as exc:
            raise UpdateFailed(str(exc)) from exc

    async def async_clear(self, kind: str) -> ClearAck:
        """Clear one accumulated counter and refresh data."""
        ack = await self.client.clear(kind)
        await self.async_request_refresh()
        return ack
