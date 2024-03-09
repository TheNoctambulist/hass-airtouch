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
    OPTIONS_MIN_TARGET_TEMPERATURE_STEP,
    OPTIONS_MIN_TARGET_TEMPERATURE_STEP_DEFAULT,
    SpillBypass,
)

_CONTEXT_TITLE = "title"
_CONTEXT_DISCOVERED_AIRTOUCHES = "discovered_airtouches"


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

    async def async_step_user(
        self, _: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle a flow initialised by the user."""
        # Only a single instance is allowed since we support discovery of all
        # AirTouch consoles in a single config entry.
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        await self.async_set_unique_id(DOMAIN, raise_on_progress=False)

        return await self.async_step_discover_airtouch()

    async def async_step_discover_airtouch(
        self,
        remote_host: str | None = None,
    ) -> config_entries.FlowResult:
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
        self.context[CONF_HOST] = remote_host

        discovered_airtouches = await pyairtouch.discover(remote_host)
        if discovered_airtouches:
            airtouch_names = [a.name for a in discovered_airtouches]
            self.context[_CONTEXT_TITLE] = ", ".join(airtouch_names)
            self.context[_CONTEXT_DISCOVERED_AIRTOUCHES] = discovered_airtouches
            return await self.async_step_spill_bypass()

        errors: dict[str, str] = {}
        if remote_host:
            # Show an error if the user has entered a hostname and we are
            # re-prompting them after a failed discovery.
            errors[CONF_HOST] = "no_devices_found"

        return await self.async_step_user_host(errors=errors)

    async def async_step_user_host(
        self,
        info: dict[str, Any] | None = None,
        errors: dict[str, str] | None = None,
    ) -> config_entries.FlowResult:
        if not info or errors:
            return self.async_show_form(
                step_id="user_host",
                data_schema=vol.Schema(
                    schema={
                        vol.Required(
                            CONF_HOST, default=self.context.get(CONF_HOST)
                        ): str,
                    }
                ),
                errors=errors,
            )

        return await self.async_step_discover_airtouch(info[CONF_HOST])

    async def async_step_spill_bypass(
        self,
        info: dict[str, Any] | None = None,
    ) -> config_entries.FlowResult:
        if not info:
            return self.async_show_form(
                step_id="spill_bypass",
                data_schema=vol.Schema(
                    schema={
                        vol.Required(
                            CONF_SPILL_BYPASS, default=SpillBypass.SPILL.value
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=[x.value for x in SpillBypass],
                                mode=selector.SelectSelectorMode.DROPDOWN,
                                translation_key=CONF_SPILL_BYPASS,
                            )
                        )
                    },
                ),
            )

        self.context[CONF_SPILL_BYPASS] = SpillBypass(info[CONF_SPILL_BYPASS])
        return await self.async_step_spill_zones()

    async def async_step_spill_zones(
        self,
        info: dict[str, Any] | None = None,
    ) -> config_entries.FlowResult:
        spill_bypass = self.context[CONF_SPILL_BYPASS]
        if spill_bypass == SpillBypass.BYPASS:
            info = {CONF_SPILL_ZONES: []}

        if not info:
            zone_options: list[selector.SelectOptionDict] = []
            for airtouch in self.context[_CONTEXT_DISCOVERED_AIRTOUCHES]:
                if not airtouch.initialised:
                    await airtouch.init()

                # This won't currently handle multiple airtouch systems very well...
                zone_options.extend(
                    [
                        {"label": z.name, "value": str(z.zone_id)}
                        for ac in airtouch.air_conditioners
                        for z in ac.zones
                    ]
                )

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

        for airtouch in self.context[_CONTEXT_DISCOVERED_AIRTOUCHES]:
            if airtouch.initialised:
                await airtouch.shutdown()

        return self.async_create_entry(
            title=self.context[_CONTEXT_TITLE],
            data={
                CONF_HOST: self.context[CONF_HOST],
                CONF_SPILL_BYPASS: spill_bypass,
                CONF_SPILL_ZONES: [int(z) for z in info[CONF_SPILL_ZONES]],
            },
        )


class AirTouchOptionsFlow(config_entries.OptionsFlow):
    """Configures changeable options for the AirTouch integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialise the options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
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
                    )
                }
            ),
        )


def _format_precision(precision: float) -> str:
    return f"{precision:.1f}"
