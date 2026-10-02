"""Config flow for FW Locations."""

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_AMBULANCE_STATIONS,
    CONF_FIRE_STATIONS,
    CONF_HOSPITALS,
    CONF_RADIUS_KM,
    DEFAULT_AMBULANCE_STATIONS,
    DEFAULT_FIRE_STATIONS,
    DEFAULT_HOSPITALS,
    DEFAULT_RADIUS_KM,
    DOMAIN,
    MAX_RADIUS_KM,
    MIN_RADIUS_KM,
)


def _schema(defaults: dict[str, Any]) -> vol.Schema:
    """Return the configuration schema."""
    return vol.Schema(
        {
            vol.Required(
                CONF_RADIUS_KM,
                default=defaults.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM),
            ): vol.All(
                vol.Coerce(float),
                vol.Range(min=MIN_RADIUS_KM, max=MAX_RADIUS_KM),
            ),
            vol.Required(
                CONF_FIRE_STATIONS,
                default=defaults.get(CONF_FIRE_STATIONS, DEFAULT_FIRE_STATIONS),
            ): bool,
            vol.Required(
                CONF_HOSPITALS,
                default=defaults.get(CONF_HOSPITALS, DEFAULT_HOSPITALS),
            ): bool,
            vol.Required(
                CONF_AMBULANCE_STATIONS,
                default=defaults.get(
                    CONF_AMBULANCE_STATIONS,
                    DEFAULT_AMBULANCE_STATIONS,
                ),
            ): bool,
        }
    )


def _at_least_one_category(data: dict[str, Any]) -> bool:
    """Return True if at least one category is enabled."""
    return any(
        data.get(key, False)
        for key in (
            CONF_FIRE_STATIONS,
            CONF_HOSPITALS,
            CONF_AMBULANCE_STATIONS,
        )
    )


class FwLocConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FW Locations."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "FwLocOptionsFlow":
        """Get the options flow."""
        return FwLocOptionsFlow(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}

        if user_input is not None:
            if not _at_least_one_category(user_input):
                errors["base"] = "select_one_category"
            else:
                return self.async_create_entry(
                    title="FW Locations",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input or {}),
            errors=errors,
        )


class FwLocOptionsFlow(config_entries.OptionsFlow):
    """Handle FW Locations options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Manage FW Locations options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not _at_least_one_category(user_input):
                errors["base"] = "select_one_category"
            else:
                return self.async_create_entry(title="", data=user_input)

        defaults = {
            **self._config_entry.data,
            **self._config_entry.options,
        }

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(user_input or defaults),
            errors=errors,
        )
