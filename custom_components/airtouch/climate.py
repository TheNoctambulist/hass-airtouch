"""Polyaire AirTouch Climate Devices."""

import logging
from collections.abc import Mapping
from typing import Any, Optional

import pyairtouch
import voluptuous
from homeassistant.components import climate
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import devices, entities
from .const import (
    DOMAIN,
    OPTIONS_ALLOW_ZONE_HVAC_MODE_CHANGES,
    OPTIONS_ALLOW_ZONE_HVAC_MODE_CHANGES_DEFAULT,
    OPTIONS_MIN_TARGET_TEMPERATURE_STEP,
    OPTIONS_MIN_TARGET_TEMPERATURE_STEP_DEFAULT,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_devices: AddEntitiesCallback,
) -> None:
    """Set up the AirTouch climate devices."""
    airtouch: pyairtouch.AirTouch = hass.data[DOMAIN][config_entry.entry_id]
    min_target_temperature_step = config_entry.options.get(
        OPTIONS_MIN_TARGET_TEMPERATURE_STEP,
        OPTIONS_MIN_TARGET_TEMPERATURE_STEP_DEFAULT,
    )
    allow_zone_hvac_mode_changes = config_entry.options.get(
        OPTIONS_ALLOW_ZONE_HVAC_MODE_CHANGES,
        OPTIONS_ALLOW_ZONE_HVAC_MODE_CHANGES_DEFAULT,
    )

    discovered_entities: list[climate.ClimateEntity] = []

    airtouch_device = devices.AirTouchDevice(hass, config_entry.entry_id, airtouch)
    for airtouch_ac in airtouch.air_conditioners:
        ac_device = airtouch_device.ac_device(airtouch_ac)
        ac_entity = AcClimateEntity(
            ac_device=ac_device,
            airtouch_ac=airtouch_ac,
            min_target_temperature_step=min_target_temperature_step,
        )
        discovered_entities.append(ac_entity)

        # Only zones with temperature sensors can be climate entities
        temp_zones = (zone for zone in airtouch_ac.zones if zone.has_temp_sensor)
        for airtouch_zone in temp_zones:
            zone_device = ac_device.zone_device(airtouch_zone)
            zone_entity = ZoneClimateEntity(
                zone_device_info=zone_device,
                airtouch_ac=airtouch_ac,
                airtouch_zone=airtouch_zone,
                min_target_temperature_step=min_target_temperature_step,
                allow_zone_hvac_mode_changes=allow_zone_hvac_mode_changes,
            )
            discovered_entities.append(zone_entity)

    _LOGGER.debug("Found entities %s", discovered_entities)

    async_add_devices(discovered_entities)

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        name="set_hvac_mode_only",
        schema={
            voluptuous.Required(climate.ATTR_HVAC_MODE): voluptuous.Coerce(
                climate.HVACMode
            )
        },
        func="async_set_hvac_mode_only",
    )

    # Update the climate entities when the configuration changes
    async def update_listener(_: HomeAssistant, config_entry: ConfigEntry) -> None:
        min_target_temperature_step = config_entry.options.get(
            OPTIONS_MIN_TARGET_TEMPERATURE_STEP,
            OPTIONS_MIN_TARGET_TEMPERATURE_STEP_DEFAULT,
        )

        allow_zone_hvac_mode_changes = config_entry.options.get(
            OPTIONS_ALLOW_ZONE_HVAC_MODE_CHANGES,
            OPTIONS_ALLOW_ZONE_HVAC_MODE_CHANGES_DEFAULT,
        )

        for entity in discovered_entities:
            match entity:
                case AcClimateEntity():
                    entity.update_min_target_temperature_step(
                        min_step=min_target_temperature_step
                    )
                case ZoneClimateEntity():
                    entity.update_min_target_temperature_step(
                        min_step=min_target_temperature_step
                    )
                    entity.update_allow_zone_hvac_mode_changes(
                        allow_mode_changes=allow_zone_hvac_mode_changes
                    )

    config_entry.async_on_unload(config_entry.add_update_listener(update_listener))


_AC_POWER_STATE_TO_PRESET = {
    pyairtouch.AcPowerState.OFF: climate.PRESET_NONE,
    pyairtouch.AcPowerState.ON: climate.PRESET_NONE,
    pyairtouch.AcPowerState.OFF_AWAY: climate.PRESET_AWAY,
    pyairtouch.AcPowerState.ON_AWAY: climate.PRESET_AWAY,
    pyairtouch.AcPowerState.SLEEP: climate.PRESET_SLEEP,
}
_CLIMATE_PRESET_TO_AC_POWER_CONTROL = {
    climate.PRESET_AWAY: pyairtouch.AcPowerControl.SET_TO_AWAY,
    climate.PRESET_SLEEP: pyairtouch.AcPowerControl.SET_TO_SLEEP,
}

