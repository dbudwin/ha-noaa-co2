"""Config flow for NOAA Atmospheric CO2 integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_DATA_FREQUENCY,
    OPTION_WEEKLY,
    OPTION_MONTHLY,
    DEFAULT_FREQUENCY,
    NOAA_WEEKLY_URL,
    NOAA_MONTHLY_URL,
)

_LOGGER = logging.getLogger(__name__)


async def _test_connection(frequency: str) -> bool:
    """Test that the NOAA data file is reachable."""
    url = NOAA_WEEKLY_URL if frequency == OPTION_WEEKLY else NOAA_MONTHLY_URL
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"User-Agent": "HomeAssistant/NOAA-CO2-Integration"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                return resp.status == 200
    except Exception:
        return False


class NOAAco2ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NOAA Atmospheric CO2."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step shown in the UI."""
        # Only allow one instance of this integration
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}

        if user_input is not None:
            frequency = user_input[CONF_DATA_FREQUENCY]
            reachable = await _test_connection(frequency)
            if not reachable:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title="NOAA Atmospheric CO2",
                    data=user_input,
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_DATA_FREQUENCY, default=DEFAULT_FREQUENCY): vol.In(
                    [OPTION_WEEKLY, OPTION_MONTHLY]
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Return the options flow handler."""
        return NOAAco2OptionsFlow(config_entry)


class NOAAco2OptionsFlow(config_entries.OptionsFlow):
    """Handle options (reconfigure after setup)."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            frequency = user_input[CONF_DATA_FREQUENCY]
            reachable = await _test_connection(frequency)
            if not reachable:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="", data=user_input)

        current_frequency = self.config_entry.options.get(
            CONF_DATA_FREQUENCY,
            self.config_entry.data.get(CONF_DATA_FREQUENCY, DEFAULT_FREQUENCY),
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_DATA_FREQUENCY, default=current_frequency): vol.In(
                    [OPTION_WEEKLY, OPTION_MONTHLY]
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )
