"""The Polyaire AirTouch integration."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pyairtouch
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.COVER,
    Platform.SENSOR,
    Platform.UPDATE,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Polyaire AirTouch connection after discovery."""
    hass.data.setdefault(DOMAIN, {})

    discovery_results = await pyairtouch.discover()
    if not discovery_results:
        # Couldn't find the AirTouch device.
        # This shouldn't happen because we are using discovery.
        raise ConfigEntryNotReady

    # Save the API instance for each discovered AirTouch controller (typically
    # there's only one)
    api_objects = []
    for airtouch_api in discovery_results:
        initialised = await airtouch_api.init()
        if not initialised:
            raise ConfigEntryNotReady

        api_objects.append(airtouch_api)

    hass.data[DOMAIN][entry.entry_id] = api_objects

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
