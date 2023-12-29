"""Config flow for Polyaire AirTouch."""
import pyairtouch
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_flow

from .const import DOMAIN


async def _async_has_devices(_: HomeAssistant) -> bool:
    """Return if there are devices that can be discovered."""
    airtouches = await pyairtouch.discover()
    return len(airtouches) > 0


config_entry_flow.register_discovery_flow(
    DOMAIN, "Polyaire AirTouch", _async_has_devices
)
