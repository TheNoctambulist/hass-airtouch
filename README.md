# Home Assistant - AirTouch

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

Integration to integrate with the [Polyaire AirTouch][polyaire-airtouch] smart air conditioner controller.

Supports the AirTouch 4 (untested) and AirTouch 5.

**This integration will set up the following platforms.**

Platform | Description
-- | --
`climate` | Separate entities for the main air-conditioners and any temperature controlled zones.
`cover` | A cover entity for each zone.<br>For any zones with temperature sensors it is not recommended to change the damper setting manually.
`binary_sensor` | Binary sensors for the active state of spill/bypass and low battery indicators.

## Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `airtouch`.
1. Download _all_ the files from the `custom_components/airtouch/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Polyaire AirTouch"

No configuration is required. The integration will automatically discover any AirTouch systems on the network.

***
[polyaire-airtouch]: https://www.airtouch.net.au/
[commits-shield]: https://img.shields.io/github/commit-activity/y/thenoctambulist/hass-airtouch.svg
[commits]: https://github.com/thenoctambulist/hass-airtouch/commits/main
[license-shield]: https://img.shields.io/github/license/thenoctambulist/hass-airtouch.svg
[releases-shield]: https://img.shields.io/github/release/thenoctambulist/hass-airtouch.svg
[releases]: https://github.com/thenoctambulist/hass-airtouch/releases