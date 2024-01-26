"""Polyaire AirTouch sensor entities.

Sensors are used to represent:
- the current temperature for the AC and any zones with sensors; and
- the current damper open percentage for each zone.
"""

import logging
from typing import TYPE_CHECKING

import pyairtouch
from homeassistant.components import sensor
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import devices, entities
from .const import DOMAIN

if TYPE_CHECKING:
    from collections.abc import Sequence

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_devices: AddEntitiesCallback,
) -> None:
    """Set up the AirTouch sensors."""
    api_objects: Sequence[pyairtouch.AirTouch] = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    discovered_entities: list[sensor.SensorEntity] = []

    for airtouch in api_objects:
        airtouch_device = devices.AirTouchDevice(hass, config_entry.entry_id, airtouch)
        for airtouch_ac in airtouch.air_conditioners:
            ac_device = airtouch_device.ac_device(airtouch_ac)
            ac_temperature_entity = AcTemperatureEntity(
                ac_device=ac_device,
                airtouch_ac=airtouch_ac,
            )
            discovered_entities.append(ac_temperature_entity)

            for airtouch_zone in airtouch_ac.zones:
                zone_device = ac_device.zone_device(airtouch_zone)
                zone_percentage_entity = ZonePercentageEntity(
                    zone_device=zone_device,
                    airtouch_zone=airtouch_zone,
                )
                discovered_entities.append(zone_percentage_entity)

                if airtouch_zone.has_temp_sensor:
                    zone_temperature_entity = ZoneTemperatureEntity(
                        zone_device=zone_device,
                        airtouch_zone=airtouch_zone,
                    )
                    discovered_entities.append(zone_temperature_entity)

    _LOGGER.debug("Found entities: %s", discovered_entities)
    async_add_devices(discovered_entities)


class AcTemperatureEntity(entities.AirTouchAcEntity, sensor.SensorEntity):
    """Sensor reporting the current temperature of an air-conditioner."""

    _attr_name = "Temperature"
    _attr_device_class = sensor.SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = sensor.SensorStateClass.MEASUREMENT

    def __init__(
        self, ac_device: devices.AcDevice, airtouch_ac: pyairtouch.AirConditioner
    ) -> None:
        super().__init__(
            ac_device=ac_device,
            airtouch_ac=airtouch_ac,
            id_suffix="_temperature",
        )

    @property
    def native_value(self) -> float:
        return self._airtouch_ac.current_temperature


class ZoneTemperatureEntity(entities.AirTouchZoneEntity, sensor.SensorEntity):
    """Sensor reporting the current temperature of a zone."""

    _attr_name = "Temperature"
    _attr_device_class = sensor.SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = sensor.SensorStateClass.MEASUREMENT

    def __init__(
        self, zone_device: devices.ZoneDevice, airtouch_zone: pyairtouch.Zone
    ) -> None:
        super().__init__(
            zone_device=zone_device,
            airtouch_zone=airtouch_zone,
            id_suffix="_temperature",
        )

    @property
    def native_value(self) -> float | None:
        return self._airtouch_zone.current_temperature


class ZonePercentageEntity(entities.AirTouchZoneEntity, sensor.SensorEntity):
    """Sensor reporting the current open percentage of a zone's damper."""

    _attr_name = "Damper Open Percentage"
    _attr_device_class = None  # No appropriate device classes are available
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = sensor.SensorStateClass.MEASUREMENT

    def __init__(
        self, zone_device: devices.ZoneDevice, airtouch_zone: pyairtouch.Zone
    ) -> None:
        super().__init__(
            zone_device=zone_device,
            airtouch_zone=airtouch_zone,
            id_suffix="_open_percentage",
        )

    @property
    def native_value(self) -> int:
        if self._airtouch_zone.power_state == pyairtouch.ZonePowerState.OFF:
            # Force the value to zero when the zone is turned off to have a more
            # accurate record of zone damper percentage history.
            return 0
        return self._airtouch_zone.current_damper_percentage
