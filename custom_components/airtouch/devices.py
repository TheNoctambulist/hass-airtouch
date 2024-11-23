"""Device mappings and registration for the AirTouch.

This module is used to ensure consistent device information and IDs are used
throughout all platforms.
"""

from typing import Optional, cast

import pyairtouch
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry, device_registry
from typing_extensions import Unpack  # noqa: UP035 # Compatibility: Python < 3.12

from .const import DOMAIN, MANUFACTURER

# Weight deletions and substitutions slightly more than insertions since we
# typically expect to see abbreviations for area names.
_INSERTION_WEIGHT = 2
_DELETION_WEIGHT = 3
_SUBSTITUTION_WEIGHT = 3

# The maximum distance we'll permit for an area name to be considered a match.
# This needs to be tweaked based on the weightings above.
_MAX_LEVENSTHEIN_DISTANCE = 15


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
        self._register_device()

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

    def _register_device(self) -> None:
        registry = device_registry.async_get(self._hass)
        if not registry.async_get_device(identifiers=self._device_info["identifiers"]):
            # We only want to suggest an area that already exists in the Area Registry
            suggested_area = self._device_info.get("suggested_area")
            if suggested_area:
                self._device_info["suggested_area"] = self._find_area(suggested_area)

            registry.async_get_or_create(
                config_entry_id=self._config_entry_id, **self._device_info
            )

    def _find_area(self, name: str) -> Optional[str]:
        """Find an area in the area registry using a fuzzy search on a name.

        Returns:
            The discovered area name, or none if no area matches.
        """
        normalized_name = self._normalize_name(name)

        registry = area_registry.async_get(self._hass)
        areas: list[area_registry.AreaEntry] = list(registry.async_list_areas())

        # Find the closest area match using a basic fuzzy search
        best_distance: int = _MAX_LEVENSTHEIN_DISTANCE
        best_area: Optional[area_registry.AreaEntry] = None
        for area in areas:
            name_distance = _levenshtein_distance(normalized_name, area.normalized_name)
            if name_distance < best_distance:
                best_distance = name_distance
                best_area = area

            for alias in area.aliases:
                normalised_alias = self._normalize_name(alias)
                alias_distance = _levenshtein_distance(
                    normalized_name, normalised_alias
                )
                if alias_distance < best_distance:
                    best_distance = alias_distance
                    best_area = area

            if best_distance == 0:
                # Exact match found, we can't do any better than this
                break

        if best_area:
            return best_area.name
        return None

    def _normalize_name(self, name: str) -> str:
        # Compatibility: Before 2024.4
        if hasattr(area_registry, "normalize_area_name"):
            return cast(str, area_registry.normalize_area_name(name))

        from homeassistant.helpers.normalized_name_base_registry import (
            normalize_name,
        )

        return normalize_name(name)


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
            # Assuming people name their zones and Home Assistant areas
            # similarly, it makes sense to use the zone name as the suggested
            # area for the device.
            suggested_area=airtouch_zone.name,
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
            # For AirTouch 4 systems the serial number doesn't appear to be
            # unique (some logs have shown an all zeroes MAC address). The
            # AirTouch ID is always unique, so we use that here.
            unique_id=airtouch.airtouch_id,
            name=airtouch.name,
            manufacturer=MANUFACTURER,
            model=airtouch.model.value,
        )

    def ac_device(self, airtouch_ac: pyairtouch.AirConditioner) -> AcDevice:
        """Construct device info for an AC within the AirTouch system."""
        return AcDevice(
            hass=self._hass,
            config_entry_id=self._config_entry_id,
            airtouch_unique_id=self.unique_id,
            airtouch_ac=airtouch_ac,
        )


def _levenshtein_distance(str1: str, str2: str) -> int:
    """The levenshtein distance between two strings."""
    # Algorithm based on the Wikipedia algorithm:
    # https://en.wikipedia.org/wiki/Levenshtein_distance#Iterative_with_two_matrix_rows

    # Declare the two vectors of the correct size, i.e. one slot for each slice
    # of str2 including the empty slice.
    # These represent the previous and current rows in the levenshtein matrix.
    v0: list[int] = [0] * (len(str2) + 1)
    v1: list[int] = list(v0)

    # Initialise v0 (the previous row of distances).
    # This row is the edit distance from an empty str1 to str2, i.e. the number
    # of characters that would need to be appended to the empty string to make
    # str2.
    for i in range(len(v0)):
        v0[i] = i

    for i in range(len(str1)):
        # Calculate v1 (the current row distances) from the previous row v0

        # The edit distance of the first entry in v0 is to delete (i + 1)
        # characters from str1 to match an empty str2
        v1[0] = i + 1

        for j in range(len(str2)):
            deletion_cost = v0[j + 1] + _DELETION_WEIGHT
            insertion_cost = v1[j] + _INSERTION_WEIGHT
            substitution_cost = (
                v0[j] if (str1[i] == str2[j]) else (v0[j] + _SUBSTITUTION_WEIGHT)
            )

            v1[j + 1] = min(deletion_cost, insertion_cost, substitution_cost)

        # Move to the next matrix row for the next letter in str1
        v_tmp = v0
        v0 = v1
        v1 = v_tmp

    # The final result is the last entry in the current row, but we've done a
    # swap so we actually return the value from the previous row.
    return v0[-1]
