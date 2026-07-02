"""Binary sensors for YM-S1-BES BLE meters."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import YmS1BesCoordinator
from .entity import YmS1BesEntity


CONNECTED_DESCRIPTION = BinarySensorEntityDescription(
    key="connected",
    translation_key="connected",
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up YM-S1-BES binary sensors."""
    coordinator: YmS1BesCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([YmS1BesConnectedSensor(coordinator)])


class YmS1BesConnectedSensor(YmS1BesEntity, BinarySensorEntity):
    """Connectivity state for the BLE meter."""

    entity_description = CONNECTED_DESCRIPTION

    def __init__(self, coordinator: YmS1BesCoordinator) -> None:
        super().__init__(coordinator, CONNECTED_DESCRIPTION.key)
        self._attr_translation_key = CONNECTED_DESCRIPTION.translation_key

    @property
    def available(self) -> bool:
        """Keep the connectivity sensor available so it can show offline."""
        return True

    @property
    def is_on(self) -> bool:
        """Return true while the meter is considered connected."""
        return self.coordinator.connected
