"""Sensor platform for the Prana BLE integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_BILLION,
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    UnitOfPressure,
    UnitOfTemperature, EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .coordinator import PranaCoordinator
from .entity import PranaBaseEntity
from .protocol import PranaState


async def async_setup_entry(_: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Prana sensors based on a config entry."""
    entities: list[PranaSensorEntity] = [
        PranaSensorEntity(entry.runtime_data, description) for description in SENSOR_DESCRIPTIONS
    ]
    async_add_entities(entities)


@dataclass(frozen=True, slots=True)
class PranaSensorDescription(SensorEntityDescription):
    """Describes a Prana sensor."""
    value_fn: Callable[[PranaState], Any] = field(default=lambda state: None),


SENSOR_DESCRIPTIONS: tuple[PranaSensorDescription, ...] = (
    PranaSensorDescription(
        key="temp_in",
        translation_key="temp_in",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    PranaSensorDescription(
        key="temp_out",
        translation_key="temp_out",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    PranaSensorDescription(
        key="temp_outside",
        translation_key="temp_outside",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    PranaSensorDescription(
        key="humidity",
        translation_key="humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
    ),
    PranaSensorDescription(
        key="pressure",
        translation_key="pressure",
        native_unit_of_measurement=UnitOfPressure.MMHG,
        device_class=SensorDeviceClass.PRESSURE,
        suggested_display_precision=0,
    ),
    PranaSensorDescription(
        key="co2",
        translation_key="co2",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO2,
    ),
    PranaSensorDescription(
        key="tvoc",
        translation_key="tvoc",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_BILLION,
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
    ),
    PranaSensorDescription(
        key="speed",
        translation_key="speed",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:fan",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PranaSensorDescription(
        key="speed_in",
        translation_key="speed_in",
        # name="TVOC",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:fan-chevron-down",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PranaSensorDescription(
        key="speed_out",
        translation_key="speed_out",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:fan-chevron-up",
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


class PranaSensorEntity(PranaBaseEntity, SensorEntity):
    """Representation of a Prana sensor."""
    entity_description: PranaSensorDescription

    def __init__(self, coordinator: PranaCoordinator, description: PranaSensorDescription) -> None:
        super().__init__(coordinator, description)
        self.entity_description = description
