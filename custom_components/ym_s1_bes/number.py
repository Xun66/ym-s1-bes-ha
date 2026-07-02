"""Number entities for YM-S1-BES configuration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import YmS1BesCoordinator
from .entity import YmS1BesEntity


@dataclass(frozen=True, kw_only=True)
class YmS1BesNumberDescription(NumberEntityDescription):
    """Number description with reading attribute key."""

    value_attr: str


NUMBER_DESCRIPTIONS: tuple[YmS1BesNumberDescription, ...] = (
    YmS1BesNumberDescription(
        key="unit_price",
        translation_key="unit_price",
        value_attr="unit_price",
        native_min_value=0,
        native_max_value=9.99,
        native_step=0.01,
        native_unit_of_measurement="CNY/kWh",
        mode=NumberMode.BOX,
    ),
    YmS1BesNumberDescription(
        key="valid_power",
        translation_key="valid_power",
        value_attr="valid_power_w",
        native_min_value=1,
        native_max_value=999,
        native_step=1,
        native_unit_of_measurement=UnitOfPower.WATT,
        mode=NumberMode.BOX,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up YM-S1-BES number entities."""
    coordinator: YmS1BesCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        YmS1BesNumber(coordinator, description) for description in NUMBER_DESCRIPTIONS
    )


class YmS1BesNumber(YmS1BesEntity, NumberEntity):
    """Number entity for meter configuration."""

    entity_description: YmS1BesNumberDescription

    def __init__(
        self,
        coordinator: YmS1BesCoordinator,
        description: YmS1BesNumberDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | int | None:
        """Return the latest configured value."""
        if self.coordinator.data is None:
            return None
        return getattr(self.coordinator.data, self.entity_description.value_attr)

    async def async_set_native_value(self, value: float) -> None:
        """Set unit price or valid timing power."""
        if self.coordinator.data is None:
            raise HomeAssistantError("No meter reading available")

        unit_price = self.coordinator.data.unit_price
        valid_power_w = self.coordinator.data.valid_power_w

        if self.entity_description.key == "unit_price":
            unit_price = round(float(value), 2)
        else:
            valid_power_w = round(float(value))

        try:
            await self.coordinator.async_set_config(unit_price, valid_power_w)
        except Exception as exc:
            raise HomeAssistantError(str(exc)) from exc
