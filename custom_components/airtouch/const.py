"""Constants for the Polyaire AirTouch integration."""

import enum

DOMAIN = "airtouch"

MANUFACTURER = "Polyaire"

CONF_VERSION = 1
CONF_MINOR_VERSION = 2

CONF_SPILL_BYPASS = "spill_bypass"


class SpillBypass(enum.Enum):
    """Whether the system has been installed with a bypass damper or spill zone."""

    SPILL = "spill"
    BYPASS = "bypass"
