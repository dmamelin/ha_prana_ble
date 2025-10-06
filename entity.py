"""Common entity helpers for the Prana BLE integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import (
    DEVICE_FALLBACK,
    DEVICE_MANUFACTURER,
    DOMAIN,
)
from .coordinator import PranaCoordinator

_LOGGER = logging.getLogger(__name__)


class PranaBaseEntity(CoordinatorEntity[PranaCoordinator]):
    """Base entity wired to the Prana coordinator."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PranaCoordinator, entity_description: EntityDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = f"{self.coordinator.entry.unique_id}_{entity_description.key}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.unique_id)},
            connections={(CONNECTION_BLUETOOTH, self.coordinator.entry.unique_id)},
            manufacturer=DEVICE_MANUFACTURER,
            model=DEVICE_FALLBACK,
        )

    @property
    def native_value(self) -> Any:
        if not self.coordinator.data:
            return None
        return getattr(self.coordinator.data, self.entity_description.key)
