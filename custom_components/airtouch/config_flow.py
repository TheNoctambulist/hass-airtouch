"""Config flow for Polyaire AirTouch."""

from typing import Any

import pyairtouch
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    PRECISION_HALVES,
    PRECISION_TENTHS,
    PRECISION_WHOLE,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    AT4_DEFAULT_PORT,
    AT5_DEFAULT_PORT,
    CONF_MANUAL_CONNECTION,
    CONF_MINOR_VERSION,
    CONF_MODEL,
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
        self, user_input: dict[str, Any] | None = None
    ) -> "config_entries.ConfigFlowResult":
        """Handle a flow initialised by the user.

        Presents a choice between auto-discovery and manual configuration.
        """
        if user_input is not None:
            if user_input.get("connection_method") == "manual":
                return await self.async_step_manual_config()
            return await self.async_step_discover_airtouch()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "connection_method", default="discover"
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value="discover", label="Auto-discover"
                                ),
                                selector.SelectOptionDict(
                                    value="manual", label="Manual configuration"
                                ),
                            ],
                            mode=selector.SelectSelectorMode.LIST,
                            translation_key="connection_method",
                        )
                    ),
                }
            ),
        )

    async def async_step_manual_config(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> "config_entries.ConfigFlowResult":
        """Handle manual configuration of AirTouch connection details."""
        errors: dict[str, str] = {}

        if user_input is not None:
            model_name = user_input[CONF_MODEL]
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            # Convert model name to enum (using getattr since we store enum member names)
            model = getattr(pyairtouch.AirTouchModel, model_name)

            # Try to connect to validate the configuration
            try:
                airtouch = pyairtouch.connect(
                    model=model,
                    host=host,
                    port=port,
                )
                # Initialize to validate connection and get device info
                if await airtouch.init():
                    # Store connection details in context
                    self.context[CONF_HOST] = host  # type: ignore[literal-required]
                    self.context[CONF_PORT] = port  # type: ignore[literal-required]
                    self.context[CONF_MODEL] = model_name  # type: ignore[literal-required]
                    self.context[CONF_MANUAL_CONNECTION] = True  # type: ignore[literal-required]
                    self.context[_CONTEXT_TITLE] = airtouch.name  # type: ignore[literal-required]
                    self.context[_CONTEXT_AIRTOUCH_API] = airtouch  # type: ignore[literal-required]
                    self.context[_CONTEXT_REMAINING_AIRTOUCHES] = []  # type: ignore[literal-required]

                    # Set unique ID based on host and port for manual connections
                    await self.async_set_unique_id(f"{host}:{port}")
                    self._abort_if_unique_id_configured()

                    return await self.async_step_settings()
                else:
                    await airtouch.shutdown()
                    errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"

        # Determine default port based on model selection
        default_port = AT4_DEFAULT_PORT

        return self.async_show_form(
            step_id="manual_config",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_MODEL, default="AIRTOUCH_4"
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value="AIRTOUCH_4", label="AirTouch 4"
                                ),
                                selector.SelectOptionDict(
                                    value="AIRTOUCH_5", label="AirTouch 5"
                                ),
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            translation_key="model",
                        )
                    ),
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=default_port): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=65535)
                    ),
                }
            ),
            errors=errors,
        )

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

        # Build the data dictionary
        entry_data: dict[str, Any] = {
            CONF_HOST: self.context[CONF_HOST],  # type: ignore[literal-required]
            CONF_SPILL_BYPASS: self.context[CONF_SPILL_BYPASS],  # type: ignore[literal-required]
            CONF_SPILL_ZONES: self.context[CONF_SPILL_ZONES],  # type: ignore[literal-required]
        }

        # Add manual connection data if applicable
        if self.context.get(CONF_MANUAL_CONNECTION):  # type: ignore[literal-required]
            entry_data[CONF_MANUAL_CONNECTION] = True
            entry_data[CONF_MODEL] = self.context[CONF_MODEL]  # type: ignore[literal-required]
            entry_data[CONF_PORT] = self.context[CONF_PORT]  # type: ignore[literal-required]

        return self.async_create_entry(
            title=self.context[_CONTEXT_TITLE],  # type: ignore[literal-required]
            data=entry_data,
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
        # Compatibility: Before 2024.12
        # The config_entry constructor parameter can be removed once this
        # backwards compatibility support is removed.
        # Needs to use `dir` because `hasattr` invokes the propery and triggers an
        # exception due to self.config_entry not being permitted for use within
        # the initialiser.
        if "config_entry" not in dir(self):
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
