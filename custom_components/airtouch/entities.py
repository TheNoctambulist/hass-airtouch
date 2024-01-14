"""Provides mix-ins for common entity logic."""

from typing import cast

import pyairtouch
from homeassistant.helpers.entity import Entity

from . import devices


class AirTouchAcEntity(Entity):
    """A mix-in class for common AC entity logic.

    Handles common logic including setting up subsriptions to AC state changes.
    """

    # All entities have to provide a name
    _attr_has_entity_name = True

    # A subscription based entity
    _attr_should_poll = False

    def __init__(
        self,
        ac_device: devices.AcDevice,
        airtouch_ac: pyairtouch.AirConditioner,
        id_suffix: str = "",
    ) -> None:
        self._airtouch_ac = airtouch_ac

        self._attr_unique_id = ac_device.unique_id + id_suffix
        self._attr_device_info = ac_device.device_info

    async def async_added_to_hass(self) -> None:
        self._airtouch_ac.subscribe_ac_state(self._async_on_ac_update)

    async def async_will_remove_from_hass(self) -> None:
        self._airtouch_ac.unsubscribe_ac_state(self._async_on_ac_update)

    async def _async_on_ac_update(self, _: int) -> None:
        self.schedule_update_ha_state()

    def __repr__(self) -> str:
        """Return a basic string representation of the entity."""
        device_name: str = "<Unknown>"
        if self._attr_device_info:
            device_name = cast(str, self._attr_device_info.get("name", device_name))
        return f"<{self.__class__.__name__}: {device_name} ({self._attr_unique_id})>"


class AirTouchZoneEntity(Entity):
    """A mix-in class for common zone entity logic.

    Handles common logic including setting up subsriptions to zone state changes.
    """

    # All entities have to provide a name
    _attr_has_entity_name = True

    # A subscription based entity
    _attr_should_poll = False

    def __init__(
        self,
        zone_device: devices.ZoneDevice,
        airtouch_zone: pyairtouch.Zone,
        id_suffix: str = "",
    ) -> None:
        self._airtouch_zone = airtouch_zone

        self._attr_unique_id = zone_device.unique_id + id_suffix
        self._attr_device_info = zone_device.device_info

    async def async_added_to_hass(self) -> None:
        self._airtouch_zone.subscribe(self._async_on_zone_update)

    async def async_will_remove_from_hass(self) -> None:
        self._airtouch_zone.unsubscribe(self._async_on_zone_update)

    async def _async_on_zone_update(self, _: int) -> None:
        self.schedule_update_ha_state()

    def __repr__(self) -> str:
        """Return a basic string representation of the entity."""
        device_name: str = "<Unknown>"
        if self._attr_device_info:
            device_name = cast(str, self._attr_device_info.get("name", device_name))
        return f"<{self.__class__.__name__}: {device_name} ({self._attr_unique_id})>"
