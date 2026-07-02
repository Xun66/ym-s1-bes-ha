"""Config flow for YM-S1-BES BLE meters."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME

from .const import (
    CONF_ADDRESS,
    CONF_MAC,
    CONF_POLL_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
)
from .protocol import advertised_name_to_mac, mac_to_advertised_name, normalize_mac


class YmS1BesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for YM-S1-BES."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery: dict[str, Any] | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle Bluetooth discovery."""
        name = _discovery_name(discovery_info)
        mac = advertised_name_to_mac(name)
        if mac is None:
            return self.async_abort(reason="not_supported")

        await self.async_set_unique_id(mac.replace(":", ""))
        self._abort_if_unique_id_configured(
            updates={CONF_ADDRESS: discovery_info.address}
        )

        self._discovery = {
            CONF_MAC: mac,
            CONF_ADDRESS: discovery_info.address,
            CONF_NAME: f"{DEFAULT_NAME} {mac[-5:]}",
        }
        self.context["title_placeholders"] = {
            "name": name or DEFAULT_NAME,
            "mac": mac,
        }
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm Bluetooth discovery."""
        if self._discovery is None:
            return self.async_abort(reason="no_discovery")

        errors: dict[str, str] = {}
        if user_input is not None:
            data = {
                **self._discovery,
                CONF_NAME: user_input.get(CONF_NAME) or self._discovery[CONF_NAME],
                CONF_POLL_INTERVAL: user_input[CONF_POLL_INTERVAL],
            }
            return self.async_create_entry(title=data[CONF_NAME], data=data)

        schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default=self._discovery[CONF_NAME]): str,
                vol.Optional(
                    CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
            }
        )
        return self.async_show_form(
            step_id="bluetooth_confirm",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "mac": self._discovery[CONF_MAC],
                "advertised_name": mac_to_advertised_name(self._discovery[CONF_MAC]),
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual setup."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                mac = normalize_mac(user_input[CONF_MAC])
            except ValueError:
                errors[CONF_MAC] = "invalid_mac"
            else:
                await self.async_set_unique_id(mac.replace(":", ""))
                self._abort_if_unique_id_configured()
                name = user_input.get(CONF_NAME) or f"{DEFAULT_NAME} {mac[-5:]}"
                data = {
                    CONF_MAC: mac,
                    CONF_ADDRESS: (user_input.get(CONF_ADDRESS) or "").strip(),
                    CONF_NAME: name,
                    CONF_POLL_INTERVAL: user_input[CONF_POLL_INTERVAL],
                }
                return self.async_create_entry(title=name, data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_MAC): str,
                vol.Optional(CONF_ADDRESS, default=""): str,
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Optional(
                    CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


def _discovery_name(discovery_info: BluetoothServiceInfoBleak) -> str | None:
    advertisement = getattr(discovery_info, "advertisement", None)
    return (
        getattr(advertisement, "local_name", None)
        or getattr(discovery_info, "name", None)
    )
