"""Polyaire AirTouch binary sensor entities.

Binary sensors are used to represent:
- whether spill or bypass mode is active for the AC;
- whether spill is active for a Zone; and
- if the battery is low in a zone's temperature sensor.
"""

import logging
from typing import Optional

import pyairtouch
from homeassistant.components import binary_sensor
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
    """Set up the AirTouch cover devices."""
    api_objects = hass.data[DOMAIN][config_entry.entry_id]

    discovered_entities: list[binary_sensor.BinarySensorEntity] = []

    for airtouch in api_objects:
        airtouch_device = devices.AirTouchDevice(hass, config_entry.entry_id, airtouch)
        for airtouch_ac in airtouch.air_conditioners:
            ac_device = airtouch_device.ac_device(airtouch_ac)
            ac_spill_entity = AcSpillEntity(
                ac_device=ac_device,
                airtouch_ac=airtouch_ac,
            )
            discovered_entities.append(ac_spill_entity)

            for airtouch_zone in airtouch_ac.zones:
                zone_device = ac_device.zone_device(airtouch_zone)
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


class AcSpillEntity(entities.AirTouchAcEntity, binary_sensor.BinarySensorEntity):
    """Binary sensor reporting the spill/bypass state of an air-conditioner."""

    _attr_name = "Spill"
    _attr_device_class = binary_sensor.BinarySensorDeviceClass.OPENING

    def __init__(
        self, ac_device: devices.AcDevice, airtouch_ac: pyairtouch.AirConditioner
    ) -> None:
        super().__init__(
            ac_device=ac_device,
            airtouch_ac=airtouch_ac,
            id_suffix="_spill",
        )

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
