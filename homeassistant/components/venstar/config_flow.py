"""Config flow to configure venstar component."""

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PIN,
    CONF_SSL,
    CONF_TIMEOUT,
    CONF_USERNAME,
)
from homeassistant.core import callback

from . import CannotConnect, validate_input
from .const import CONF_HUMIDIFIER, CONF_INTERVAL, DEFAULT_SSL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class VenstarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Venstar configuration flow."""

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_import(self, import_info):
        """Set the config entry up from yaml."""
        return await self.async_step_user(import_info)

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}
        if user_input is not None:
            _LOGGER.debug("Received User Form: %s", user_input)
            try:
                client = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors = {"client": "cannot_connect"}

            if "client" not in errors:
                await self.async_set_unique_id(f"{client.addr}_{client.name.lower()}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=client.name, data=user_input)

        _LOGGER.debug("Showing User Form")
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_USERNAME): str,
                    vol.Optional(CONF_PASSWORD): str,
                    vol.Optional(CONF_PIN): str,
                    vol.Optional(CONF_HUMIDIFIER, default=True): bool,
                    vol.Optional(CONF_SSL, default=DEFAULT_SSL): bool,
                    vol.Optional(CONF_TIMEOUT, default=5): int,
                    vol.Optional(CONF_INTERVAL, default=30): int,
                }
            ),
            errors=errors,
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_USERNAME): str,
                    vol.Optional(CONF_PASSWORD): str,
                    vol.Optional(CONF_PIN): str,
                    vol.Optional(CONF_HUMIDIFIER, default=True): bool,
                    vol.Optional(CONF_SSL, default=DEFAULT_SSL): bool,
                    vol.Optional(CONF_TIMEOUT, default=5): int,
                    vol.Optional(CONF_INTERVAL, default=30): int,
                }
            ),
        )
