"""Fan entities for the Prana BLE integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature, FanEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .coordinator import PranaCoordinator
from .entity import PranaBaseEntity
from .protocol import PranaSetCommand, SPEED, SPEED_IN, SPEED_OUT, MODE

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(_: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Prana fans based on a config entry."""
    entities: list[PranaFanEntity] = [
        PranaFanEntity(entry.runtime_data, description) for description in FAN_ENTITY_DESCRIPTIONS
    ]
    async_add_entities(entities)


@dataclass(frozen=True, slots=True)
class PranaFanEntityDescription(FanEntityDescription):
    speed_cmd: dict[int, PranaSetCommand] = None


FAN_ENTITY_DESCRIPTIONS: tuple[PranaFanEntityDescription, ...] = (
    PranaFanEntityDescription(
        key="",
        translation_key="fan",
        name="",
        speed_cmd=SPEED,
    ),
    PranaFanEntityDescription(
        key="in",
        translation_key="fan_in",
        name="In",
        speed_cmd=SPEED_IN,
        icon="mdi:fan-chevron-down",
    ),
    PranaFanEntityDescription(
        key="out",
        translation_key="fan_out",
        name="Out",
        speed_cmd=SPEED_OUT,
        icon="mdi:fan-chevron-up",
    ),
)


class PranaFanEntity(PranaBaseEntity, FanEntity):
    """Common logic shared by all Prana fan entities."""

    entity_description: PranaFanEntityDescription

    _attr_supported_features = (
            FanEntityFeature.SET_SPEED
            | FanEntityFeature.TURN_OFF
            | FanEntityFeature.TURN_ON
    )
    _attr_preset_modes = list(MODE.keys())

    def __init__(self, coordinator: PranaCoordinator, entity_description: PranaFanEntityDescription) -> None:
        super().__init__(coordinator, entity_description)
        self._attr_speed_count = coordinator.max_speed
        _LOGGER.debug(
            "Creating Prana fan entity %s (%s)",
            entity_description.key,
            entity_description,
        )

        # only for main fan
        if not entity_description.key:
            self._attr_supported_features |= FanEntityFeature.PRESET_MODE

    def _get_key(self, base: str) -> str:
        key = base
        if self.entity_description.key:
            key += f"_{self.entity_description.key}"
        return key

    @property
    def is_on(self) -> bool | None:
        return getattr(self.coordinator.data, self._get_key("power"))

    @property
    def percentage(self) -> int | None:
        speed = self._current_speed_level
        if speed is None:
            return None
        if self._attr_speed_count <= 0:
            return 0
        return max(0, min(100, round((speed / self._attr_speed_count) * 100)))

    @property
    def _current_speed_level(self) -> int | None:
        return getattr(self.coordinator.data, self._get_key("speed"))

    @property
    def preset_mode(self) -> str | None:
        return self.coordinator.data.mode

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode not in MODE:
            raise ValueError(f"Unsupported preset mode {preset_mode}")
        await self.coordinator.async_send_command(MODE[preset_mode])

    def _percentage_to_level(self, percentage: int) -> int:
        if percentage <= 0 or self._attr_speed_count == 0:
            return 0
        percentage = max(0, min(percentage, 100))
        return max(1, round((percentage / 100) * self._attr_speed_count))

    async def async_turn_on(self, percentage: int | None = None, preset_mode: str | None = None, **kwargs: Any) -> None:
        _LOGGER.debug(
            "Turning on fan %s (percentage=%s, preset=%s, kwargs=%s)",
            self.entity_description.key,
            percentage,
            preset_mode,
            kwargs,
        )
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
            return
        elif percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            if not self.is_on:
                await self.coordinator.async_send_command(self.entity_description.speed_cmd.get(0))

    async def async_set_percentage(self, percentage: int) -> None:
        level = self._percentage_to_level(percentage)
        if level == 0:
            await self.async_turn_off()
        else:
            await self.coordinator.async_send_command(self.entity_description.speed_cmd.get(level))

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self.is_on:
            await self.coordinator.async_send_command(self.entity_description.speed_cmd.get(0))
