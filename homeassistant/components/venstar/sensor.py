"""Sensor for Venstar Thermostat additional sensors."""
import logging

from homeassistant.const import (
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_TEMPERATURE,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
    UNIT_PERCENTAGE,
)
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, HUMID_TYPE, TEMP_TYPE, VENSTAR_CLIENT, VENSTAR_COORDINATOR

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Initialize sensors for a venstar thermostat."""
    domain_data = hass.data[DOMAIN][config_entry.entry_id]
    client = domain_data[VENSTAR_CLIENT]
    coordinator = domain_data[VENSTAR_COORDINATOR]
    sensors = []
    if not client.sensors:
        await client.update_data()
    for sensor in client.sensors:
        if TEMP_TYPE in sensor:
            sensors.append(VenstarSensor(client, coordinator, sensor.get("name")))
        if HUMID_TYPE in sensor:
            sensors.append(
                VenstarSensor(
                    client, coordinator, sensor.get("name"), sensor_type=HUMID_TYPE
                )
            )
    async_add_entities(sensors, False)


class VenstarSensor(Entity):
    """Sensor for Venstar Thermostats."""

    def __init__(self, client, coordinator, name, sensor_type=TEMP_TYPE):
        """Initialize a Venstar Sensor."""
        self._client = client
        self._coordinator = coordinator
        self._name = name
        self._type = sensor_type
        self.type_name = "Temperature" if self._type == TEMP_TYPE else "Humidity"

    @property
    def unique_id(self):
        """Return the uniqueid of the thermostat."""
        return f"{self._client.addr}_{self._client.name.lower()}_sensor_{self._name}_{self._type}"

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._client.name} {self._name} {self.type_name} Sensor"

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        if self._type == TEMP_TYPE:
            return DEVICE_CLASS_TEMPERATURE
        return DEVICE_CLASS_HUMIDITY

    @property
    def unit_of_measurement(self):
        """Return the unit_of_measurement of the sensor."""
        if self._type == TEMP_TYPE:
            if self._client.tempunits == 0:
                return TEMP_FAHRENHEIT
            return TEMP_CELSIUS
        return UNIT_PERCENTAGE

    @property
    def state(self):
        """Return the state of the sensor."""
        for sensor in self._client.sensors:
            if sensor.get("name") == self._name:
                return sensor.get(self._type)
        return None

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update the entity.

        Only used by the generic entity update service.
        """
        await self._coordinator.async_request_refresh()
