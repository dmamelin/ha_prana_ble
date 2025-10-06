"""Home Assistant integration for Prana BLE ventilation units."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, PLATFORMS
from .coordinator import PranaCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry[PranaCoordinator]) -> bool:
    """Set up Prana BLE from a config entry."""
    _LOGGER.debug("Setting up Prana BLE entry %s", entry.entry_id)
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.debug("Prana BLE options for %s: %s", entry.entry_id, entry.options)
    coordinator = PranaCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(lambda hass, e: hass.config_entries.async_reload(e.entry_id)))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_shutdown()
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Cleanup when removing a config entry."""
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if data:
        await entry.runtime_data.async_shutdown()
