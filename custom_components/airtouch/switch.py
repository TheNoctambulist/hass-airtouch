"""Polyaire AirTouch switch entities.

Switch entities are used to control turbo mode for zones that support it.
"""

import logging
from typing import TYPE_CHECKING, Any

import pyairtouch
from homeassistant.components import switch

from . import devices, entities
from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_devices: AddEntitiesCallback,
) -> None:
    """Set up the AirTouch switch devices."""
    airtouch: pyairtouch.AirTouch = hass.data[DOMAIN][config_entry.entry_id]

    discovered_entities: list[switch.SwitchEntity] = []

    airtouch_device = devices.AirTouchDevice(hass, config_entry.entry_id, airtouch)
    for airtouch_ac in airtouch.air_conditioners:
        ac_device = airtouch_device.ac_device(airtouch_ac)

        for airtouch_zone in airtouch_ac.zones:
            # Turbo is only available for zones that have been configured to
            # support it on the AirTouch console.
            if (
                pyairtouch.ZonePowerState.TURBO
                not in airtouch_zone.supported_power_states
            ):
                continue

            zone_device = ac_device.zone_device(airtouch_zone)
            zone_turbo_entity = ZoneTurboEntity(
                zone_device=zone_device,
                airtouch=airtouch,
                airtouch_zone=airtouch_zone,
            )
            discovered_entities.append(zone_turbo_entity)

    _LOGGER.debug("Found entities %s", discovered_entities)
    async_add_devices(discovered_entities)


class ZoneTurboEntity(entities.AirTouchZoneEntity, switch.SwitchEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Switch entity to control turbo mode for an AirTouch zone.

    Turbo is one of the "on" power states of a zone. Turning the switch on
    sets the zone to turbo, while turning the switch off returns the zone to
    the normal on state. The zone is never turned off by this entity.
    """

    _attr_name = "Turbo"
    _attr_translation_key = "zone_turbo"

    def __init__(
        self,
        zone_device: devices.ZoneDevice,
        airtouch: pyairtouch.AirTouch,
        airtouch_zone: pyairtouch.Zone,
    ) -> None:
        super().__init__(
            zone_device=zone_device,
            airtouch=airtouch,
            airtouch_zone=airtouch_zone,
            id_suffix="_turbo",
        )

    @property
    def is_on(self) -> bool | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        return self._airtouch_zone.power_state == pyairtouch.ZonePowerState.TURBO

    async def async_turn_on(self, **_: Any) -> None:  # noqa: ANN401
        await self._airtouch_zone.set_power(pyairtouch.ZonePowerState.TURBO)

    async def async_turn_off(self, **_: Any) -> None:  # noqa: ANN401
        # Turbo is an "on" state, so leaving turbo returns the zone to the
        # normal on state. If the zone is not currently in turbo there is
        # nothing to do, and in particular we must not turn an off zone on.
        if self.is_on:
            await self._airtouch_zone.set_power(pyairtouch.ZonePowerState.ON)
