# Home Assistant - AirTouch

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

![HACS][hacs-shield]



Integration to integrate with the [Polyaire AirTouch][polyaire-airtouch] smart air conditioner controller.

Supports the AirTouch 4 (untested) and AirTouch 5.

![AirTouch](./images/3-console-themes-slider-010-1536x565.webp)

**This integration will set up the following platforms.**

Platform | Description
-- | --
`climate` | Separate entities for the main air-conditioners and any temperature controlled zones.
`cover` | A cover entity for each zone.<br>For any zones with temperature sensors it is not recommended to change the damper setting manually.
`binary_sensor` | Binary sensors for the active state of spill/bypass and low battery indicators.

## Installation

### HACS (Preferred)
This integration can be added to Home Assistant as a [custom HACS repository](https://hacs.xyz/docs/faq/custom_repositories):
1. From the HACS page, click the 3 dots at the top right corner.
1. Select `Custom repositories`.
1. Add the URL `https://github.com/thenoctambulist/hass-airtouch`
1. Select the category `Integration`.
1. Click the ADD button.
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Polyaire AirTouch"

### Manual
1. Download the latest release from [here](https://github.com/thenoctambulist/hass-airtouch/releases).
1. Create a folder called `custom_components` in the same directory as the Home Assistant `configuration.yaml`.
1. Extract the contents of the zip into folder called `airtouch` inside `custom_components`.
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Polyaire AirTouch"

## Configuration
No configuration is required.
The integration will automatically discover any AirTouch systems on the network and integrate them into Home Assistant.

## Say Thank You
If you would like to make a donation as appreciation of my work, please use the link below:

<a href="https://www.buymeacoffee.com/thenoctambulist" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-blue.png" alt="Buy Me A Coffee" height="41" width="174"></a>

***
[polyaire-airtouch]: https://www.airtouch.net.au/
[commits-shield]: https://img.shields.io/github/commit-activity/y/thenoctambulist/hass-airtouch.svg
[commits]: https://github.com/thenoctambulist/hass-airtouch/commits/main
[hacs-shield]: https://img.shields.io/badge/HACS-Custom-blue.svg
[license-shield]: https://img.shields.io/github/license/thenoctambulist/hass-airtouch.svg
[releases-shield]: https://img.shields.io/github/release/thenoctambulist/hass-airtouch.svg
[releases]: https://github.com/thenoctambulist/hass-airtouch/releases