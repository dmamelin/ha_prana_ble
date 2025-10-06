"""Data update coordinator for the Prana BLE integration."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import timedelta

from bleak import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from homeassistant import config_entries
from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.const import CONF_MAC
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DEFAULT_MAX_SPEED, CONF_MAX_SPEED, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
from .protocol import (
    COMMAND_PREFIX,
    CONTROL_RW_CHARACTERISTIC_UUID,
    PranaCommand,
    PranaState,
    REQUEST_STATE,
)

_LOGGER = logging.getLogger(__name__)

_NOTIFY_TIMEOUT = 5.0
_EXPECTED_STATE_BYTES = 100


class PranaCoordinator(DataUpdateCoordinator[PranaState]):
    """Coordinate updates for a Prana BLE device."""

    def __init__(self, hass: HomeAssistant, entry: config_entries.ConfigEntry) -> None:
        """Initialize the coordinator."""
        update_interval_seconds = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            name=f"Prana BLE ({entry.title})",
            update_interval=timedelta(seconds=update_interval_seconds),
        )

        self.entry = entry
        self.address: str | None = entry.data.get(CONF_MAC,"").upper()
        self.max_speed: int = entry.options.get(CONF_MAX_SPEED, DEFAULT_MAX_SPEED)
        self._stale_threshold = timedelta(seconds=update_interval_seconds * 3)

        # Preserve reference to higher-level client for entity services.
        self._ble_client: BleakClientWithServiceCache | None = None
        self._client_lock = asyncio.Lock()
        self._operation_lock = asyncio.Lock()
        self._notify_buffer = bytearray()
        self._notify_future: asyncio.Future[bytearray] | None = None

        self.data = PranaState()

    async def _ensure_client(self) -> BleakClientWithServiceCache:
        """Return a connected BleakClient, establishing a session if needed."""
        if not self.address:
            raise BleakError("No BLE address configured for Prana device")

        async with self._client_lock:
            client = self._ble_client
            if client and client.is_connected:
                return client

            if client:
                with contextlib.suppress(BleakError):
                    await client.disconnect()
                self._ble_client = None

            ble_device = async_ble_device_from_address(
                self.hass, self.address, connectable=True
            )
            if ble_device is None:
                raise BleakError(f"Unable to find BLE device with address {self.address}")

            new_client: BleakClientWithServiceCache | None = None

            try:
                new_client = await establish_connection(
                    BleakClientWithServiceCache,
                    ble_device,
                    self.address,
                    self._ble_disconnected_callback,
                )
                await new_client.start_notify(CONTROL_RW_CHARACTERISTIC_UUID, self._ble_notification_handler)
            except BleakError:
                self._ble_client = None
                if new_client:
                    with contextlib.suppress(BleakError):
                        await new_client.stop_notify(CONTROL_RW_CHARACTERISTIC_UUID)
                    with contextlib.suppress(BleakError):
                        await new_client.disconnect()
                raise

            self._notify_buffer.clear()
            self._ble_client = new_client
            _LOGGER.debug("Connected to Prana device %s", self.address)
            return new_client

    def _fail_pending_notification(self, err: Exception) -> None:
        """Abort any in-flight notification waiters."""
        future = self._notify_future
        if future and not future.done():
            future.set_exception(err)
        self._notify_buffer.clear()

    async def _invalidate_client(
            self, client: BleakClientWithServiceCache | None = None
    ) -> None:
        """Drop the active BLE client so the next call reconnects."""
        async with self._client_lock:
            if client and self._ble_client is not client:
                client = None
            else:
                client = self._ble_client if client is None else client
                self._ble_client = None

        if client is None:
            return

        with contextlib.suppress(BleakError):
            await client.stop_notify(CONTROL_RW_CHARACTERISTIC_UUID)
        with contextlib.suppress(BleakError):
            await client.disconnect()

    def _ble_notification_handler(self, _, data: bytearray) -> None:
        """Handle incoming notification chunks from the device."""
        future = self._notify_future
        if future is None or future.done():
            return

        chunk = bytearray(data)
        if not chunk:
            return

        if not self._notify_buffer and chunk[:1] != COMMAND_PREFIX[:1]:
            _LOGGER.debug("Discarding Prana chunk with invalid prefix: %s", chunk.hex())
            return

        self._notify_buffer.extend(chunk)

        if (len(self._notify_buffer) >= len(COMMAND_PREFIX)
                and self._notify_buffer[: len(COMMAND_PREFIX)] != COMMAND_PREFIX):
            _LOGGER.debug("Resetting notification buffer due to prefix mismatch")
            self._notify_buffer.clear()
            return

        if len(self._notify_buffer) >= _EXPECTED_STATE_BYTES:
            if not future.done():
                future.set_result(bytearray(self._notify_buffer))
            self._notify_buffer.clear()

    def _ble_disconnected_callback(self, client: BleakClientWithServiceCache) -> None:
        """Handle BLE disconnections from Bleak's callback thread."""
        _LOGGER.warning("Prana BLE device %s (%s) disconnected", self.entry.title, self.address)
        self.hass.loop.call_soon_threadsafe(self._handle_ble_disconnect, client)

    def _handle_ble_disconnect(self, client: BleakClientWithServiceCache) -> None:
        if self._ble_client is client:
            self._ble_client = None
        self._fail_pending_notification(BleakError("Device disconnected"))

    async def _async_update_data(self) -> PranaState:
        """Fetch data from the device."""
        try:
            client = await self._ensure_client()
        except BleakError as err:
            raise UpdateFailed(f"Failed to connect to Prana BLE device: {err}") from err

        async with self._operation_lock:
            await self._async_request_state_locked(client)

        return self.data

    @property
    def stale_threshold(self) -> timedelta:
        """Return the maximum age before data is considered stale."""
        return self._stale_threshold

    async def async_shutdown(self) -> None:
        """Close BLE connection for this coordinator."""
        self._fail_pending_notification(BleakError("Coordinator shutdown"))
        await self._invalidate_client()

    async def async_send_command(self, command: PranaCommand) -> None:
        """Send a Prana command and refresh device state."""
        try:
            client = await self._ensure_client()
        except BleakError as err:
            raise UpdateFailed(f"Failed to connect before sending command: {err}") from err

        async with self._operation_lock:
            try:
                _LOGGER.debug("Sending Prana BLE command: %s", command)
                resp = await client.write_gatt_char(CONTROL_RW_CHARACTERISTIC_UUID, command.payload, True)
                if resp:
                    _LOGGER.debug("Command response: %s", resp)
            except BleakError as err:
                await self._invalidate_client(client)
                raise UpdateFailed(f"BLE error while sending command: {err}") from err

        await self.async_refresh()

    async def _async_request_state_locked(self, client: BleakClientWithServiceCache) -> PranaState:
        """Request state assuming the operation lock is held."""
        future = self.hass.loop.create_future()
        self._notify_future = future
        self._notify_buffer.clear()

        try:
            _LOGGER.debug("Sending Prana BLE state request")
            resp = await client.write_gatt_char(CONTROL_RW_CHARACTERISTIC_UUID, REQUEST_STATE.payload, True)
            if resp:
                _LOGGER.debug("Command response: %s", resp)
            payload = await asyncio.wait_for(future, _NOTIFY_TIMEOUT)
        except asyncio.TimeoutError as err:
            self._fail_pending_notification(err)
            await self._invalidate_client(client)
            raise UpdateFailed("Timeout while waiting for Prana BLE state") from err
        except BleakError as err:
            self._fail_pending_notification(err)
            await self._invalidate_client(client)
            raise UpdateFailed(f"BLE error while requesting state: {err}") from err
        finally:
            self._notify_future = None

        if payload is None:
            raise UpdateFailed("No data received from Prana BLE device")

        _LOGGER.debug("Received Prana BLE state: %s", payload.hex())
        try:
            self.data.update(payload)
            _LOGGER.debug("Updated Prana BLE state: %s", self.data)
        except ValueError as err:
            raise UpdateFailed(f"Invalid state payload: {err}") from err
        return self.data
