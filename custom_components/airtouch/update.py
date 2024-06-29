"""Polyaire AirTouch update entities.

An update entity is used to indicate when updates are available for the AirTouch
console.
"""

import logging
from typing import Optional

import pyairtouch
from homeassistant.components import update
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import devices, entities
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_devices: AddEntitiesCallback,
) -> None:
    """Set up the AirTouch update entities."""
    airtouch: pyairtouch.AirTouch = hass.data[DOMAIN][config_entry.entry_id]

    discovered_entities: list[update.UpdateEntity] = []

    airtouch_device = devices.AirTouchDevice(hass, config_entry.entry_id, airtouch)
    airtouch_update_entity = AirtouchUpdateEntity(
        airtouch_device=airtouch_device,
        airtouch=airtouch,
    )
    discovered_entities.append(airtouch_update_entity)

    _LOGGER.debug("Found entities: %s", discovered_entities)
    async_add_devices(discovered_entities)


class AirtouchUpdateEntity(entities.AirTouchConsoleEntity, update.UpdateEntity):
    """An update entity for the AirTouch console software."""

    # Leaving the name unset results in a suffix of "None" instead of just being
    # the device name only.
    _attr_name = "Console"

    def __init__(
        self, airtouch_device: devices.AirTouchDevice, airtouch: pyairtouch.AirTouch
    ) -> None:
        super().__init__(airtouch_device=airtouch_device, airtouch=airtouch)

    @property
    def installed_version(self) -> Optional[str]:
        if self._airtouch.console_versions:
            # The first entry is the master-console version
            return self._airtouch.console_versions[0]
        return None

    @property
    def latest_version(self) -> Optional[str]:
        if self._airtouch.update_available:
            # The latest version number is not available, returning any string
            # here is sufficient for Home Assistant to mark the entity as "On"
            # and indicate that an update is available.
            return "<Update available>"
        # The currently installed version is already the latest version.
        return self.installed_version
