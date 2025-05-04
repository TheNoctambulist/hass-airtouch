"""Polyair AirTouch cover entities.

Cover entities are used to represent the dampers for zones within an AirTouch
system.
"""

import logging
from typing import Any, Optional

import pyairtouch
from homeassistant.components import cover
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import devices, entities
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# The AirTouch console doesn't seem to perform any checks for a Damper
# Increase command if the current percentage is >95% which can result in
# an open percentage >100%!
# To avoid this, we jump to the nearest 5%.
_DAMPER_STEP = 5


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_devices: AddEntitiesCallback,
) -> None:
    """Set up the AirTouch cover devices."""
    airtouch: pyairtouch.AirTouch = hass.data[DOMAIN][config_entry.entry_id]

    discovered_entities: list[cover.CoverEntity] = []

    airtouch_device = devices.AirTouchDevice(hass, config_entry.entry_id, airtouch)
    for airtouch_ac in airtouch.air_conditioners:
        ac_device = airtouch_device.ac_device(airtouch_ac)

        for airtouch_zone in airtouch_ac.zones:
            zone_device = ac_device.zone_device(airtouch_zone)
            zone_entity = ZoneDamperEntity(
                zone_device=zone_device,
                airtouch_zone=airtouch_zone,
            )
            discovered_entities.append(zone_entity)

    _LOGGER.debug("Found entities %s", discovered_entities)
    async_add_devices(discovered_entities)


class ZoneDamperEntity(entities.AirTouchZoneEntity, cover.CoverEntity):
    """Cover entity for an AirTouch zone's damper."""

    _attr_name = "Damper"
    _attr_device_class = cover.CoverDeviceClass.DAMPER
    _attr_supported_features = (
        cover.CoverEntityFeature.CLOSE
        | cover.CoverEntityFeature.OPEN
        | cover.CoverEntityFeature.SET_POSITION
    )

    def __init__(
        self, zone_device: devices.ZoneDevice, airtouch_zone: pyairtouch.Zone
    ) -> None:
        # The climate entity is considered main entity, so the damper entity
        # uses an id_suffix.
        super().__init__(
            zone_device=zone_device,
            airtouch_zone=airtouch_zone,
            id_suffix="_damper",
        )

    @property
    def current_cover_position(self) -> int | None:
        if self._airtouch_zone.power_state == pyairtouch.ZonePowerState.OFF:
            return 0
        return self._airtouch_zone.current_damper_percentage

    @property
    def is_closed(self) -> Optional[bool]:
        return self._airtouch_zone.power_state == pyairtouch.ZonePowerState.OFF

    async def async_open_cover(self, **_: Any) -> None:  # noqa: ANN401
        # We treat this as a request to turn the zone on
        await self._airtouch_zone.set_power(pyairtouch.ZonePowerState.ON)

    async def async_close_cover(self, **_: Any) -> None:  # noqa: ANN401
        # We treat this as a request to turn the zone off
        await self._airtouch_zone.set_power(pyairtouch.ZonePowerState.OFF)

    async def async_set_cover_position(self, **kwargs: Any) -> None:  # noqa: ANN401
        open_percentage: int = kwargs[cover.ATTR_POSITION]
        open_percentage = _DAMPER_STEP * round(open_percentage / _DAMPER_STEP)
        await self._airtouch_zone.set_damper_percentage(open_percentage)

        # Automatically turn the zone on if the damper position is being opened,
        # otherwise the damper position change won't be reflected in the next
        # state update.
        if (
            open_percentage > 0
            and self._airtouch_zone.power_state == pyairtouch.ZonePowerState.OFF
        ):
            await self._airtouch_zone.set_power(pyairtouch.ZonePowerState.ON)
