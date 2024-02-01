"""Polyaire AirTouch binary sensor entities.

Binary sensors are used to represent:
- whether spill or bypass mode is active for the AC;
- whether spill is active for a Zone; and
- if the battery is low in a zone's temperature sensor.
"""

import logging
from typing import TYPE_CHECKING, Optional

import pyairtouch
from homeassistant.components import binary_sensor
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import devices, entities
from .const import CONF_SPILL_BYPASS, DOMAIN, SpillBypass

if TYPE_CHECKING:
    from collections.abc import Sequence

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_devices: AddEntitiesCallback,
) -> None:
    """Set up the AirTouch binary sensors."""
    api_objects: Sequence[pyairtouch.AirTouch] = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    # When reading serialised configuration, the config data will be the
    # underlying value not the enum value so it needs to be converted to an enum
    # literal for future comparisons.
    spill_bypass = SpillBypass(
        config_entry.data.get(CONF_SPILL_BYPASS, SpillBypass.SPILL)
    )

    discovered_entities: list[binary_sensor.BinarySensorEntity] = []

    for airtouch in api_objects:
        airtouch_device = devices.AirTouchDevice(hass, config_entry.entry_id, airtouch)
        for airtouch_ac in airtouch.air_conditioners:
            ac_device = airtouch_device.ac_device(airtouch_ac)

            if (
                spill_bypass == SpillBypass.SPILL
                # AirTouch 4 doesn't report bypass status, so don't create a sensor.
                or airtouch.model != pyairtouch.AirTouchModel.AIRTOUCH_4
            ):
                ac_spill_entity = AcSpillBypassEntity(
                    spill_bypass=spill_bypass,
                    ac_device=ac_device,
                    airtouch_ac=airtouch_ac,
                )
                discovered_entities.append(ac_spill_entity)

            for airtouch_zone in airtouch_ac.zones:
                zone_device = ac_device.zone_device(airtouch_zone)

                # Zone spill sensors are only useful if the system was not set
                # up with a bypass damper.
                if spill_bypass == SpillBypass.SPILL:
                    zone_spill_entity = ZoneSpillEntity(
                        zone_device=zone_device,
                        airtouch_zone=airtouch_zone,
                    )
                    discovered_entities.append(zone_spill_entity)

                if airtouch_zone.has_temp_sensor:
                    zone_battery_entity = ZoneBatteryEntity(
                        zone_device=zone_device,
                        airtouch_zone=airtouch_zone,
                    )
                    discovered_entities.append(zone_battery_entity)

    _LOGGER.debug("Found entities %s", discovered_entities)
    async_add_devices(discovered_entities)


class AcSpillBypassEntity(entities.AirTouchAcEntity, binary_sensor.BinarySensorEntity):
    """Binary sensor reporting the spill/bypass state of an air-conditioner."""

    _attr_device_class = binary_sensor.BinarySensorDeviceClass.OPENING

    def __init__(
        self,
        spill_bypass: SpillBypass,
        ac_device: devices.AcDevice,
        airtouch_ac: pyairtouch.AirConditioner,
    ) -> None:
        super().__init__(
            ac_device=ac_device,
            airtouch_ac=airtouch_ac,
            id_suffix="_bypass" if spill_bypass == SpillBypass.BYPASS else "_spill",
        )
        self._attr_name = "Bypass" if spill_bypass == SpillBypass.BYPASS else "Spill"

    @property
    def is_on(self) -> Optional[bool]:
        return self._airtouch_ac.spill_state != pyairtouch.AcSpillState.NONE


class ZoneSpillEntity(entities.AirTouchZoneEntity, binary_sensor.BinarySensorEntity):
    """Binary sensor reporting the spill state of a zone."""

    _attr_name = "Spill"
    _attr_device_class = binary_sensor.BinarySensorDeviceClass.OPENING

    def __init__(
        self, zone_device: devices.ZoneDevice, airtouch_zone: pyairtouch.Zone
    ) -> None:
        super().__init__(
            zone_device=zone_device,
            airtouch_zone=airtouch_zone,
            id_suffix="_spill",
        )

    @property
    def is_on(self) -> Optional[bool]:
        return self._airtouch_zone.spill_active


class ZoneBatteryEntity(entities.AirTouchZoneEntity, binary_sensor.BinarySensorEntity):
    """Binary sensor reporting the battery level of a zone's temperature sensor."""

    _attr_name = "Battery"
    _attr_device_class = binary_sensor.BinarySensorDeviceClass.BATTERY

    def __init__(
        self, zone_device: devices.ZoneDevice, airtouch_zone: pyairtouch.Zone
    ) -> None:
        super().__init__(
            zone_device=zone_device,
            airtouch_zone=airtouch_zone,
            id_suffix="_battery",
        )

    @property
    def is_on(self) -> Optional[bool]:
        return (
            self._airtouch_zone.sensor_battery_status
            == pyairtouch.SensorBatteryStatus.LOW
        )
