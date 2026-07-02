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
        self._failed_updates = 0
        self._ever_connected = False
        self.last_rssi: int | None = None
        interval = int(
            entry.options.get(
                CONF_POLL_INTERVAL,
                entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
            )
        )

        super().__init__(
            hass,
            _LOGGER,
            name=entry.title,
            update_interval=timedelta(seconds=interval),
        )

    async def _async_update_data(self) -> MeterReading:
        try:
            reading = await self.client.read_meter()
        except BleakError as exc:
            self._mark_update_failed()
            if self.last_update_success is False:
                raise UpdateFailed(str(exc)) from exc
            raise ConfigEntryNotReady(str(exc)) from exc
        except Exception as exc:
            self._mark_update_failed()
            raise UpdateFailed(str(exc)) from exc
        else:
            self._failed_updates = 0
            self._ever_connected = True
            self.last_rssi = self.client.last_rssi
            return reading

    @property
    def connected(self) -> bool:
        """Return whether the meter is considered connected."""
        return self._ever_connected and self._failed_updates <= 2

    def _mark_update_failed(self) -> None:
        """Track consecutive failed reads for connectivity state."""
        self._failed_updates += 1

    async def async_clear(self, kind: str) -> ClearAck:
        """Clear one accumulated counter and refresh data."""
        ack = await self.client.clear(kind)
        await self.async_request_refresh()
        return ack

    async def async_set_config(
        self, unit_price: float, valid_power_w: int
    ) -> MeterReading:
        """Set meter configuration and refresh coordinator data."""
        reading = await self.client.set_config(unit_price, valid_power_w)
        self.async_set_updated_data(reading)
        return reading
