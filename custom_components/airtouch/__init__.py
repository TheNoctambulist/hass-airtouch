"""The Polyaire AirTouch integration."""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import TYPE_CHECKING

import pyairtouch
from homeassistant.const import CONF_HOST, Platform
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_MINOR_VERSION,
    CONF_VERSION,
    DOMAIN,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


_LOGGER = logging.getLogger(__name__)

_LOCK_KEY = "lock"

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

    # Initialise the saved domain data if it is not already initialised.
    # A lock is included to support mutual exclusion between config entries.
    hass.data.setdefault(DOMAIN, {_LOCK_KEY: asyncio.Lock()})

    # Ensure discovery is mutually exlusive across config entries since it needs
    # to bind to an explicit local port.
    async with hass.data[DOMAIN][_LOCK_KEY]:
        discovery_results = await pyairtouch.discover(
            remote_host=entry.data.get(CONF_HOST)
        )

    # Filter the API instances to the AirTouch controller that matches this
    # config entry.
    airtouch = next(
        (at for at in discovery_results if entry.unique_id == at.airtouch_id), None
    )
    if not airtouch:
        # Couldn't find the AirTouch device.
        # As a general rule this shouldn't happen because we are using discovery.
        # However, it might happen if the AirTouch console is offline or the
        # user configured with unicast discovery and the AirTouch console got a
        # new IP address.
        raise ConfigEntryNotReady("AirTouch not detected on network")

    if not await airtouch.init():
        await airtouch.shutdown()
        raise ConfigEntryNotReady("Error initialising AirTouch communication")

    # Save the API object for use throughout the integration
    hass.data[DOMAIN][entry.entry_id] = airtouch

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        airtouch: pyairtouch.AirTouch = hass.data[DOMAIN].pop(entry.entry_id)
        if airtouch:
            await airtouch.shutdown()

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

    if entry_version > CONF_VERSION:
        # The user has downgraded from a future version
        _LOGGER.error(
            "Failed config downgrade from v%s.%s to v%s.%s",
            entry_version,
            entry_minor_version,
            CONF_VERSION,
            CONF_MINOR_VERSION,
        )
        return False

    if entry_version < 2:  # noqa: PLR2004
        # Migration is not supported from config version 1 to version 2.
        _LOGGER.error(
            "Migration not supported from v%s.%s to v%s.%s. "
            "Delete and re-add config entries.",
            entry_version,
            entry_minor_version,
            CONF_VERSION,
            CONF_MINOR_VERSION,
        )
        return False

    # Take a copy of the existing data so we can mutate it until we reach the
    # appropriate config version.
    config_data = {**entry.data}

    # No migration actions required at the moment.
    # Just update the config entry version to the latest.
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
