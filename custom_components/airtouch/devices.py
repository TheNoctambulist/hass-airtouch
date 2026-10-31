"""Device mappings and registration for the AirTouch.

This module is used to ensure consistent device information and IDs are used
throughout all platforms.
"""

from typing import TYPE_CHECKING, cast

from homeassistant.helpers import area_registry, device_registry
from homeassistant.helpers.normalized_name_base_registry import normalize_name

from .const import DOMAIN, MANUFACTURER

if TYPE_CHECKING:
    import pyairtouch
    from homeassistant.core import HomeAssistant

# Weight deletions and substitutions slightly more than insertions since we
# typically expect to see abbreviations for area names. For example, a zone
# named "Master Bed" should be a close match for "Master Bedroom".
_INSERTION_WEIGHT = 2
_DELETION_WEIGHT = 3
_SUBSTITUTION_WEIGHT = 3

# The most edits tolerated between a zone name and an area name
_MAX_EDITS = 5
_MAX_DISTANCE = _MAX_EDITS * _SUBSTITUTION_WEIGHT


class ZoneDevice:
    """Device information for an AirTouch zone.

    Should be constructed using the zone_device() method on the AcDevice class.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        ac_unique_id: str,
        ac_device_id: str,
        airtouch_zone: pyairtouch.Zone,
    ) -> None:
        self._hass = hass
        self._config_entry_id = config_entry_id

        self._unique_id = f"{ac_unique_id}_zone{airtouch_zone.zone_id}"

        self._device_info = device_registry.ChildDeviceInfo(
            identifiers={(DOMAIN, self._unique_id)},
            parent_device_id=ac_device_id,
            name=airtouch_zone.name,
            # We only want to suggest an area that already exists in the Area Registry
            suggested_area=self._find_area(airtouch_zone.name),
        )

        # Always explicitly register the device in case there are no associated
        # entities in the platform.
        self._device_entry = self._register_device()

    @property
    def unique_id(self) -> str:
        """The unique ID for this device.

        This can be used as a prefix for any entities associated with the
        device.
        """
        return self._unique_id

    @property
    def device_info(self) -> device_registry.ChildDeviceInfo:
        """The device registry ChildDeviceInfo for this device."""
        return self._device_info

    def _register_device(self) -> device_registry.ChildDeviceEntry:
        registry = device_registry.async_get(self._hass)
        return registry.async_get_or_create_child(
            config_entry_id=self._config_entry_id, **self._device_info
        )

    def _find_area(self, name: str) -> str | None:
        """Find an area in the area registry using a fuzzy search on a name.

        Returns:
            The discovered area name, or none if no area matches.
        """
        normalized_name = normalize_name(name)

        registry = area_registry.async_get(self._hass)
        areas: list[area_registry.AreaEntry] = list(registry.async_list_areas())

        # Find the closest area match using a basic fuzzy search
        best_distance: int = _MAX_DISTANCE
        best_area: area_registry.AreaEntry | None = None
        for area in areas:
            candidates = [
                area.normalized_name,
                *(normalize_name(a) for a in area.aliases),
            ]
            name_distance = min(
                _weighted_edit_distance(normalized_name, c) for c in candidates
            )
            if name_distance < best_distance:
                best_distance = name_distance
                best_area = area

            if best_distance == 0:
                # Exact match found, we can't do any better than this
                break

        if best_area:
            return best_area.name
        return None


class AcDevice:
    """Device information for an AirTouch air-conditioner.

    Should be constructed using the ac_device() method on the AirTouchDevice class.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        airtouch_unique_id: str,
        airtouch_device_id: str,
        airtouch_ac: pyairtouch.AirConditioner,
    ) -> None:
        self._hass = hass
        self._config_entry_id = config_entry_id

        # ACs get a sequential identifier within an AirTouch system, so include
        # the airtouch unique ID as a prefix.
        self._unique_id = f"{airtouch_unique_id}_ac{airtouch_ac.ac_id}"

        self._device_info = device_registry.DeviceInfo(
            identifiers={(DOMAIN, self._unique_id)},
            name=airtouch_ac.name,
            via_device_id=airtouch_device_id,
        )

        self._device_entry = self._register_device()

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

    def zone_device(self, airtouch_zone: pyairtouch.Zone) -> ZoneDevice:
        """Construct device info for a zone associated with this AC."""
        return ZoneDevice(
            hass=self._hass,
            config_entry_id=self._config_entry_id,
            ac_unique_id=self.unique_id,
            ac_device_id=self._device_entry.id,
            airtouch_zone=airtouch_zone,
        )

    def _register_device(self) -> device_registry.DeviceEntry:
        registry = device_registry.async_get(self._hass)
        return registry.async_get_or_create(
            config_entry_id=self._config_entry_id, **self._device_info
        )


class AirTouchDevice:
    """Device information for the AirTouch controller."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        airtouch: pyairtouch.AirTouch,
    ) -> None:
        self._hass = hass
        self._config_entry_id = config_entry_id

        # For AirTouch 4 systems the serial number doesn't appear to be
        # unique (some logs have shown an all zeroes MAC address). The
        # AirTouch ID is always unique, so we use that here.
        # The airtouch_id will never be None at this stage since the AirTouch object
        # has been initialised.
        self._unique_id = cast("str", airtouch.airtouch_id)

        self._device_info = device_registry.DeviceInfo(
            identifiers={(DOMAIN, self._unique_id)},
            name=airtouch.name,
            manufacturer=MANUFACTURER,
            model=airtouch.model.value,
        )

        # Always explicitly register the device in case there are no associated
        # entities in the platform.
        self._device_entry = self._register_device()

    def ac_device(self, airtouch_ac: pyairtouch.AirConditioner) -> AcDevice:
        """Construct device info for an AC within the AirTouch system."""
        return AcDevice(
            hass=self._hass,
            config_entry_id=self._config_entry_id,
            airtouch_unique_id=self.unique_id,
            airtouch_device_id=self._device_entry.id,
            airtouch_ac=airtouch_ac,
        )

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

    def _register_device(self) -> device_registry.DeviceEntry:
        registry = device_registry.async_get(self._hass)
        return registry.async_get_or_create(
            config_entry_id=self._config_entry_id, **self._device_info
        )


def _weighted_edit_distance(source: str, target: str) -> int:
    """Cost of turning `source` (the zone name) into `target` (the area name).

    Not symmetric: insertions are cheaper than deletions, so a short
    abbreviation is "close" to its full name but not vice versa.
    """
    # This algorithm is an asymmetric implementation of a levenshtein distance algorithm
    # https://en.wikipedia.org/wiki/Levenshtein_distance#Iterative_with_two_matrix_rows
    #
    # Insertions are cheaper than deletions and substitutions because AirTouch zone
    # names are limited to a small number of characters and expected to be abbreviations
    # of area names in Home Assistant.

    # Distance from an empty source to each prefix of target, i.e. the cost of inserting
    # every character of that prefix.
    previous = [j * _INSERTION_WEIGHT for j in range(len(target) + 1)]

    for i, source_char in enumerate(source, start=1):
        # Distance from the first i characters of source to an empty target.
        # i.e. the cost of deleting all of them.
        current = [i * _DELETION_WEIGHT]

        for j, target_char in enumerate(target, start=1):
            substitution = 0 if source_char == target_char else _SUBSTITUTION_WEIGHT
            current.append(
                min(
                    previous[j] + _DELETION_WEIGHT,
                    current[j - 1] + _INSERTION_WEIGHT,
                    previous[j - 1] + substitution,
                )
            )

        previous = current

    return previous[-1]
