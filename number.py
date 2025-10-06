"""Number platform for Prana BLE brightness control."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .entity import PranaBaseEntity
from .protocol import BRIGHTNESS, MAX_BRIGHTNESS


async def async_setup_entry(_: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up number entities from a config entry."""
    async_add_entities([PranaBrightnessNumberEntity(entry.runtime_data, NumberEntityDescription(
        key="brightness",
        translation_key="brightness",
        native_min_value=0,
        native_max_value=MAX_BRIGHTNESS,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:lightbulb",
    ))])


class PranaBrightnessNumberEntity(PranaBaseEntity, NumberEntity):
    """Expose the front display brightness as a number entity."""

    async def async_set_native_value(self, value: float) -> None:
        command = BRIGHTNESS.get(int(value))
        if command is None:
            raise ValueError(f"Unsupported brightness {value}")
        await self.coordinator.async_send_command(command)
