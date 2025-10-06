"""Select platform for Prana BLE display configuration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from . import protocol
from .entity import PranaBaseEntity
from .protocol import PranaSetCommand


async def async_setup_entry(_: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Prana BLE select entities from a config entry."""
    async_add_entities([PranaDisplaySelect(entry.runtime_data, SelectEntityDescription(
        key="display",
        translation_key="display",
        options=DISPLAY_OPTIONS,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:information-slab-box-outline"
    ))])


def _build_display_mappings() -> tuple[list[str], dict[str, PranaSetCommand]]:
    """Generate ordered display options and lookup tables."""
    options: list[str] = []
    label_to_command: dict[str, PranaSetCommand] = {}
    for raw_key, command in sorted(protocol.DISPLAY.items()):
        name = command.name
        options.append(name)
        label_to_command[name] = command
    return options, label_to_command


DISPLAY_OPTIONS, DISPLAY_TO_COMMAND = _build_display_mappings()


class PranaDisplaySelect(PranaBaseEntity, SelectEntity):
    """Expose the front panel display mode as a select entity."""

    @property
    def current_option(self) -> str | None:
        return self.native_value

    async def async_select_option(self, option: str) -> None:
        """Handle selecting a display mode option."""
        command = DISPLAY_TO_COMMAND.get(option)
        if command is None:
            raise ValueError(f"Unsupported display option: {option}")
        await self.coordinator.async_send_command(command)
