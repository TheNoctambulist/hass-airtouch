"""Polyaire AirTouch time sensor entities.

Time entities are used to represent:
- The on/off quick timers for each AC.
"""

import datetime
import logging

import pyairtouch
import voluptuous
from homeassistant.components import time
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation, entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import devices, entities
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_devices: AddEntitiesCallback,
) -> None:
    """Set up the AirTouch binary sensors."""
    airtouch: pyairtouch.AirTouch = hass.data[DOMAIN][config_entry.entry_id]

    discovered_entities: list[time.TimeEntity] = []

    airtouch_device = devices.AirTouchDevice(hass, config_entry.entry_id, airtouch)
    for airtouch_ac in airtouch.air_conditioners:
        ac_device = airtouch_device.ac_device(airtouch_ac)

        for timer_type in pyairtouch.AcTimerType:
            timer_entity = AcQuickTimerEntity(
                timer_type=timer_type,
                ac_device=ac_device,
                airtouch_ac=airtouch_ac,
            )
            discovered_entities.append(timer_entity)

    _LOGGER.debug("Found entities %s", discovered_entities)
    async_add_devices(discovered_entities)

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        name="clear_timer",
        schema={},
        func="async_clear_timer",
    )
    platform.async_register_entity_service(
        name="set_timer_from_delay",
        schema={voluptuous.Required("delay"): config_validation.positive_time_period},
        func="async_set_timer_from_delay",
    )


_TIMER_TYPE_NAME_MAPPING = {
    pyairtouch.AcTimerType.OFF_TIMER: "Off Timer",
    pyairtouch.AcTimerType.ON_TIMER: "On Timer",
}


class AcQuickTimerEntity(entities.AirTouchAcEntity, time.TimeEntity):
    """Time entity for an AirTouch AC Quick Timer."""

    _attr_icon = "mdi:fan-clock"

    def __init__(
        self,
        timer_type: pyairtouch.AcTimerType,
        ac_device: devices.AcDevice,
        airtouch_ac: pyairtouch.AirConditioner,
    ) -> None:
        super().__init__(
            ac_device=ac_device,
            airtouch_ac=airtouch_ac,
            id_suffix="_" + timer_type.name.lower(),
        )
        self._timer_type = timer_type
        self._attr_name = _TIMER_TYPE_NAME_MAPPING[timer_type]

    @property
    def native_value(self) -> datetime.time | None:  # type: ignore[override] # MyPy reports an error here even though the signature is identical!
        return self._airtouch_ac.next_quick_timer(self._timer_type)

    async def async_set_value(self, value: datetime.time) -> None:
        await self._airtouch_ac.set_quick_timer(self._timer_type, value)

    async def async_set_timer_from_delay(self, delay: datetime.timedelta) -> None:
        await self._airtouch_ac.set_quick_timer(self._timer_type, delay)

    async def async_clear_timer(self) -> None:
        await self._airtouch_ac.clear_quick_timer(self._timer_type)
