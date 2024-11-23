"""Config flow for Polyaire AirTouch."""

from typing import Any

import pyairtouch
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    PRECISION_HALVES,
    PRECISION_TENTHS,
    PRECISION_WHOLE,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_MINOR_VERSION,
    CONF_SPILL_BYPASS,
    CONF_SPILL_ZONES,
    CONF_VERSION,
    DOMAIN,
    OPTIONS_ALLOW_ZONE_HVAC_MODE_CHANGES,
    OPTIONS_ALLOW_ZONE_HVAC_MODE_CHANGES_DEFAULT,
    OPTIONS_MIN_TARGET_TEMPERATURE_STEP,
    OPTIONS_MIN_TARGET_TEMPERATURE_STEP_DEFAULT,
    SpillBypass,
)

_CONTEXT_TITLE = "title"
_CONTEXT_AIRTOUCH_API = "airtouch_api"
_CONTEXT_REMAINING_AIRTOUCHES = "remaining_airtouches"


class AirTouchConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configures the AirTouch integration."""

    # Schema version for created config entries
    VERSION = CONF_VERSION
    MINOR_VERSION = CONF_MINOR_VERSION

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return AirTouchOptionsFlow(config_entry)

    # Compatibility: Before 2024.4:
    # Return type is quoted for type checking only since it is new in 2024.4.
    async def async_step_user(
        self, _: dict[str, Any] | None = None
    ) -> "config_entries.ConfigFlowResult":
        """Handle a flow initialised by the user."""
        return await self.async_step_discover_airtouch()

    async def async_step_discover_airtouch(
        self,
        remote_host: str | None = None,
    ) -> "config_entries.ConfigFlowResult":
        """Attempt to discover AirTouch devices on the network.

        Attempts to perform discovery of AirTouch devices. If no remote host is
        specified, broadcast discovery is used. If no devices are found via the
        broadcast discovery the user will be prompted to enter the hostname of
        the AirTouch console for unicast discovery. It's important to allow
        unicast discovery for network configurations that don't support
        broadcast such as when Home Assistant is running on the Docker bridge
        network.

        Args:
            info: accumulated info from any previous steps.
            remote_host: optional remote host to target for discovery.
        """
        # Save the current remote host as context for other steps
        self.context[CONF_HOST] = remote_host  # type: ignore[literal-required]

        discovered_airtouches = await pyairtouch.discover(remote_host)
        airtouches = self._filter_unconfigured(discovered_airtouches)

        if airtouches:
            # If more than one AirTouch is discovered, arbitrarily choose the
            # last one in the list. The user will need to run the config flow
            # again to add the other AirTouch devices.
            airtouch = airtouches.pop()
            self.context[_CONTEXT_TITLE] = airtouch.name  # type: ignore[literal-required]
            self.context[_CONTEXT_AIRTOUCH_API] = airtouch  # type: ignore[literal-required]
            self.context[_CONTEXT_REMAINING_AIRTOUCHES] = airtouches  # type: ignore[literal-required]

            await self.async_set_unique_id(airtouch.airtouch_id)

            return await self.async_step_settings()

        errors: dict[str, str] = {}
        if remote_host:
            # Show an error if the user has entered a hostname and we are
            # re-prompting them after a failed discovery.
            #
            # There are two cases to consider, either no AirTouch was found or
            # the AirTouch that was found had already been discovered.
            if discovered_airtouches:
                errors[CONF_HOST] = "already_configured"
            else:
                errors[CONF_HOST] = "no_devices_found"

        return await self.async_step_user_host(errors=errors)

    async def async_step_user_host(
        self,
        info: dict[str, Any] | None = None,
        errors: dict[str, str] | None = None,
    ) -> "config_entries.ConfigFlowResult":
        if not info or errors:
            return self.async_show_form(
                step_id="user_host",
                data_schema=vol.Schema(
                    schema={
                        vol.Required(
                            CONF_HOST,
                            default=self.context.get(CONF_HOST),
                        ): str,
                    }
                ),
                errors=errors,
            )

        return await self.async_step_discover_airtouch(info[CONF_HOST])

    async def async_step_settings(
        self,
        info: dict[str, Any] | None = None,
    ) -> "config_entries.ConfigFlowResult":
        if not info:
            return self.async_show_form(
                step_id="settings",
                description_placeholders={
                    "airtouch_name": self.context[_CONTEXT_TITLE],  # type: ignore[literal-required]
                },
                data_schema=vol.Schema(
                    schema={
                        vol.Required(
                            OPTIONS_ALLOW_ZONE_HVAC_MODE_CHANGES, default=False
                        ): bool,
                        vol.Required(
                            CONF_SPILL_BYPASS, default=SpillBypass.SPILL.value
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=[x.value for x in SpillBypass],
                                mode=selector.SelectSelectorMode.DROPDOWN,
                                translation_key=CONF_SPILL_BYPASS,
                            )
                        ),
                    },
                ),
            )

        self.context[OPTIONS_ALLOW_ZONE_HVAC_MODE_CHANGES] = info[  # type: ignore[literal-required]
            OPTIONS_ALLOW_ZONE_HVAC_MODE_CHANGES
        ]
        self.context[CONF_SPILL_BYPASS] = SpillBypass(info[CONF_SPILL_BYPASS])  # type: ignore[literal-required]
        return await self.async_step_spill_zones()

    async def async_step_spill_zones(
        self,
        info: dict[str, Any] | None = None,
    ) -> "config_entries.ConfigFlowResult":
        spill_bypass = self.context[CONF_SPILL_BYPASS]  # type: ignore[literal-required]
        if spill_bypass == SpillBypass.BYPASS:
            info = {CONF_SPILL_ZONES: []}

        if not info:
            zone_options: list[selector.SelectOptionDict] = []
            airtouch: pyairtouch.AirTouch = self.context[_CONTEXT_AIRTOUCH_API]  # type: ignore[literal-required]

            await airtouch.init()

            # Zone IDs are unique across all ACs within an AirTouch system.
            zone_options.extend(
                [
                    {"label": z.name, "value": str(z.zone_id)}
                    for ac in airtouch.air_conditioners
                    for z in ac.zones
                ]
            )

            await airtouch.shutdown()

            return self.async_show_form(
                step_id="spill_zones",
                data_schema=vol.Schema(
                    schema={
                        vol.Required(CONF_SPILL_ZONES): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=zone_options,
                                multiple=True,
                                mode=selector.SelectSelectorMode.LIST,
                            )
                        )
                    }
                ),
            )

        self.context[CONF_SPILL_ZONES] = [int(z) for z in info[CONF_SPILL_ZONES]]  # type: ignore[literal-required]

        return await self.async_step_finalise()

    async def async_step_finalise(
        self, info: dict[str, Any] | None = None
    ) -> "config_entries.ConfigFlowResult":
        if info is None and self.context[_CONTEXT_REMAINING_AIRTOUCHES]:  # type: ignore[literal-required]
            # Show an empty form just so that we can put a title and description
            # to notify the user that additional AirTouches have been
            # discovered.
            return self.async_show_form(
                step_id="finalise",
            )

        return self.async_create_entry(
            title=self.context[_CONTEXT_TITLE],  # type: ignore[literal-required]
            data={
                CONF_HOST: self.context[CONF_HOST],  # type: ignore[literal-required]
                CONF_SPILL_BYPASS: self.context[CONF_SPILL_BYPASS],  # type: ignore[literal-required]
                CONF_SPILL_ZONES: self.context[CONF_SPILL_ZONES],  # type: ignore[literal-required]
            },
            options={
                OPTIONS_ALLOW_ZONE_HVAC_MODE_CHANGES: self.context[
                    OPTIONS_ALLOW_ZONE_HVAC_MODE_CHANGES  # type: ignore[literal-required]
                ]
            },
        )

    def _filter_unconfigured(
        self, discovered_airtouches: list[pyairtouch.AirTouch]
    ) -> list[pyairtouch.AirTouch]:
        """Filter to a list of unconfigured AirTouch systems.

        Return a new list of AirTouch systems that contains only those that have
        not already been associated with a config entry. The returned list may
        be empty.
        """
        configured_airtouch_ids = [
            entry.unique_id for entry in self._async_current_entries()
        ]
        return [
            airtouch
            for airtouch in discovered_airtouches
            if airtouch.airtouch_id not in configured_airtouch_ids
        ]


class AirTouchOptionsFlow(config_entries.OptionsFlow):
    """Configures changeable options for the AirTouch integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialise the options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            # Convert to float for storage
            user_input[OPTIONS_MIN_TARGET_TEMPERATURE_STEP] = float(
                user_input.get(
                    OPTIONS_MIN_TARGET_TEMPERATURE_STEP,
                    OPTIONS_MIN_TARGET_TEMPERATURE_STEP_DEFAULT,
                )
            )
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        schema=OPTIONS_ALLOW_ZONE_HVAC_MODE_CHANGES,
                        default=self.config_entry.options.get(
                            OPTIONS_ALLOW_ZONE_HVAC_MODE_CHANGES,
                            OPTIONS_ALLOW_ZONE_HVAC_MODE_CHANGES_DEFAULT,
                        ),
                    ): bool,
                    vol.Required(
                        OPTIONS_MIN_TARGET_TEMPERATURE_STEP,
                        default=_format_precision(
                            self.config_entry.options.get(
                                OPTIONS_MIN_TARGET_TEMPERATURE_STEP,
                                OPTIONS_MIN_TARGET_TEMPERATURE_STEP_DEFAULT,
                            )
                        ),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                _format_precision(PRECISION_WHOLE),
                                _format_precision(PRECISION_HALVES),
                                _format_precision(PRECISION_TENTHS),
                            ],
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    ),
                }
            ),
        )


def _format_precision(precision: float) -> str:
    return f"{precision:.1f}"
