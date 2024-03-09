"""The Polyaire AirTouch integration."""

from __future__ import annotations

import inspect
import logging
from typing import TYPE_CHECKING

import pyairtouch
from homeassistant.const import CONF_HOST, Platform
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_MINOR_VERSION,
    CONF_SPILL_BYPASS,
    CONF_SPILL_ZONES,
    CONF_VERSION,
    DOMAIN,
    SpillBypass,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.COVER,
    Platform.SENSOR,
    Platform.UPDATE,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Polyaire AirTouch connection after discovery."""
    _LOGGER.debug(
        "ConfigEntry (v%d.%d): %s",
        entry.version,
        getattr(entry, "minor_version", 0),  # For Home Assistant <2024.1
        entry.data,
    )

    hass.data.setdefault(DOMAIN, {})

    discovery_results = await pyairtouch.discover(remote_host=entry.data.get(CONF_HOST))
    if not discovery_results:
        # Couldn't find the AirTouch device.
        # As a general rule this shouldn't happen because we are using discovery.
        # However, it might happen if the AirTouch console is offline or the
        # user configured with unicast discovery and the AirTouch console got a
        # new IP address.
        raise ConfigEntryNotReady

    # Save the API instance for each discovered AirTouch controller (typically
    # there's only one)
    api_objects: list[pyairtouch.AirTouch] = []
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
        api_objects: list[pyairtouch.AirTouch] = hass.data[DOMAIN].pop(entry.entry_id)
        for airtouch_api in api_objects:
            await airtouch_api.shutdown()

    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate previous versions of configuration."""
    entry_version = entry.version
    # Use getattr for backwards compatibility before Home Assistant 2024.1
    entry_minor_version = getattr(entry, "minor_version", 0)
    _LOGGER.debug(
        "Migrating config from schema v%s.%s",
        entry_version,
        entry_minor_version,
    )

    if entry_version > 1:
        # The user has downgraded from a future version
        _LOGGER.error(
            "Failed config downgrade from v%s.%s to v%s.%s",
            entry_version,
            entry_minor_version,
            CONF_VERSION,
            CONF_MINOR_VERSION,
        )
        return False

    # Take a copy of the existing data so we can mutate it until we reach the
    # appropriate config version.
    config_data = {**entry.data}

    if entry_version == 1:
        if entry_minor_version < 2:  # noqa: PLR2004
            # Prior to v1.2, only broadcast discovery was supported
            config_data.setdefault(CONF_HOST, None)
            # Prior to v1.2 the integration always created zone spill entities
            config_data.setdefault(CONF_SPILL_BYPASS, SpillBypass.SPILL)

        if entry_minor_version < 3:  # noqa: PLR2004
            # Prior to v1.3 spill entities were created for all zones
            # An empty list is handled as a special case for backwards compatibility.
            config_data.setdefault(CONF_SPILL_ZONES, [])

    update_signature = inspect.signature(hass.config_entries.async_update_entry)
    if "version" in update_signature.parameters:
        # Compatibility: 2024.3 onwards
        hass.config_entries.async_update_entry(
            entry,
            version=CONF_VERSION,
            minor_version=CONF_MINOR_VERSION,
            data=config_data,
        )
    else:
        # Compatibility: Before 2024.3
        entry.version = CONF_VERSION
        if hasattr(entry, "minor_version"):
            # Compatibility: For 2024.1 and 2024.2
            entry.minor_version = CONF_MINOR_VERSION
        hass.config_entries.async_update_entry(entry, data=config_data)

    _LOGGER.debug(
        "Successfully migrated config to schema v%s.%s",
        CONF_VERSION,
        CONF_MINOR_VERSION,
    )
    return True
