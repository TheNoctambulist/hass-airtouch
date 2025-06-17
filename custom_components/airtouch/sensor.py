"""Polyaire AirTouch sensor entities.

Sensors are used to represent:
- the current temperature for the AC and any zones with sensors; and
- the current damper open percentage for each zone.
"""

import logging
from typing import Any

import pyairtouch
from homeassistant.components import sensor
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import climate, devices, entities
from .const import CONF_SPILL_ZONES, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_devices: AddEntitiesCallback,
) -> None:
    """Set up the AirTouch sensors."""
    airtouch: pyairtouch.AirTouch = hass.data[DOMAIN][config_entry.entry_id]

    spill_zones: list[int] = config_entry.data.get(CONF_SPILL_ZONES, [])

    discovered_entities: list[sensor.SensorEntity] = []

    airtouch_device = devices.AirTouchDevice(hass, config_entry.entry_id, airtouch)
    for airtouch_ac in airtouch.air_conditioners:
        ac_device = airtouch_device.ac_device(airtouch_ac)
        ac_temperature_entity = AcTemperatureEntity(
            ac_device=ac_device,
            airtouch_ac=airtouch_ac,
        )
        discovered_entities.append(ac_temperature_entity)

        ac_error_entity = AcErrorEntity(
            ac_device=ac_device,
            airtouch_ac=airtouch_ac,
        )
        discovered_entities.append(ac_error_entity)

        # Active fan speed is only useful for systems the support intelligent auto.
        if pyairtouch.AcFanSpeed.INTELLIGENT_AUTO in airtouch_ac.supported_fan_speeds:
            ac_fan_speed_entity = AcActiveFanSpeedEntity(
                ac_device=ac_device,
                airtouch_ac=airtouch_ac,
            )
            discovered_entities.append(ac_fan_speed_entity)

        spill_zone_count = 0

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

            if airtouch_zone.zone_id in spill_zones:
                spill_zone_count += 1

        if spill_zone_count > 0:
            ac_spill_percentage_entity = SpillPercentageEntity(
                ac_device=ac_device,
                airtouch_ac=airtouch_ac,
                spill_zone_count=spill_zone_count,
            )
            discovered_entities.append(ac_spill_percentage_entity)

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


class AcActiveFanSpeedEntity(entities.AirTouchAcEntity, sensor.SensorEntity):
    """Sensor reporting the active fan speed of an air-conditioner."""

    _attr_name = "Active Fan Speed"
    _attr_device_class = sensor.SensorDeviceClass.ENUM
    _attr_translation_key = "ac_active_fan_speed"

    def __init__(
        self, ac_device: devices.AcDevice, airtouch_ac: pyairtouch.AirConditioner
    ) -> None:
        super().__init__(
            ac_device=ac_device,
            airtouch_ac=airtouch_ac,
            id_suffix="_active_fan_speed",
        )
        self._attr_options = list(climate.AC_TO_CLIMATE_FAN_MODE.values())

    @property
    def native_value(self) -> str | None:
        if self._airtouch_ac.active_fan_speed:
            return climate.AC_TO_CLIMATE_FAN_MODE[self._airtouch_ac.active_fan_speed]
        return None


_NO_ERROR = "none"


class AcErrorEntity(entities.AirTouchAcEntity, sensor.SensorEntity):
    """Sensor reporting the error state of an air-conditioner."""

    _attr_name = "Error Code"
    _attr_device_class = None  # No appropriate device classes are available.
    _attr_translation_key = "ac_error_code"

    def __init__(
        self, ac_device: devices.AcDevice, airtouch_ac: pyairtouch.AirConditioner
    ) -> None:
        super().__init__(
            ac_device=ac_device, airtouch_ac=airtouch_ac, id_suffix="_error"
        )

    @property
    def native_value(self) -> int | str:
        error_info = self._airtouch_ac.error_info
        if error_info:
            return error_info.code
        return _NO_ERROR

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        error_description: str | None = _NO_ERROR
        error_info = self._airtouch_ac.error_info
        if error_info:
            error_description = error_info.description

        return {"error_description": error_description}


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


class SpillPercentageEntity(entities.AirTouchAcEntity, sensor.SensorEntity):
    """Sensor reporting the current spill percentage for an AC.

    The value may be greater than 100% for ACs with multiple spill zones.
    """

    _attr_name = "Spill Percentage"
    _attr_device_class = None  # No appropriate device classes are available
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = sensor.SensorStateClass.MEASUREMENT

    def __init__(
        self,
        ac_device: devices.AcDevice,
        airtouch_ac: pyairtouch.AirConditioner,
        spill_zone_count: int,
    ) -> None:
        super().__init__(
            ac_device=ac_device,
            airtouch_ac=airtouch_ac,
            id_suffix="_spill_percentage",
            include_zone_subscription=True,
        )
        # The AirTouch algorithm will always ensure that the sum of zone opening
        # percentages remains a minimum opening percentage of:
        #    spill_zone_count * 100
        self._spill_percentage_limit = spill_zone_count * 100

    @property
    def native_value(self) -> int:
        if self._airtouch_ac.power_state in [
            pyairtouch.AcPowerState.OFF,
            pyairtouch.AcPowerState.OFF_AWAY,
        ]:
            return 0

        zone_percentage_sum = sum(
            [
                z.current_damper_percentage
                for z in self._airtouch_ac.zones
                if z.power_state != pyairtouch.ZonePowerState.OFF
            ]
        )
        # The spill percentage can never be less than zero
        return max(0, self._spill_percentage_limit - zone_percentage_sum)
