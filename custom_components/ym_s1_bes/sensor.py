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
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import YmS1BesCoordinator
from .entity import YmS1BesEntity


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
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up YM-S1-BES sensors."""
    coordinator: YmS1BesCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        YmS1BesSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS
    )


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

    @property
    def native_value(self):
        """Return the latest sensor value."""
        return getattr(self.coordinator.data, self.entity_description.value_attr)
