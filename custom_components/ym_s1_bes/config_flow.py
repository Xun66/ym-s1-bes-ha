"""Config flow for YM-S1-BES BLE meters."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import voluptuous as vol

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_NAME

from .const import (
    CONF_ACTIVE_LOAD_ID,
    CONF_ADDRESS,
    CONF_MAC,
    CONF_POLL_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    LOAD_ID,
    LOAD_NAME,
)
from .load import get_active_load_id, get_loads, load_options, options_with_loads
from .protocol import advertised_name_to_mac, mac_to_advertised_name, normalize_mac


class YmS1BesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for YM-S1-BES."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery: dict[str, Any] | None = None

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Create the options flow."""
        return YmS1BesOptionsFlow(config_entry)

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


class YmS1BesOptionsFlow(OptionsFlow):
    """Handle YM-S1-BES options."""

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the options menu."""
        menu_options = {"add_load": "Add load"}
        if get_loads(self._entry):
            menu_options.update(
                {
                    "select_active_load": "Select active load",
                    "rename_load": "Rename load",
                    "remove_load": "Remove load",
                }
            )
        return self.async_show_menu(step_id="init", menu_options=menu_options)

    async def async_step_add_load(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a virtual load."""
        if user_input is not None:
            loads = get_loads(self._entry)
            load_id = uuid4().hex[:8]
            loads.append({LOAD_ID: load_id, LOAD_NAME: user_input[LOAD_NAME].strip()})
            active_load_id = get_active_load_id(self._entry) or load_id
            return self.async_create_entry(
                title="",
                data=options_with_loads(self._entry, loads, active_load_id),
            )

        return self.async_show_form(
            step_id="add_load",
            data_schema=vol.Schema({vol.Required(LOAD_NAME): str}),
        )

    async def async_step_select_active_load(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select the load that receives transient readings."""
        loads = get_loads(self._entry)
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data=options_with_loads(
                    self._entry, loads, user_input[CONF_ACTIVE_LOAD_ID]
                ),
            )

        return self.async_show_form(
            step_id="select_active_load",
            data_schema=vol.Schema(
                {vol.Required(CONF_ACTIVE_LOAD_ID): vol.In(load_options(loads))}
            ),
        )

    async def async_step_rename_load(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Rename a virtual load."""
        loads = get_loads(self._entry)
        if user_input is not None:
            target_id = user_input[LOAD_ID]
            new_name = user_input[LOAD_NAME].strip()
            renamed = [
                {**load, LOAD_NAME: new_name} if load[LOAD_ID] == target_id else load
                for load in loads
            ]
            return self.async_create_entry(
                title="",
                data=options_with_loads(
                    self._entry, renamed, get_active_load_id(self._entry)
                ),
            )

        return self.async_show_form(
            step_id="rename_load",
            data_schema=vol.Schema(
                {
                    vol.Required(LOAD_ID): vol.In(load_options(loads)),
                    vol.Required(LOAD_NAME): str,
                }
            ),
        )

    async def async_step_remove_load(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Remove a virtual load."""
        loads = get_loads(self._entry)
        if user_input is not None:
            target_id = user_input[LOAD_ID]
            remaining = [load for load in loads if load[LOAD_ID] != target_id]
            active_load_id = get_active_load_id(self._entry)
            if active_load_id == target_id:
                active_load_id = remaining[0][LOAD_ID] if remaining else None
            return self.async_create_entry(
                title="",
                data=options_with_loads(self._entry, remaining, active_load_id),
            )

        return self.async_show_form(
            step_id="remove_load",
            data_schema=vol.Schema({vol.Required(LOAD_ID): vol.In(load_options(loads))}),
        )