_AC_TO_CLIMATE_HVAC_MODE = {
    pyairtouch.AcMode.AUTO: climate.HVACMode.HEAT_COOL,
    pyairtouch.AcMode.HEAT: climate.HVACMode.HEAT,
    pyairtouch.AcMode.DRY: climate.HVACMode.DRY,
    pyairtouch.AcMode.FAN: climate.HVACMode.FAN_ONLY,
    pyairtouch.AcMode.COOL: climate.HVACMode.COOL,
}

# Excludes HVACMode.OFF which translates to a power control request for AirTouch.
_CLIMATE_TO_AC_HVAC_MODE = {
    climate.HVACMode.HEAT_COOL: pyairtouch.AcMode.AUTO,
    climate.HVACMode.HEAT: pyairtouch.AcMode.HEAT,
    climate.HVACMode.DRY: pyairtouch.AcMode.DRY,
    climate.HVACMode.FAN_ONLY: pyairtouch.AcMode.FAN,
    climate.HVACMode.COOL: pyairtouch.AcMode.COOL,
}

_AC_TO_CLIMATE_HVAC_ACTION = {
    pyairtouch.AcMode.AUTO: climate.HVACAction.IDLE,
    pyairtouch.AcMode.HEAT: climate.HVACAction.HEATING,
    pyairtouch.AcMode.DRY: climate.HVACAction.DRYING,
    pyairtouch.AcMode.FAN: climate.HVACAction.FAN,
    pyairtouch.AcMode.COOL: climate.HVACAction.COOLING,
}

# Public because it is also used in sensor.py
AC_TO_CLIMATE_FAN_MODE = {
    pyairtouch.AcFanSpeed.AUTO: climate.FAN_AUTO,
    pyairtouch.AcFanSpeed.QUIET: "quiet",
    pyairtouch.AcFanSpeed.LOW: climate.FAN_LOW,
    pyairtouch.AcFanSpeed.MEDIUM: climate.FAN_MEDIUM,
    pyairtouch.AcFanSpeed.HIGH: climate.FAN_HIGH,
    pyairtouch.AcFanSpeed.POWERFUL: "powerful",
    pyairtouch.AcFanSpeed.TURBO: "turbo",
    pyairtouch.AcFanSpeed.INTELLIGENT_AUTO: "intelligent",
}
_CLIMATE_TO_AC_FAN_MODE = {value: key for key, value in AC_TO_CLIMATE_FAN_MODE.items()}


