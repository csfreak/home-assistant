"""The venstar component."""
import asyncio
from datetime import timedelta
import logging

from requests.exceptions import RequestException
from venstarcolortouch import VenstarColorTouch
import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PIN,
    CONF_SSL,
    CONF_TIMEOUT,
    CONF_USERNAME,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    COMPONENTS,
    CONF_HUMIDIFIER,
    CONF_INTERVAL,
    DEFAULT_SSL,
    DOMAIN,
    VENSTAR_CLIENT,
    VENSTAR_COORDINATOR,
)

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_USERNAME): str,
        vol.Optional(CONF_PASSWORD): str,
        vol.Optional(CONF_HUMIDIFIER, default=True): cv.boolean,
        vol.Optional(CONF_SSL, default=DEFAULT_SSL): cv.boolean,
        vol.Optional(CONF_TIMEOUT, default=5): cv.positive_int,
        vol.Optional(CONF_PIN): str,
        vol.Optional(CONF_INTERVAL, default=30): cv.positive_int,
    },
    extra=vol.ALLOW_EXTRA,
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.All(cv.ensure_list, [DATA_SCHEMA])}, extra=vol.ALLOW_EXTRA
)


async def validate_input(hass, data):
    """Verify that we can connect to thermostat."""
    username = data.get(CONF_USERNAME)
    password = data.get(CONF_PASSWORD)
    pin = data.get(CONF_PIN)
    host = data.get(CONF_HOST)
    timeout = data.get(CONF_TIMEOUT)
    protocol = "https" if data.get(CONF_SSL) else "http"

    client = VenstarClient(
        hass=hass,
        addr=host,
        timeout=timeout,
        user=username,
        password=password,
        pin=pin,
        proto=protocol,
    )
    if await client.setup():
        _LOGGER.debug(
            "Connected to %s %s at %s", client.model, client._type, client.addr
        )
        return client

    _LOGGER.debug("Unable to connect to thermostat at %s", client.addr)
    raise CannotConnect


async def async_setup(hass, config):
    """Initiate setup of venstar environment."""
    hass.data.setdefault(DOMAIN, {})

    if DOMAIN not in config:
        return True
    for index, conf in enumerate(config[DOMAIN]):
        _LOGGER.debug("Importing Venstar #%d - %s", index, conf[CONF_HOST])
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data=conf,
            )
        )
    return True


async def async_setup_entry(hass, config_entry):
    """Create components for a venstar entry."""
    try:
        client = await validate_input(hass, config_entry.data)
        if not client:
            return False
    except CannotConnect:
        raise exceptions.ConfigEntryNotReady

    async def async_update_data():
        """Update data from venstar thermostat."""

        success = await client.update_data()
        if not success:
            raise UpdateFailed(
                f"Unable to update data for {client.name} at {client.addr}"
            )

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{client.name} at {client.addr}",
        update_method=async_update_data,
        update_interval=timedelta(seconds=config_entry.data.get(CONF_INTERVAL)),
    )

    hass.data[DOMAIN][config_entry.entry_id] = {
        VENSTAR_CLIENT: client,
        CONF_HUMIDIFIER: config_entry.data.get(CONF_HUMIDIFIER),
        VENSTAR_COORDINATOR: coordinator,
    }

    for component in COMPONENTS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, component)
        )

    if not config_entry.update_listeners:
        config_entry.add_update_listener(async_update_options)

    return True


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, component)
                for component in COMPONENTS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok


async def async_update_options(hass, config_entry):
    """Update options."""
    await hass.config_entries.async_reload(config_entry.entry_id)


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class VenstarClient(VenstarColorTouch):
    """Async Wrapper to VenstarColorTouch."""

    def __init__(self, hass, *args, **kwargs):
        """Initialize a VenstarClient object."""
        self.hass = hass
        super().__init__(*args, **kwargs)

    async def setup(self):
        """Login to Thermostat and update data."""
        if await self.hass.async_add_job(self.login):
            return await self.update_data()
        return False

    async def update_data(self):
        """Gather all data from thermostat."""
        try:
            success = all(
                [
                    await self.hass.async_add_job(self.update_info),
                    await self.hass.async_add_job(self.update_sensors),
                ]
            )
        except RequestException:
            return False
        return success

    @property
    def sensors(self):
        """Sensor Data from thermostat."""
        if self._sensors:
            return self._sensors.get("sensors")
        return None
