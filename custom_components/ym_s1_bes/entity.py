"""Shared entity helpers for YM-S1-BES."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_MAC, DEFAULT_NAME, DOMAIN
from .coordinator import YmS1BesCoordinator


class YmS1BesEntity(CoordinatorEntity[YmS1BesCoordinator]):
    """Base entity for YM-S1-BES devices."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: YmS1BesCoordinator, key: str) -> None:
        super().__init__(coordinator)
        mac = coordinator.config_entry.data[CONF_MAC]
        self._attr_unique_id = f"{mac.replace(':', '').lower()}_{key}"
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, mac)},
            identifiers={(DOMAIN, mac)},
            manufacturer="Yunmu",
            model="YM-S1-BES",
            name=DEFAULT_NAME,
            sw_version=str(coordinator.data.firmware) if coordinator.data else None,
        )