class AcClimateEntity(entities.AirTouchAcEntity, climate.ClimateEntity):
    """A climate entity for an AirTouch Air Conditioner."""

    _attr_name = None  # Name comes from the device info
    _attr_translation_key = "ac_climate"

    # Device Class is not officially supported for climate entities, but this is
    # useful to differentiate the AC and zone climate entities for selectors
    # (e.g. in services.yaml)
    _attr_device_class = "ac"

    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        ac_device: devices.AcDevice,
        airtouch_ac: pyairtouch.AirConditioner,
        min_target_temperature_step: float,
    ) -> None:
        super().__init__(
            ac_device=ac_device,
            airtouch_ac=airtouch_ac,
        )

        self._attr_supported_features = (
            climate.ClimateEntityFeature.FAN_MODE
            | climate.ClimateEntityFeature.TARGET_TEMPERATURE
            | climate.ClimateEntityFeature.PRESET_MODE
        )
        if hasattr(climate.ClimateEntityFeature, "TURN_OFF"):
            # HomeAssistant 2024.2 onwards
            self._attr_supported_features |= (
                climate.ClimateEntityFeature.TURN_OFF
                | climate.ClimateEntityFeature.TURN_ON
            )
            self._enable_turn_on_off_backwards_compatibility = False

        self._attr_target_temperature_step = max(
            airtouch_ac.target_temperature_resolution, min_target_temperature_step
        )

        # The Climate Entity groups the OFF Power State into the HVACMode
        self._attr_hvac_modes = [climate.HVACMode.OFF] + [
            _AC_TO_CLIMATE_HVAC_MODE[mode] for mode in airtouch_ac.supported_modes
        ]
        self._attr_fan_modes = [
            AC_TO_CLIMATE_FAN_MODE[fan_speed]
            for fan_speed in airtouch_ac.supported_fan_speeds
        ]

        self._attr_preset_modes = [climate.PRESET_NONE] + [
            preset
            for preset, ac_power in _CLIMATE_PRESET_TO_AC_POWER_CONTROL.items()
            if ac_power in airtouch_ac.supported_power_controls
        ]

    @property
    def current_temperature(self) -> Optional[float]:
        return self._airtouch_ac.current_temperature

    @property
    def target_temperature(self) -> Optional[float]:
        return self._airtouch_ac.target_temperature

    @property
    def max_temp(self) -> float:
        return self._airtouch_ac.max_target_temperature

    @property
    def min_temp(self) -> float:
        return self._airtouch_ac.min_target_temperature

    @property
    def fan_mode(self) -> str | None:
        if self._airtouch_ac.selected_fan_speed:
            return AC_TO_CLIMATE_FAN_MODE[self._airtouch_ac.selected_fan_speed]
        return None

    @property
    def hvac_mode(self) -> climate.HVACMode | None:
        match self._airtouch_ac.power_state:
            case pyairtouch.AcPowerState.OFF | pyairtouch.AcPowerState.OFF_AWAY:
                return climate.HVACMode.OFF
            case _:
                if self._airtouch_ac.selected_mode:
                    return _AC_TO_CLIMATE_HVAC_MODE[self._airtouch_ac.selected_mode]
        return None

    @property
    def hvac_action(self) -> climate.HVACAction | None:
        match self._airtouch_ac.power_state:
            case pyairtouch.AcPowerState.OFF | pyairtouch.AcPowerState.OFF_AWAY:
                return climate.HVACAction.OFF
            case pyairtouch.AcPowerState.OFF_FORCED:
                return climate.HVACAction.IDLE
            case _:
                if self._airtouch_ac.active_mode:
                    return _AC_TO_CLIMATE_HVAC_ACTION[self._airtouch_ac.active_mode]
        return None

    @property
    def preset_mode(self) -> str:
        if self._airtouch_ac.power_state:
            return _AC_POWER_STATE_TO_PRESET[self._airtouch_ac.power_state]
        return climate.PRESET_NONE

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return AC specific state attributes."""
        last_active_hvac_mode: climate.HVACMode | None = None
        if self._airtouch_ac.selected_mode:
            last_active_hvac_mode = _AC_TO_CLIMATE_HVAC_MODE[
                self._airtouch_ac.selected_mode
            ]
        return {
            # The "current" HVAC mode
            "last_active_hvac_mode": last_active_hvac_mode
        }

    def update_min_target_temperature_step(self, min_step: float) -> None:
        self._attr_target_temperature_step = max(
            self._airtouch_ac.target_temperature_resolution, min_step
        )

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        await self._airtouch_ac.set_fan_speed(_CLIMATE_TO_AC_FAN_MODE[fan_mode])

    async def async_set_hvac_mode(self, hvac_mode: climate.HVACMode) -> None:
        if hvac_mode == climate.HVACMode.OFF:
            await self._airtouch_ac.set_power(pyairtouch.AcPowerControl.TURN_OFF)
        else:
            await self._airtouch_ac.set_mode(
                _CLIMATE_TO_AC_HVAC_MODE[hvac_mode], power_on=True
            )

    async def async_turn_on(self) -> None:
        # Turn the AC on in the last used mode.
        await self._airtouch_ac.set_power(pyairtouch.AcPowerControl.TURN_ON)

    async def async_turn_off(self) -> None:
        await self._airtouch_ac.set_power(pyairtouch.AcPowerControl.TURN_OFF)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        power_control = _CLIMATE_PRESET_TO_AC_POWER_CONTROL.get(preset_mode)
        if power_control:
            await self._airtouch_ac.set_power(power_control)
        elif preset_mode != climate.PRESET_NONE:
            _LOGGER.warning("Unsupported preset mode: %s", preset_mode)

    async def async_set_temperature(self, **kwargs: Any) -> None:  # noqa: ANN401
        temperature: float = kwargs[climate.ATTR_TEMPERATURE]
        await self._airtouch_ac.set_target_temperature(temperature)

        # The "climate.set_temperature" service also allows a HVAC Mode to be specified.
        if climate.ATTR_HVAC_MODE in kwargs:
            await self.async_set_hvac_mode(kwargs[climate.ATTR_HVAC_MODE])

    async def async_set_hvac_mode_only(self, hvac_mode: climate.HVACMode) -> None:
        """Set the HVAC mode without powering on.

        A custom service call that sets the HVAC Mode only without changing the
        current power state. If the AC is currently turned off it will remain
        off. If it is currently on it will remain on.
        """
        if hvac_mode not in _CLIMATE_TO_AC_HVAC_MODE:
            raise ValueError("Unsupported HVAC Mode")
        await self._airtouch_ac.set_mode(_CLIMATE_TO_AC_HVAC_MODE[hvac_mode])


_ZONE_TO_CLIMATE_FAN_MODE = {
    pyairtouch.ZonePowerState.OFF: climate.FAN_OFF,
    pyairtouch.ZonePowerState.ON: climate.FAN_ON,
    pyairtouch.ZonePowerState.TURBO: "turbo",
}
_CLIMATE_TO_ZONE_FAN_MODE = {
    value: key for key, value in _ZONE_TO_CLIMATE_FAN_MODE.items()
}


class ZoneClimateEntity(entities.AirTouchZoneEntity, climate.ClimateEntity):
    """A climate entity for an AirTouch Zone."""

    _attr_name = None  # Name comes from the device info
    _attr_translation_key = "zone_climate"
    _attr_device_class = "zone"

    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        zone_device_info: devices.ZoneDevice,
        airtouch_ac: pyairtouch.AirConditioner,
        airtouch_zone: pyairtouch.Zone,
        min_target_temperature_step: float,
        *,
        allow_zone_hvac_mode_changes: bool,
    ) -> None:
        super().__init__(
            zone_device=zone_device_info,
            airtouch_zone=airtouch_zone,
        )
        self._airtouch_ac = airtouch_ac
        self._allow_zone_hvac_mode_changes = allow_zone_hvac_mode_changes

        self._attr_supported_features = (
            climate.ClimateEntityFeature.FAN_MODE
            | climate.ClimateEntityFeature.TARGET_TEMPERATURE
        )
        if hasattr(climate.ClimateEntityFeature, "TURN_OFF"):
            # HomeAssistant 2024.2 onwards
            self._attr_supported_features |= (
                climate.ClimateEntityFeature.TURN_OFF
                | climate.ClimateEntityFeature.TURN_ON
            )
            self._enable_turn_on_off_backwards_compatibility = False

        self._attr_target_temperature_step = max(
            airtouch_zone.target_temperature_resolution, min_target_temperature_step
        )

        # Only used when allow_zone_hvac_mode_changes is True
        self._attr_hvac_modes = [climate.HVACMode.OFF] + [
            _AC_TO_CLIMATE_HVAC_MODE[mode] for mode in airtouch_ac.supported_modes
        ]

        self._attr_fan_modes = [
            _ZONE_TO_CLIMATE_FAN_MODE[fan_speed]
            for fan_speed in airtouch_zone.supported_power_states
        ]

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._airtouch_ac.subscribe_ac_state(self._async_on_ac_update)

    async def async_will_remove_from_hass(self) -> None:
        await super().async_will_remove_from_hass()
        self._airtouch_ac.unsubscribe_ac_state(self._async_on_ac_update)

    @property
    def hvac_modes(self) -> list[climate.HVACMode]:
        if self._allow_zone_hvac_mode_changes:
            return self._attr_hvac_modes
        # otherwises the Zone can either be off, or on in the current mode of the AC
        if self._airtouch_ac.selected_mode is None:
            return [
                climate.HVACMode.OFF,
            ]
        return [
            climate.HVACMode.OFF,
            _AC_TO_CLIMATE_HVAC_MODE[self._airtouch_ac.selected_mode],
        ]

    @property
    def current_temperature(self) -> Optional[float]:
        return self._airtouch_zone.current_temperature

    @property
    def target_temperature(self) -> Optional[float]:
        return self._airtouch_zone.target_temperature

    @property
    def max_temp(self) -> float:
        return self._airtouch_ac.max_target_temperature

    @property
    def min_temp(self) -> float:
        return self._airtouch_ac.min_target_temperature

    @property
    def fan_mode(self) -> str | None:
        if self._airtouch_zone.power_state:
            return _ZONE_TO_CLIMATE_FAN_MODE[self._airtouch_zone.power_state]
        return None

    @property
    def hvac_mode(self) -> climate.HVACMode | None:
        if self._airtouch_zone.power_state == pyairtouch.ZonePowerState.OFF:
            return climate.HVACMode.OFF

        # If the Zone is on then the mode is as per the parent AC mode
        match self._airtouch_ac.power_state:
            case pyairtouch.AcPowerState.OFF | pyairtouch.AcPowerState.OFF_AWAY:
                return climate.HVACMode.OFF
            case _:
                if self._airtouch_ac.selected_mode:
                    return _AC_TO_CLIMATE_HVAC_MODE[self._airtouch_ac.selected_mode]
        return None

    @property
    def hvac_action(self) -> climate.HVACAction | None:
        if self._airtouch_zone.power_state == pyairtouch.ZonePowerState.OFF:
            return climate.HVACAction.OFF

        # If the zone is on the zone hvac action follows the AC mode.
        match self._airtouch_ac.power_state:
            case pyairtouch.AcPowerState.OFF | pyairtouch.AcPowerState.OFF_AWAY:
                return climate.HVACAction.OFF
            case pyairtouch.AcPowerState.OFF_FORCED:
                return climate.HVACAction.IDLE
            case _:
                if self._airtouch_ac.active_mode:
                    return _AC_TO_CLIMATE_HVAC_ACTION[self._airtouch_ac.active_mode]
        return None

    @property
    def extra_state_attributes(self) -> Optional[Mapping[str, Any]]:
        # Add the control method as an attribute so that this can be seen in
        # Home Assistant. It's unlikely to change often but potentially useful
        # for automations.
        return {"control_method": self._airtouch_zone.control_method.name.lower()}

    def update_min_target_temperature_step(self, min_step: float) -> None:
        self._attr_target_temperature_step = max(
            self._airtouch_ac.target_temperature_resolution, min_step
        )
        self.async_schedule_update_ha_state()

    def update_allow_zone_hvac_mode_changes(self, *, allow_mode_changes: bool) -> None:
        self._allow_zone_hvac_mode_changes = allow_mode_changes
        self.async_schedule_update_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:  # noqa: ANN401
        temperature: float = kwargs[climate.ATTR_TEMPERATURE]
        await self._airtouch_zone.set_target_temperature(temperature)

        # The "climate.set_temperature" service also allows a HVAC Mode to be specified.
        if climate.ATTR_HVAC_MODE in kwargs:
            await self.async_set_hvac_mode(kwargs[climate.ATTR_HVAC_MODE])

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        await self._airtouch_zone.set_power(_CLIMATE_TO_ZONE_FAN_MODE[fan_mode])

    async def async_set_hvac_mode(self, hvac_mode: climate.HVACMode) -> None:
        # Any HVACMode other than OFF is a request to turn the zone on.
        power_state = pyairtouch.ZonePowerState.ON
        if hvac_mode == climate.HVACMode.OFF:
            power_state = pyairtouch.ZonePowerState.OFF

        # If configured to do so, change the AC HVAC mode based on the zone change
        if (
            self._allow_zone_hvac_mode_changes
            and power_state == pyairtouch.ZonePowerState.ON
        ):
            await self._airtouch_ac.set_mode(_CLIMATE_TO_AC_HVAC_MODE[hvac_mode])

        if self._airtouch_zone.power_state != power_state:
            await self._airtouch_zone.set_power(power_state)
        elif (
            power_state == pyairtouch.ZonePowerState.ON
            and self._airtouch_ac.power_state == pyairtouch.AcPowerState.OFF
        ):
            # If the zone is already on, but the AC is off we toggle the zone
            # off then on again. This will trigger the AC to turn on if the
            # AirTouch setting to "Turn the AC on when a zone is turned on" is
            # enabled and mirror the behaviour of the official app.
            await self._airtouch_zone.set_power(pyairtouch.ZonePowerState.OFF)
            await self._airtouch_zone.set_power(pyairtouch.ZonePowerState.ON)

    async def async_turn_on(self) -> None:
        # Turn the zone on by activating it according to the current mode of the
        # AirTouch AC. This will always be an "on" mode even if the AC is turned
        # off.
        if self._airtouch_ac.selected_mode is None:
            raise RuntimeError("AC Mode is unknown")
        await self.async_set_hvac_mode(
            _AC_TO_CLIMATE_HVAC_MODE[self._airtouch_ac.selected_mode]
        )

    async def async_turn_off(self) -> None:
        await self._airtouch_zone.set_power(pyairtouch.ZonePowerState.OFF)

    async def _async_on_ac_update(self, _: int) -> None:
        # We only really need to trigger an update if the AC Mode or Power State
        # have been updated. However this update isn't triggered that often and
        # Home Assistant filters no-change updates internally.
        self.async_schedule_update_ha_state()
