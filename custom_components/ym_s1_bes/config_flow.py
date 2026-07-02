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
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import (
    CONF_ADDRESS,
    CONF_CONFIGURE_LOADS,
    CONF_CREATE_LOAD,
    CONF_LOAD_ACTION,
    CONF_MAC,
    CONF_POLL_INTERVAL,
    DEFAULT_LOAD_NAME,
    DEFAULT_NAME,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    LOAD_ID,
    LOAD_NAME,
)
from .load import (
    default_options,
    get_active_load_id,
    get_loads,
    load_options,
    options_with_loads,
)
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
            CONF_NAME: name or mac_to_advertised_name(mac),
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
                CONF_NAME: self._discovery[CONF_NAME],
                CONF_POLL_INTERVAL: user_input[CONF_POLL_INTERVAL],
            }
            return self.async_create_entry(
                title=data[CONF_NAME],
                data=data,
                options=default_options(data[CONF_POLL_INTERVAL]),
            )

        schema = vol.Schema(
            {
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
                return self.async_create_entry(
                    title=name,
                    data=data,
                    options=default_options(data[CONF_POLL_INTERVAL]),
                )

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
        self._pending_poll_interval: int | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show top-level device settings."""
        if user_input is not None:
            poll_interval = user_input[CONF_POLL_INTERVAL]
            if user_input.get(CONF_CONFIGURE_LOADS):
                self._pending_poll_interval = poll_interval
                return await self.async_step_load_settings()

            options = options_with_loads(
                self._entry,
                get_loads(self._entry),
                get_active_load_id(self._entry),
                poll_interval,
            )
            return self.async_create_entry(title="", data=options)

        poll_interval = int(
            self._entry.options.get(
                CONF_POLL_INTERVAL,
                self._entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
            )
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_POLL_INTERVAL, default=poll_interval
                    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
                    vol.Optional(CONF_CONFIGURE_LOADS, default=False): bool,
                }
            ),
        )

    async def async_step_load_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create, switch, rename, or delete a virtual load."""
        loads = get_loads(self._entry)
        errors: dict[str, str] = {}

        if user_input is not None:
            action = user_input.get(CONF_LOAD_ACTION)
            target_id = user_input.get(LOAD_ID)
            create_load = user_input.get(CONF_CREATE_LOAD, False)
            if create_load:
                load_id = uuid4().hex[:8]
                name = _unique_load_name(loads)
                loads.append({LOAD_ID: load_id, LOAD_NAME: name})
                active_load_id = load_id
            elif action == "set_active":
                if not target_id:
                    errors[LOAD_ID] = "load_required"
                active_load_id = target_id
            elif action == "rename":
                if not target_id:
                    errors[LOAD_ID] = "load_required"
                if errors:
                    return self._show_load_settings_form(loads, errors)
                return await self.async_step_rename_load({LOAD_ID: target_id})
            elif action == "delete":
                if not target_id:
                    errors[LOAD_ID] = "load_required"
                active_load_id = get_active_load_id(self._entry)
                if not errors:
                    loads = [load for load in loads if load[LOAD_ID] != target_id]
                    if active_load_id == target_id:
                        active_load_id = loads[0][LOAD_ID] if loads else None
                    _remove_load_registry_entries(self.hass, self._entry, target_id)
            else:
                active_load_id = get_active_load_id(self._entry)

            if errors:
                return self._show_load_settings_form(loads, errors)

            return self.async_create_entry(
                title="",
                data=options_with_loads(
                    self._entry,
                    loads,
                    active_load_id,
                    self._effective_poll_interval(),
                ),
            )

        return self._show_load_settings_form(loads, errors)

    async def async_step_rename_load(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Rename a virtual load."""
        loads = get_loads(self._entry)
        errors: dict[str, str] = {}
        if user_input is not None and LOAD_NAME in user_input:
            target_id = user_input[LOAD_ID]
            new_name = user_input[LOAD_NAME].strip()
            if not new_name:
                errors[LOAD_NAME] = "name_required"
            else:
                renamed = [
                    {**load, LOAD_NAME: new_name}
                    if load[LOAD_ID] == target_id
                    else load
                    for load in loads
                ]
                return self.async_create_entry(
                    title="",
                    data=options_with_loads(
                        self._entry,
                        renamed,
                        get_active_load_id(self._entry),
                        self._effective_poll_interval(),
                    ),
                )

        target_id = None
        if user_input is not None:
            target_id = user_input.get(LOAD_ID)
        if not target_id:
            target_id = get_active_load_id(self._entry)
        target_name = next(
            (load[LOAD_NAME] for load in loads if load[LOAD_ID] == target_id), ""
        )
        return self.async_show_form(
            step_id="rename_load",
            data_schema=vol.Schema(
                {
                    vol.Required(LOAD_ID, default=target_id): vol.In(
                        load_options(loads)
                    ),
                    vol.Required(LOAD_NAME, default=target_name): str,
                }
            ),
            errors=errors,
        )

    def _show_load_settings_form(
        self, loads: list[dict[str, str]], errors: dict[str, str]
    ) -> ConfigFlowResult:
        """Show the load settings form."""
        schema_fields: dict[Any, Any] = {
            vol.Optional(CONF_CREATE_LOAD, default=False): bool,
        }
        if loads:
            schema_fields[
                vol.Optional(LOAD_ID, default=get_active_load_id(self._entry))
            ] = vol.In(load_options(loads))
            schema_fields[vol.Optional(CONF_LOAD_ACTION, default="set_active")] = vol.In(
                {
                    "set_active": "设为当前负载",
                    "rename": "重命名负载",
                    "delete": "删除负载",
                }
            )

        return self.async_show_form(
            step_id="load_settings",
            data_schema=vol.Schema(schema_fields),
            errors=errors,
        )

    def _effective_poll_interval(self) -> int:
        """Return the interval being edited in this options flow."""
        if self._pending_poll_interval is not None:
            return self._pending_poll_interval
        return int(
            self._entry.options.get(
                CONF_POLL_INTERVAL,
                self._entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
            )
        )


def _unique_load_name(loads: list[dict[str, str]]) -> str:
    """Return a default load name that does not collide."""
    existing_names = {load[LOAD_NAME] for load in loads}
    if DEFAULT_LOAD_NAME not in existing_names:
        return DEFAULT_LOAD_NAME

    suffix = 2
    while f"{DEFAULT_LOAD_NAME} {suffix}" in existing_names:
        suffix += 1
    return f"{DEFAULT_LOAD_NAME} {suffix}"


def _remove_load_registry_entries(
    hass,
    entry: ConfigEntry,
    load_id: str,
) -> None:
    """Remove registry rows that belong to a deleted virtual load."""
    mac = entry.data[CONF_MAC]
    unique_id_prefix = f"{mac.replace(':', '').lower()}_load_{load_id}_"
    entity_registry = er.async_get(hass)
    for entity_entry in er.async_entries_for_config_entry(
        entity_registry, entry.entry_id
    ):
        if entity_entry.unique_id.startswith(unique_id_prefix):
            entity_registry.async_remove(entity_entry.entity_id)

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(
        identifiers={(DOMAIN, f"{mac}_load_{load_id}")}
    )
    if device is not None:
        device_registry.async_remove_device(device.id)
