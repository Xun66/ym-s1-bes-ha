"""Sensors for YM-S1-BES BLE meters."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_MAC, DOMAIN, LOAD_ID, LOAD_NAME
from .coordinator import YmS1BesCoordinator
from .entity import YmS1BesEntity
from .load import get_active_load_id, get_loads


@dataclass(frozen=True, kw_only=True)
class YmS1BesSensorDescription(SensorEntityDescription):
    """Sensor description with reading attribute key."""

    value_attr: str


SENSOR_DESCRIPTIONS: tuple[YmS1BesSensorDescription, ...] = (
    YmS1BesSensorDescription(
        key="power",
        translation_key="power",
        value_attr="power_w",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
    YmS1BesSensorDescription(
        key="energy",
        translation_key="energy",
        value_attr="total_kwh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    YmS1BesSensorDescription(
        key="voltage",
        translation_key="voltage",
        value_attr="voltage_v",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    ),
    YmS1BesSensorDescription(
        key="current",
        translation_key="current",
        value_attr="current_a",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
    ),
    YmS1BesSensorDescription(
        key="power_factor",
        translation_key="power_factor",
        value_attr="power_factor",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    YmS1BesSensorDescription(
        key="total_time",
        translation_key="total_time",
        value_attr="total_time_minutes",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.MINUTES,
    ),
    YmS1BesSensorDescription(
        key="amount",
        translation_key="amount",
        value_attr="amount",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="CNY",
    ),
    YmS1BesSensorDescription(
        key="valid_power",
        translation_key="valid_power",
        value_attr="valid_power_w",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
    YmS1BesSensorDescription(
        key="rssi",
        translation_key="rssi",
        value_attr="rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="dBm",
    ),
)

LOAD_SENSOR_KEYS = {"power", "voltage", "current", "power_factor"}
LOAD_SENSOR_DESCRIPTIONS = tuple(
    description
    for description in SENSOR_DESCRIPTIONS
    if description.key in LOAD_SENSOR_KEYS
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up YM-S1-BES sensors."""
    coordinator: YmS1BesCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        YmS1BesSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS
    ]
    for load in get_loads(entry):
        entities.extend(
            YmS1BesLoadSensor(coordinator, load, description)
            for description in LOAD_SENSOR_DESCRIPTIONS
        )
    async_add_entities(entities)


class YmS1BesSensor(YmS1BesEntity, SensorEntity):
    """Sensor entity for a decoded meter field."""

    entity_description: YmS1BesSensorDescription

    def __init__(
        self,
        coordinator: YmS1BesCoordinator,
        description: YmS1BesSensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_translation_key = description.translation_key

    @property
    def native_value(self):
        """Return the latest sensor value."""
        if self.entity_description.value_attr == "rssi":
            return self.coordinator.last_rssi
        return getattr(self.coordinator.data, self.entity_description.value_attr)


class YmS1BesLoadSensor(CoordinatorEntity[YmS1BesCoordinator], SensorEntity):
    """Transient sensor entity attached to a virtual load device."""

    _attr_has_entity_name = True
    entity_description: YmS1BesSensorDescription

    def __init__(
        self,
        coordinator: YmS1BesCoordinator,
        load: dict[str, str],
        description: YmS1BesSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        mac = coordinator.config_entry.data[CONF_MAC]
        load_id = load[LOAD_ID]
        self._load_id = load_id
        self.entity_description = description
        self._attr_unique_id = (
            f"{mac.replace(':', '').lower()}_load_{load_id}_{description.key}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{mac}_load_{load_id}")},
            manufacturer="Yunmu",
            model="YM-S1-BES Load",
            name=load[LOAD_NAME],
            via_device=(DOMAIN, mac),
        )
        self._attr_translation_key = description.translation_key

    @property
    def available(self) -> bool:
        """Return if this load currently owns transient readings."""
        return (
            super().available
            and get_active_load_id(self.coordinator.config_entry) == self._load_id
        )

    @property
    def native_value(self):
        """Return the latest transient value for the active load."""
        if not self.available or self.coordinator.data is None:
            return None
        return getattr(self.coordinator.data, self.entity_description.value_attr)
