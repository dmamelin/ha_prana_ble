"""Config flow for the Prana BLE integration."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

import voluptuous as vol
from bleak import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_ble_device_from_address,
)
from homeassistant.const import CONF_MAC, CONF_NAME, CONF_DESCRIPTION
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector
from homeassistant.helpers.device_registry import format_mac
from .const import (
    CONF_MAX_SPEED,
    CONF_UPDATE_INTERVAL,
    DEFAULT_MAX_SPEED,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

OPTIONS_FIELDS = {
    vol.Required(CONF_MAX_SPEED, default=DEFAULT_MAX_SPEED): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=1,
            max=10,
            step=1,
            mode=selector.NumberSelectorMode.BOX,
        )
    ),
    vol.Required(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=20,
            max=10 * 60,
            step=1,
            mode=selector.NumberSelectorMode.BOX,
        )
    ),
}


class PranaBleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Prana BLE."""

    VERSION = 1

    def __init__(self) -> None:
        self.discovered_mac = None
        self.discovered_name = None
        _LOGGER.debug("Prana config flow init")

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        _LOGGER.debug("Prana config flow step user (input: %s)", user_input)

        errors: dict[str, str] = {}

        if user_input:
            mac_value = user_input.get(CONF_MAC) or self.discovered_mac
            if not mac_value:
                errors["base"] = "cannot_connect"
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._build_schema(),
                    errors=errors,
                )

            mac = format_mac(mac_value)
            max_speed = user_input[CONF_MAX_SPEED]
            updating_interval = user_input[CONF_UPDATE_INTERVAL]

            try:
                self.discovered_name = await self._async_validate_input(mac)
            except CannotConnect as err:
                _LOGGER.debug("Cannot connect to Prana BLE device %s: %s", mac, err)
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error validating Prana BLE device")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(mac)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=self.discovered_name,
                    data={CONF_MAC: mac},
                    options={
                        CONF_MAX_SPEED: max_speed,
                        CONF_UPDATE_INTERVAL: updating_interval,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self._build_schema(),
            errors=errors,
        )

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak):
        """Handle bluetooth discovery."""

        _LOGGER.debug("Prana config flow step bluetooth")
        mac = format_mac(discovery_info.address)
        await self.async_set_unique_id(mac)
        self._abort_if_unique_id_configured()

        name = discovery_info.name.strip() if discovery_info.name else None

        _LOGGER.info("Discovered Prana BLE device %s", name)
        self.context["title_placeholders"] = {CONF_NAME: name, CONF_MAC: mac, CONF_DESCRIPTION: "DESC"}
        self.discovered_mac = mac
        self.discovered_name = name
        return await self.async_step_user()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        _LOGGER.debug("Prana config flow step options")
        return PranaOptionsFlowHandler()

    async def _async_validate_input(self, mac: str) -> str | None:
        """Validate that we can reach the device and return its name."""

        ble_device = async_ble_device_from_address(self.hass, mac.upper(), connectable=True)
        if ble_device is None:
            raise CannotConnect from None

        client: BleakClientWithServiceCache | None = None

        try:
            client = await establish_connection(
                BleakClientWithServiceCache,
                ble_device,
                mac,
            )
        except (asyncio.TimeoutError, BleakError, OSError) as err:
            raise CannotConnect from err
        finally:
            if client:
                with contextlib.suppress(BleakError):
                    await client.disconnect()

        return ble_device.name.strip() if ble_device.name else mac

    def _build_schema(self) -> vol.Schema:
        """Return the form schema, hiding MAC when discovered."""

        fields: dict[Any, Any] = {}
        if not self.discovered_mac:
            fields[vol.Required(CONF_MAC)] = str
        fields.update(OPTIONS_FIELDS)
        return vol.Schema(fields)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class PranaOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for an existing entry."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(OPTIONS_FIELDS), self.config_entry.options
            ),
        )
