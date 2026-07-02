"""Buttons for YM-S1-BES clear commands."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import YmS1BesCoordinator
from .entity import YmS1BesEntity


@dataclass(frozen=True, kw_only=True)
class YmS1BesButtonDescription(ButtonEntityDescription):
    """Clear button description."""

    clear_kind: str


BUTTON_DESCRIPTIONS: tuple[YmS1BesButtonDescription, ...] = (
    YmS1BesButtonDescription(
        key="clear_energy",
        translation_key="clear_energy",
        clear_kind="energy",
    ),
    YmS1BesButtonDescription(
        key="clear_time",
        translation_key="clear_time",
        clear_kind="time",
    ),
    YmS1BesButtonDescription(
        key="clear_amount",
        translation_key="clear_amount",
        clear_kind="amount",
    ),
    YmS1BesButtonDescription(
        key="clear_all",
        translation_key="clear_all",
        clear_kind="all",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up YM-S1-BES buttons."""
    coordinator: YmS1BesCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        YmS1BesButton(coordinator, description) for description in BUTTON_DESCRIPTIONS
    )


class YmS1BesButton(YmS1BesEntity, ButtonEntity):
    """Button entity for a clear command."""

    entity_description: YmS1BesButtonDescription

    def __init__(
        self,
        coordinator: YmS1BesCoordinator,
        description: YmS1BesButtonDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_translation_key = description.translation_key

    async def async_press(self) -> None:
        """Run the clear command."""
        try:
            await self.coordinator.async_clear(self.entity_description.clear_kind)
        except Exception as exc:
            raise HomeAssistantError(str(exc)) from exc
