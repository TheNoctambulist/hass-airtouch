# Home Assistant - AirTouch

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

![HACS][hacs-shield]



Integration to integrate with the [Polyaire AirTouch][polyaire-airtouch] smart air conditioner controller.

Supports the AirTouch 4 and AirTouch 5.

![AirTouch](./images/3-console-themes-slider-010-1536x565.webp)

## :computer: Installation
This custom integration is an alternative to the built-in AirTouch 4 and AirTouch 5 integrations.
The built-in integrations are not required for the custom integration to work.

<details>
<summary>Click to expand installation steps...</summary>

### HACS (Preferred)
This integration can be added to Home Assistant as a [custom HACS repository](https://hacs.xyz/docs/faq/custom_repositories):
1. From the HACS page, click the 3 dots at the top right corner.
1. Select `Custom repositories`.
1. Add the URL `https://github.com/thenoctambulist/hass-airtouch`
1. Select the category `Integration`.
1. Click the ADD button.
1. Restart Home Assistant
1. Click the button below, or in the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Polyaire AirTouch"

[![Add integration][my-hass-add-integration-img]][my-hass-add-integration]

### Manual
1. Download the latest release from [here](https://github.com/thenoctambulist/hass-airtouch/releases).
1. Create a folder called `custom_components` in the same directory as the Home Assistant `configuration.yaml`.
1. Extract the contents of the zip into folder called `airtouch` inside `custom_components`.
1. Restart Home Assistant
1. Click the button below, or in the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Polyaire AirTouch"

[![Add integration][my-hass-add-integration-img]][my-hass-add-integration]

</details>

## :gear: Configuration
Configuration of the integration is performed using a config flow in the user interface.
Simply follow the steps shown on screen.

Usually the integration will be able to automatically discover any AirTouch systems on the network and integrate them into Home Assistant.

If your AirTouch system cannot be discovered automatically, the integration will prompt you to enter the host name or IP address of the AirTouch wall panel.

<details>
<summary>Have a firewall?</summary>

The following ports are used for communication between Home Assistant and the AirTouch controller.
You will need to ensure your firewall allows traffic for these ports.

 Device    | Ports 
-----------|-------
AirTouch 4 | TCP: 9004, UDP: 49004
AirTouch 5 | TCP: 9005, UDP: 49005

For automatic discovery to work your network needs to support UDP broadcast.
UDP broadcast may not work if you have installed Home Assistant in a Docker container using the bridge network.

</details>

### :gear: Options
The following options can be modified after set-up via the integration setting page:

 Option                          | Description
---------------------------------|-------------
 Minimum Target Temperature Step | The minumum step when changing the target temperature of climate entities.<br>This is a lower bound and the actual temperature step may bigger if the selected value is not supported by the AirTouch system.

## :bulb: Usage
This integration provides several entities depending on the capabilities of your AirTouch system.
A custom service is provided to allow changing the HVAC mode without changing the current power state of the air-conditioner.

The entities and services are described in the following sections.

### :snowflake: Climate: Air-Conditioner (`climate.<ac_name>`)

For each air-conditioner in the AirTouch system a [**climate**][hass-climate] entity is created.

The climate entity is be named after the air-conditioner, this is often the brand name of the air-conditioner, e.g. Panasonic of Fujitsu.

Use this entity to control the overall state of the system such as the Heating/Coolng Mode, Fan Speed etc.

#### States
 State       | Description
-------------|-------------
 `off`       | When the AC is turned off.<br>Unlike the AirTouch app, the AC mode is not shown when it is turned off.
 `<ac_mode>` | Changing the AC mode to one of the on modes will automatically turn the AC and any `on` zones on in the selected mode.

#### Attributes
 Attribute               | Description 
-------------------------|-------------
 `hvac_modes`            | The available HVAC Modes for the AC.
 `fan_modes`             | The set of fan modes supported by the AC.
 `fan_mode`              | The current fan mode of the AC. It will remain in the last set fan mode even when the AC is turned off.<br>Changing the fan mode will not turn the AC on if it is currently off.
 `last_active_hvac_mode` | The last active HVAC mode.<br>While the AC is turned on this will match the current state. While the AC is turned off the attribute indicates the mode that will become active if the `climate.turn_on` service is called.
 `temperature`           | The target temperature for the AC.<br>*Note*: If you have zones with temperature controllers, changing the target temperature will have no effect.

### :snowflake: Climate: Zone (`climate.<zone_name>`)
If you have any zones set up with a temperature sensor, a separate [**climate**][hass-climate] entity will be created for each zone.

The climate entities for the zones can be used to:
- see the current temperature of the room
- turn the zone on or off
- change the target temperature
- set the zone to turbo (if supported)

#### States
 State       | Description
-------------|-------------
 `off`       | The zone will be in the off state if:<br>- the AC is off; or<br>- the zone is off.
 `<ac_mode>` | If the zone is turned on the zone's state will be the same as the AC's state.<br>If the AirTouch setting "Turn on AC when a zone is being turned on" is enabled, turning a zone on when the AC is off will automatically turn on the AC (and any other zone's that were left on).

#### Attributes
 Attribute     | Description 
---------------|-------------
 `hvac_modes`  | The available HVAC Modes for a zone will dynamically change based on the current AC mode.<br>The list will always have two values: `off` and the current AC mode.
 `fan_modes`   | `on`, `off`, and `turbo` (if supported).<br>Fan speed is controlled by the AC climate entity.
 `fan_mode`    | The fan mode will remain `on` if the zone is on even if the AC is turned off.<br>This can be used to see which zones will be active if the AC is turned on.
 `temperature` | The target temperature for the zone.<br>Changing the target temperature when a zone is in damper control will automatically change it back to being temperature controlled.

### :wind_face: Cover: Zone (`cover.<zone_name>_damper`)
A [**cover**][hass-cover] entity is created for all zones (whether they have) to represent the current damper state.

The cover entity for zones can be used to:
- see the current open percentage of the damper
- turn the zone on or off
- change the damper percentage (not recommended for zones with temperature sensors!)

The damper percentage can only be changed in increments of 5% to align with the official app.

#### States
 State    | Description 
----------|-------------
 `closed` | The zone will be in the closed state if it is turned off.
 `open`   | The zone will be in the open state if it is turned on<br>This state is retained even if the AC is currently turned off to provide an indication of which zones will be active if the AC is turned on.

#### Attributes
 Attribute | Description 
-----------|-------------
 `current_position` | The current open percentage of the damper. 0 is closed, 100 is fully open.<br>Changing the damper percentage when a zone is in temperature control will automatically change it to a fixed damper position.<br>*Note:* The current open percentage reflects the AirTouch algorithm's intended position, it will not be accurate for a zone that is being used as a spill.

#### Using Zones With Thermostat Cards
If you're using the new Thermostat Card in recent versions of Home Assistant and want to enable the *Climate HVAC Modes* feature, some manual customisation is required to show the available HVAC modes correctly.

First add a thermostat card for the air-conditioner entity, then open the HVAC Climate Modes code editor as shown below. Copy the YAML that is shown, then open the same code view for the thermostat card for each zone and paste in the full list of HVAC Modes. Consider creating one zone card and then copy/pasting it for other zones.

  Step 1 | | Step 2 | | Step 3 
 --------|-|--------|-|--------
![](./images/thermostat-card-1.png) | ![][right-arrow]| ![](./images/thermostat-card-2.png) | ![][right-arrow] | ![](./images/thermostat-card-3.png)

### :thermometer: Sensor: Temperature (`sensor.<name>_temperature`)
A temperature [**sensor**][hass-sensor] is created for the main AC and each zone with a temperature sensor.
Dedicated temperature sensors make it easy to use the current temperature in automations or view the temperature value over time in the Home Assistant history view.

These entities can safely be disabled if you are not using them.

#### States
 State     | Description
-----------|-------------
 `<value>` | The current temperature value in °C

### :large_blue_circle: Sensor: Damper Open Percentage (`sensor.<name>_damper_open_percentage`)
A [**sensor**][hass-sensor] is created for the each zone to represent the current open percentage of the damper.
A dedicated sensor entity makes it easy to display the current open percentage in entity cards or view the open perctengate over time in the Home Assistant history view.

These entities can safely be disabled if you are not using them.

#### States
 State     | Description
-----------|-------------
 `<value>` | The current damper open percentage. Range 0-100%<br>The damper open percentage does not take into account spill.

### :twisted_rightwards_arrows: Sensor: Spill Percentage (`sensor.<name>_spill_percentage`)
A [**sensor**][hass-sensor] is created for the each air-conditioner to represent the current spill percentage.

This entity will only be created if one or more spill zones were selected during the integration configuration.
For a system with one spill zone, the actual opening percentage of the zone will be the sum of the spill percentage and the current open percentage.

#### States
 State     | Description
-----------|-------------
 `<value>` | The current spill percentage. The spill percentage may be >100% if there are multiple spill zones.

### :battery: Binary Sensor: Battery (`binary_sensor.<zone_name>_battery`)
A [**binary sensor**][hass-binary] is created for each zone with a temperature sensor to represent the battery state.

#### States
 State            | Description 
------------------|-------------
 `off` (`Normal`) | The temperature sensor battery is healthy.
 `on` (`Low`)     | The battery in the temperature sensor is getting low and will need to be replaced soon.

### :twisted_rightwards_arrows: Binary Sensor: Spill/Bypass (`binary_sensor.<ac/zone_name>_spill/bypass`)
A [**binary sensor**][hass-binary] is created for each air-conditioner and each zone to represent the spill or bypass state according to the configuration selected when the integration was set up.

If your system has a bypass damper installed, only the `binary_sensor.<ac_name>_bypass` sensor for each air-conditioner will be created.
If your system is set up to use one or more zones for spill, you will get a `binary_sensor.<ac_name>_spill` for each air-conditioner and a `binary_sensor.<zone_name>_spill` for each spill zone.

Note: The bypass sensor is only created for the AirTouch 5. Bypass state is not available in the AirTouch 4 API.

#### States
 State            | Description 
------------------|-------------
 `off` (`Closed`) | The AC is not using spill/bypass, or the zone is not active as a spill zone.
 `on` (`Open`)    | The AC is in spill/bypass, or the zone is being used as a spill zone.

### :arrow_up: Update: Console (`update.<airtouch_name>_console`)
An [**update**][hass-update] entity is created to represent the software update status of the AirTouch Console.

The AirTouch API doesn't provide information about the version of any updates, so the `latest_version` attribute just uses a fixed string when an update is available.

#### States
 State  | Description
--------|-------------
 `off`  | The AirTouch software is up to date.
 `on`   | An update is available for the AirTouch software.

#### Attributes
 Attribute           | Description
---------------------|-------------
 `installed_version` | The current version of the AirTouch software.
 `latest_version`    | Matches `installed_version` if the software is update to date.<br>Value will be *"\<Update available>"* if an update is available.

### :snowflake: Polyaire AirTouch: Set HVAC Mode (`airtouch.set_hvac_mode_only`)
A service that sets the HVAC mode without changing the current power state.

This service can be used to change the mode of an air-conditioner while it is turned off without causing it to be turned on.
It may be useful for time based automations.

If the air-conditioner is turned off, the current HVAC mode can be seen in the [`last_active_hvac_mode`](#snowflake-climate-air-conditioner-climateac_name) attribute of the climate entity. 

#### Fields
 Field       | Description
-------------|-------------
 `target`    | An AirTouch air-conditioner climate entity.
 `hvac_mode` | The desired mode for the AirTouch air-conditioner.

#### Example
```yaml
service: airtouch.set_hvac_mode_only
data:
  hvac_mode: cool
target:
  entity_id: climate.panasonic
```

## :yellow_heart: Say Thank You
If you like this integration, please :star: the repository.

If you would like to make a donation as appreciation of my work:

<a href="https://coindrop.to/thenoctambulist" target="_blank"><img src="https://coindrop.to/embed-button.png" style="border-radius: 10px; height: 57px !important;width: 229px !important;" alt="Coindrop.to me"/></a>
<a href="https://www.buymeacoffee.com/thenoctambulist" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-blue.png" style="border-radius: 10px; margin-left: 25px" alt="Buy Me A Coffee" height="57px" width="242px"/></a>

***
[right-arrow]: ./images/right-arrow.png

[polyaire-airtouch]: https://www.airtouch.net.au/
[commits-shield]: https://img.shields.io/github/commit-activity/y/thenoctambulist/hass-airtouch.svg
[commits]: https://github.com/thenoctambulist/hass-airtouch/commits/main
[hacs-shield]: https://img.shields.io/badge/HACS-Custom-blue.svg
[hass-binary]: https://www.home-assistant.io/integrations/binary_sensor/
[hass-climate]: https://www.home-assistant.io/integrations/climate/
[hass-cover]: https://www.home-assistant.io/integrations/cover/
[hass-customizing-entities]: https://www.home-assistant.io/docs/configuration/customizing-devices/
[hass-sensor]: https://www.home-assistant.io/integrations/sensor/
[hass-update]: https://www.home-assistant.io/integrations/update/
[license-shield]: https://img.shields.io/github/license/thenoctambulist/hass-airtouch.svg
[my-hass-add-integration-img]: https://my.home-assistant.io/badges/config_flow_start.svg
[my-hass-add-integration]: https://my.home-assistant.io/redirect/config_flow_start/?domain=airtouch
[releases-shield]: https://img.shields.io/github/release/thenoctambulist/hass-airtouch.svg
[releases]: https://github.com/thenoctambulist/hass-airtouch/releases