"""Number platform for hive_mqtt_orchestrator."""

from __future__ import annotations

from typing import Any, cast
from dataclasses import dataclass

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.components.number import (
    NumberEntityDescription,
    NumberExtraStoredData,
    NumberMode,
    RestoreNumber,
)
from homeassistant.core import callback
from homeassistant.util import slugify
from homeassistant.util.dt import utcnow
from homeassistant.const import (
    Platform,
    UnitOfInformation,
    CONF_NAME,
    CONF_ENTITIES,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)

from .entity import HiveEntity, HiveEntityDescription

from .utils.attributes import dict_to_typed_dict

from .const import (
    DOMAIN,
    LOGGER,
    CONF_MQTT_TOPIC
)

@dataclass
class HiveNumberEntityDescription(
    HiveEntityDescription,
    NumberEntityDescription,
):
    """Class describing Hive sensor entities."""


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback
    ):
    """Set up the sensor platform."""

    ENTITY_DESCRIPTIONS = (
        HiveNumberEntityDescription(
            key="heating_boost_duration",
            translation_key="heating_boost_duration",
            icon="mdi:timer",
            func=None,
            topic=None,
            entity_category=EntityCategory.CONFIG,
            native_min_value=30,
            native_max_value=180,
            native_step=1,
            mode=NumberMode.SLIDER,
        ),
        HiveNumberEntityDescription(
            key="water_boost_duration",
            translation_key="water_boost_duration",
            icon="mdi:timer",
            func=None,
            topic=None,
            entity_category=EntityCategory.CONFIG,
            native_min_value=30,
            native_max_value=180,
            native_step=1,
            mode=NumberMode.SLIDER,
        ),
        HiveNumberEntityDescription(
            key="heating_frost_prevention",
            translation_key="heating_frost_prevention",
            icon="mdi:snowflake-thermometer",
            func=None,
            topic=None,
            entity_category=EntityCategory.CONFIG,
            native_min_value=5,
            native_max_value=16,
            native_step=0.5,
            mode=NumberMode.SLIDER,
        ),
    )

    _entities = {}

    _entities = [HiveNumber(entity_description=entity_description,) for entity_description in ENTITY_DESCRIPTIONS]

    async_add_entities(
        [sensorEntity for sensorEntity in _entities],
    )

    hass.data[DOMAIN][config_entry.entry_id][Platform.NUMBER] = _entities

class HiveNumber(HiveEntity, RestoreNumber):
    """hive_mqtt_orchestrator Number class."""

    def __init__(
        self,
        entity_description: HiveNumberEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(entity_description)

        self.entity_description = entity_description
        self._attr_unique_id = f"{DOMAIN}_{entity_description.key}".lower()
        self._attr_has_entity_name = True
        self._func = entity_description.func
        self._topic = entity_description.topic
        self._state = None
        self._attributes = {}
        self._last_updated = None

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        self.restored_data = await self.async_get_last_number_data()

        if ((last_state := await self.async_get_last_state()) and
            (last_number_data := await self.async_get_last_number_data())
        ):
            self._attributes = dict_to_typed_dict(last_state.attributes, ["min", "max", "step"])
            if last_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                self._state = last_number_data.native_value

        LOGGER.debug(f'Restored {self.entity_description.key} state: {self._state}')

    @property
    def native_value(self) -> float | None:
        """Return value of number."""
        return self._state

    async def async_set_native_value(self, value: float) -> None:
        """Set value."""
        self._state = value
        self._last_updated = utcnow()
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        """Attributes of the sensor."""
        return self._attributes

    def process_update(self, mqtt_data) -> None:
        """Update the state of the sensor."""
        if (self.hass is not None): # this is a hack to get around the fact that the entity is not yet initialized at first
            self.async_schedule_update_ha_state()