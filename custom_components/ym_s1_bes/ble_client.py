"""BLE client for YM-S1-BES meters."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import NOTIFY_UUID, SERVICE_UUID, WRITE_UUID
from .protocol import (
    CLEAR_PAYLOADS,
    READ_PAYLOAD,
    ClearAck,
    MeterReading,
    YmS1BesProtocol,
    advertised_name_to_mac,
    build_set_config_payload,
    decode_clear_ack,
    decode_meter_payload,
    decode_set_config_ack,
    mac_to_advertised_name,
    normalize_mac,
)

_LOGGER = logging.getLogger(__name__)


class YmS1BesBleClient:
    """Short-lived BLE command client."""

    def __init__(self, hass: HomeAssistant, mac: str, address: str | None = None) -> None:
        self.hass = hass
        self.mac = normalize_mac(mac)
        self.address = address
        self.protocol = YmS1BesProtocol(self.mac)
        self._lock = asyncio.Lock()

    async def read_meter(self) -> MeterReading:
        """Read current meter data."""
        payload = await self._request(READ_PAYLOAD)
        return decode_meter_payload(payload)

    async def clear(self, kind: str) -> ClearAck:
        """Run one of the clear commands."""
        payload = CLEAR_PAYLOADS[kind]
        response = await self._request(payload)
        return decode_clear_ack(response)

    async def set_config(self, unit_price: float, valid_power_w: int) -> MeterReading:
        """Set unit price and timing power."""
        payload = build_set_config_payload(unit_price, valid_power_w)
        response = await self._request(payload)
        return decode_set_config_ack(response)

    async def _request(self, payload: bytes) -> bytes:
        async with self._lock:
            device = self._find_device()
            if device is None:
                advertised_name = mac_to_advertised_name(self.mac)
                raise BleakError(
                    f"YM-S1-BES {advertised_name} was not found by Home Assistant Bluetooth"
                )

            address = self.address or device.address
            client = await establish_connection(
                BleakClientWithServiceCache,
                device,
                address,
                disconnected_callback=None,
                use_services_cache=True,
            )

            rx_buffer = bytearray()
            response_fut: asyncio.Future[bytes] = self.hass.loop.create_future()

            def on_notify(_sender: int, data: bytearray) -> None:
                nonlocal rx_buffer
                rx_buffer.extend(data)
                try:
                    parsed_payload, consumed = self.protocol.parse_frame(bytes(rx_buffer))
                except ValueError as exc:
                    if not response_fut.done():
                        response_fut.set_exception(exc)
                    return
                if parsed_payload is None:
                    return
                rx_buffer = rx_buffer[consumed:]
                if not response_fut.done():
                    response_fut.set_result(parsed_payload)

            try:
                await client.start_notify(NOTIFY_UUID, on_notify)
                await asyncio.sleep(1)
                frame = self.protocol.build_frame(payload)
                _LOGGER.debug("Writing YM-S1-BES frame: %s", frame.hex(" "))
                await client.write_gatt_char(WRITE_UUID, frame, response=False)
                return await asyncio.wait_for(response_fut, timeout=8)
            finally:
                try:
                    await client.stop_notify(NOTIFY_UUID)
                except (BleakError, AttributeError):
                    pass
                await client.disconnect()

    def _find_device(self):
        """Find a connectable BLE device via HA Bluetooth."""
        if self.address:
            device = bluetooth.async_ble_device_from_address(
                self.hass, self.address, connectable=True
            )
            if device is not None:
                return device

        advertised_name = mac_to_advertised_name(self.mac).upper()

        for service_info in _iter_service_info(self.hass):
            name = (getattr(service_info, "name", None) or "").upper()
            local_name = (
                getattr(getattr(service_info, "advertisement", None), "local_name", None)
                or ""
            ).upper()
            if advertised_name not in {name, local_name}:
                continue

            device = getattr(service_info, "device", None)
            if device is not None:
                self.address = device.address
                return device

            address = getattr(service_info, "address", None)
            if address:
                device = bluetooth.async_ble_device_from_address(
                    self.hass, address, connectable=True
                )
                if device is not None:
                    self.address = address
                    return device

        return None


def is_ym_s1_advertisement(name: str | None) -> bool:
    """Return true when a Bluetooth name looks like a supported meter."""
    return advertised_name_to_mac(name) is not None


def _iter_service_info(hass: HomeAssistant):
    """Iterate Bluetooth service info across supported HA versions."""
    discovered: Callable[..., list] | None = getattr(
        bluetooth, "async_discovered_service_info", None
    )
    if discovered is None:
        return []

    try:
        return discovered(hass, connectable=True)
    except TypeError:
        return discovered(hass)
