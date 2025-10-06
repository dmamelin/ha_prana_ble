"""Switch platform for Prana BLE controls."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .entity import PranaBaseEntity
from .protocol import (
    FLOWS_LOCK_TOGGLE,
    MINI_HEATING_TOGGLE,
    PranaSetCommand,
    WINTER_MODE_TOGGLE,
)


async def async_setup_entry(_: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Prana BLE switches from a config entry."""
    entities: list[PranaSwitchEntity] = [
        PranaSwitchEntity(entry.runtime_data, description) for description in SWITCH_ENTITY_DESCRIPTIONS
    ]
    async_add_entities(entities)


@dataclass(frozen=True, slots=True)
class PranaSwitchEntityDescription(SwitchEntityDescription):
    entity_category = EntityCategory.CONFIG
    toggle_cmd: PranaSetCommand = None


SWITCH_ENTITY_DESCRIPTIONS: tuple[PranaSwitchEntityDescription, ...] = (
    PranaSwitchEntityDescription(
        key="mini_heating",
        translation_key="mini_heating",
        icon="mdi:radiator",
        toggle_cmd=MINI_HEATING_TOGGLE,
    ),
    PranaSwitchEntityDescription(
        key="winter_mode",
        translation_key="winter_mode",
        icon="mdi:snowflake",
        toggle_cmd=WINTER_MODE_TOGGLE,
    ),
    PranaSwitchEntityDescription(
        key="flows_locked",
        translation_key="flows_locked",
        icon="mdi:lock",
        toggle_cmd=FLOWS_LOCK_TOGGLE,
    ),
)


class PranaSwitchEntity(PranaBaseEntity, SwitchEntity):
    entity_description: PranaSwitchEntityDescription

    @property
    def is_on(self) -> bool | None:
        return self.native_value

    async def async_turn_on(self, **kwargs: object) -> None:
        if not self.is_on:
            await self.coordinator.async_send_command(self.entity_description.toggle_cmd)

    async def async_turn_off(self, **kwargs: object) -> None:
        if self.is_on:
            await self.coordinator.async_send_command(self.entity_description.toggle_cmd)
