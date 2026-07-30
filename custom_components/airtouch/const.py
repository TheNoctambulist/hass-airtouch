"""Constants for the Polyaire AirTouch integration."""

import enum

import pyairtouch
from homeassistant.const import PRECISION_HALVES

DOMAIN = "airtouch"

MANUFACTURER = "Polyaire"

CONF_VERSION = 2
CONF_MINOR_VERSION = 2

# Selected AirTouch model during setup
CONF_AIRTOUCH_MODEL = "airtouch_model"

# Indicates whether the AirTouch is set up with a spill zone or with a bypass duct.
CONF_SPILL_BYPASS = "spill_bypass"

# A list of zones that are used as spill zones.
# Only valid if CONF_SPILL_BYPASS == SpillBypass.SPILL
CONF_SPILL_ZONES = "spill_zones"

OPTIONS_MIN_TARGET_TEMPERATURE_STEP = "min_target_temperature_step"
OPTIONS_MIN_TARGET_TEMPERATURE_STEP_DEFAULT = PRECISION_HALVES

# Allow the zone climate entities to change the AC HVAC mode.
OPTIONS_ALLOW_ZONE_HVAC_MODE_CHANGES = "allow_zone_hvac_mode_changes"
OPTIONS_ALLOW_ZONE_HVAC_MODE_CHANGES_DEFAULT = False


class AirTouchModel(enum.Enum):
    """Selected AirTouch model."""

    AUTO_DISCOVER = "auto_discover"
    AIRTOUCH_4 = "airtouch_4"
    AIRTOUCH_5 = "airtouch_5"


AIRTOUCH_MODEL_TO_API = {
    AirTouchModel.AIRTOUCH_4: pyairtouch.AirTouchModel.AIRTOUCH_4,
    AirTouchModel.AIRTOUCH_5: pyairtouch.AirTouchModel.AIRTOUCH_5,
}


class SpillBypass(enum.Enum):
    """Whether the system has been installed with a bypass damper or spill zone."""

    SPILL = "spill"
    BYPASS = "bypass"
