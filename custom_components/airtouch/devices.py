"""Device mappings and registration for the AirTouch.

This module is used to ensure consistent device information and IDs are used
throughout all platforms.
"""
import pyairtouch
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from typing_extensions import Unpack

from .const import DOMAIN, MANUFACTURER


class BaseDevice:
    """Base class used for the various devices within an AirTouch system."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        unique_id: str,
        **kwargs: Unpack[device_registry.DeviceInfo],
    ) -> None:
        self._hass = hass
        self._config_entry_id = config_entry_id

        self._unique_id = unique_id

        self._device_info = device_registry.DeviceInfo(
            identifiers={(DOMAIN, unique_id)}, **kwargs
        )

        # Always explicitly register the device in case there are no associated
        # entities in the platform.
        self._register_device(hass, config_entry_id)

    @property
    def unique_id(self) -> str:
        """The unique ID for this device.

        This can be used as a prefix for any entities associated with the
        device.
        """
        return self._unique_id

    @property
    def device_info(self) -> device_registry.DeviceInfo:
        """The device registry DeviceInfo for this device."""
        return self._device_info

    def _register_device(self, hass: HomeAssistant, config_entry_id: str) -> None:
        registry = device_registry.async_get(hass)
        registry.async_get_or_create(
            config_entry_id=config_entry_id, **self._device_info
        )


class ZoneDevice(BaseDevice):
    """Device information for an AirTouch zone.

    Should be constructed using the zone_device() method on the AcDevice class.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        ac_unique_id: str,
        airtouch_zone: pyairtouch.Zone,
    ) -> None:
        super().__init__(
            hass=hass,
            config_entry_id=config_entry_id,
            # The zone ID is unique across all ACs within an AirTouch system, so
            # there's no need to include the AC ID in the unique identifier, but to
            # keep things simply we just use the parent as the prefix for the unique
            # ID.
            unique_id=f"{ac_unique_id}_zone{airtouch_zone.zone_id}",
            name=airtouch_zone.name,
            manufacturer=MANUFACTURER,
            via_device=(DOMAIN, ac_unique_id),
        )


class AcDevice(BaseDevice):
    """Device information for an AirTouch air-conditioner.

    Should be constructed using the ac_device() method on the AirTouchDevice class.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        airtouch_unique_id: str,
        airtouch_ac: pyairtouch.AirConditioner,
    ) -> None:
        super().__init__(
            hass=hass,
            config_entry_id=config_entry_id,
            # ACs get a sequential identifier within an AirTouch system, so include
            # the airtouch unique ID as a prefix.
            unique_id=f"{airtouch_unique_id}_ac{airtouch_ac.ac_id}",
            name=airtouch_ac.name,
            via_device=(DOMAIN, airtouch_unique_id),
        )

    def zone_device(self, airtouch_zone: pyairtouch.Zone) -> ZoneDevice:
        """Construct device info for a zone associated with this AC."""
        return ZoneDevice(
            hass=self._hass,
            config_entry_id=self._config_entry_id,
            ac_unique_id=self.unique_id,
            airtouch_zone=airtouch_zone,
        )


class AirTouchDevice(BaseDevice):
    """Device information for the AirTouch controller."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        airtouch: pyairtouch.AirTouch,
    ) -> None:
        super().__init__(
            hass=hass,
            config_entry_id=config_entry_id,
            # We know the serial number for the AirTouch, so use that as the unique
            # ID as per the Entity documentation.
            unique_id=airtouch.serial,
            name=airtouch.name,
            manufacturer=MANUFACTURER,
            model=airtouch.version.value,
        )

    def ac_device(self, airtouch_ac: pyairtouch.AirConditioner) -> AcDevice:
        """Construct device info for an AC within the AirTouch system."""
        return AcDevice(
            hass=self._hass,
            config_entry_id=self._config_entry_id,
            airtouch_unique_id=self.unique_id,
            airtouch_ac=airtouch_ac,
        )
