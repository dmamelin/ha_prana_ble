"""BLE protocol primitives for the Prana ventilation unit."""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass
from math import log2

_LOGGER = logging.getLogger(__name__)

CONTROL_RW_CHARACTERISTIC_UUID = "0000cccc-0000-1000-8000-00805f9b34fb"
COMMAND_PREFIX = b"\xBE\xEF"

STATE_INDEX_POWER = 10
STATE_INDEX_POWER_IN = 28
STATE_INDEX_POWER_OUT = 32

STATE_INDEX_BRIGHTNESS = 12
STATE_INDEX_MINI_HEATING = 14

STATE_INDEX_NIGHT_MODE = 16
STATE_INDEX_BOOST_MODE = 18
STATE_INDEX_AUTO_MODE = 20

STATE_INDEX_FLOWS_LOCKED = 22
STATE_INDEX_SPEED = 26
STATE_INDEX_SPEED_IN = 30
STATE_INDEX_SPEED_OUT = 34

STATE_INDEX_WINTER_MODE = 42

STATE_INDEX_TEMP_IN = 48
STATE_INDEX_TEMP_OUTSIDE = 51
STATE_INDEX_TEMP_OUT = 54
STATE_INDEX_HUMIDITY = 60
STATE_INDEX_CO2 = 61
STATE_INDEX_TVOC = 63
STATE_INDEX_PRESSURE = 77
STATE_INDEX_DISPLAY = 99

MAX_BRIGHTNESS = 6
MAX_SPEED = 10


class PranaCommand:

    def __init__(self, *command: int) -> None:
        self._payload = COMMAND_PREFIX + bytes(command)

    @property
    def payload(self) -> bytes:
        """Return the raw bytes for the command."""
        return self._payload

    def __repr__(self) -> str:
        """Return a developer-friendly representation of the command."""
        payload = " ".join(f"{byte:02X}" for byte in self._payload)
        return f"PranaCommand(payload=[{payload}])"


REQUEST_STATE = PranaCommand(0x05, 0x01, 0x00, 0x00, 0x00, 0x00, 0x5A)


class PranaSetCommand(PranaCommand):
    """Command that writes a single configuration byte."""

    SET_BYTE = 0x04

    def __init__(self, last_byte: int) -> None:
        super().__init__(self.SET_BYTE, last_byte)


class PranaDisplayCommand(PranaSetCommand):

    def __init__(self, name: str, last_byte: int) -> None:
        super().__init__(last_byte)
        self.name = name


BRIGHTNESS = {i: PranaSetCommand(0x6E + i) for i in range(MAX_BRIGHTNESS + 1)}

DISPLAY = {
    0x0: PranaDisplayCommand("fan", 0x62),
    0x1: PranaDisplayCommand("temp_in", 0x5B),
    0x2: PranaDisplayCommand("temp_out", 0x5C),
    0x3: PranaDisplayCommand("co2", 0x5D),
    0x4: PranaDisplayCommand("tvoc", 0x5E),
    0x5: PranaDisplayCommand("humidity", 0x5F),
    0x6: PranaDisplayCommand("efficiency", 0x60),
    0x7: PranaDisplayCommand("pressure", 0x61),
    0x9: PranaDisplayCommand("date", 0x63),
    0xA: PranaDisplayCommand("time", 0x64),
}

TOGGLE = PranaSetCommand(0x0A)  # 1?
# STOP = PranaSetCommand(0x01)
# START = PranaSetCommand(0x0A)

TOGGLE_IN = PranaSetCommand(0x0D)
TOGGLE_OUT = PranaSetCommand(0x10)

SPEED_IN = {i: (TOGGLE_IN if i == 0 else PranaSetCommand(30 + i)) for i in range(MAX_SPEED + 1)}
SPEED_OUT = {i: (TOGGLE_OUT if i == 0 else PranaSetCommand(40 + i)) for i in range(MAX_SPEED + 1)}
SPEED = {i: (TOGGLE if i == 0 else PranaSetCommand(50 + i)) for i in range(MAX_SPEED + 1)}

FLOWS_LOCK_TOGGLE = PranaSetCommand(0x09)
WINTER_MODE_TOGGLE = PranaSetCommand(0x16)
MINI_HEATING_TOGGLE = PranaSetCommand(0x05)

MODE = {
    "auto": PranaDisplayCommand("auto", 0x43),
    "auto_plus": PranaDisplayCommand("auto_plus", 0x44),
    "night": PranaDisplayCommand("night", 0x06),
    "boost": PranaDisplayCommand("boost", 0x07),
}


@dataclass
class PranaState:
    """Parsed representation of the raw device state payload."""

    power: bool | None = None
    speed: int | None = None

    power_in: bool | None = None
    speed_in: int | None = None

    power_out: int | None = None
    speed_out: int | None = None

    mode: str | None = None
    brightness: int | None = None
    display: str | None = None
    flows_locked: bool | None = None
    mini_heating: bool | None = None
    winter_mode: bool | None = None
    temp_in: float | None = None
    temp_out: float | None = None
    temp_outside: float | None = None
    humidity: int | None = None
    pressure: int | None = None
    tvoc: int | None = None
    co2: int | None = None

    def update(self, data: bytearray) -> None:
        """Update the state with raw bytes returned from the device."""
        if data[:2] != COMMAND_PREFIX:
            raise ValueError("Unexpected payload prefix")

        self.power = bool(data[STATE_INDEX_POWER])
        self.power_in = bool(data[STATE_INDEX_POWER_IN])
        self.power_out = bool(data[STATE_INDEX_POWER_OUT])

        self.mini_heating = data[STATE_INDEX_MINI_HEATING] == 1
        self.winter_mode = data[STATE_INDEX_WINTER_MODE] == 1

        if data[STATE_INDEX_AUTO_MODE] == 1:
            self.mode = "auto"
        elif data[STATE_INDEX_AUTO_MODE] == 2:
            self.mode = "auto_plus"
        elif data[STATE_INDEX_BOOST_MODE] == 1:
            self.mode = "boost"
        elif data[STATE_INDEX_NIGHT_MODE] == 1:
            self.mode = "night"
        else:
            self.mode = None

        self.flows_locked = bool(data[STATE_INDEX_FLOWS_LOCKED])

        self.speed_in = int(data[STATE_INDEX_SPEED_IN] / 10)
        self.speed_out = int(data[STATE_INDEX_SPEED_OUT] / 10)

        if self.flows_locked:
            self.speed = int(data[STATE_INDEX_SPEED] / 10)
        else:
            # virtual speed
            self.speed = max(self.speed_in, self.speed_out)

        brightness_value = data[STATE_INDEX_BRIGHTNESS]
        self.brightness = 0 if brightness_value == 0 else int(log2(brightness_value) + 1)

        display_value = DISPLAY.get(data[STATE_INDEX_DISPLAY])
        self.display = display_value.name if display_value else None

        self.humidity = int(data[STATE_INDEX_HUMIDITY] - 128)
        self.pressure = self.unpack(data, STATE_INDEX_PRESSURE)

        self.temp_in = float(self.unpack(data, STATE_INDEX_TEMP_IN)) / 10
        self.temp_outside = float(self.unpack(data, STATE_INDEX_TEMP_OUTSIDE)) / 10
        self.temp_out = float(self.unpack(data, STATE_INDEX_TEMP_OUT)) / 10

        self.co2 = self.unpack(data, STATE_INDEX_CO2)
        self.tvoc = self.unpack(data, STATE_INDEX_TVOC)

    def unpack(self, data: bytearray, key: int) -> int:
        return struct.unpack_from(">h", data, key)[0] & 0b0011_1111_1111_1111
