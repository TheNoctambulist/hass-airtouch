"""Constants for the Polyaire AirTouch integration."""

import enum

from homeassistant.const import PRECISION_HALVES

DOMAIN = "airtouch"

MANUFACTURER = "Polyaire"

CONF_VERSION = 1
CONF_MINOR_VERSION = 2

CONF_SPILL_BYPASS = "spill_bypass"

OPTIONS_MIN_TARGET_TEMPERATURE_STEP = "min_target_temperature_step"
OPTIONS_MIN_TARGET_TEMPERATURE_STEP_DEFAULT = PRECISION_HALVES


class SpillBypass(enum.Enum):
    """Whether the system has been installed with a bypass damper or spill zone."""

    SPILL = "spill"
    BYPASS = "bypass"
