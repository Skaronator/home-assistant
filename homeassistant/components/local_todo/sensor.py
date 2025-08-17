"""Sensor platform for the Local Todo integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.json import JsonValueType

from . import LocalTodoConfigEntry

if TYPE_CHECKING:
    from .todo import LocalTodoListEntity

from homeassistant.components.todo import TodoItemStatus

_LOGGER = logging.getLogger(__name__)


SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="total_items",
        translation_key="total_items",
    ),
    SensorEntityDescription(
        key="completed_items",
        translation_key="completed_items",
    ),
    SensorEntityDescription(
        key="open_items",
        translation_key="open_items",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: LocalTodoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Local Todo sensor platform."""
    data = config_entry.runtime_data

    # The todo entity should be available now since todo platform sets up first
    if not data.todo_entity:
        # Log the issue but don't fail - this might be due to todo platform setup failing
        _LOGGER.warning(
            "Todo entity not found during sensor platform setup - skipping sensor creation"
        )
        return

    async_add_entities(
        LocalTodoSensorEntity(data.todo_entity, description)
        for description in SENSOR_DESCRIPTIONS
    )


class LocalTodoSensorEntity(SensorEntity):
    """Local Todo sensor entity."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        todo_entity: LocalTodoListEntity,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the Local Todo sensor entity."""
        self.entity_description = entity_description
        self._todo_entity = todo_entity
        self._attr_unique_id = f"{todo_entity.unique_id}_{entity_description.key}"
        self._attr_device_info = todo_entity.device_info

    @property
    def native_value(self) -> str | None:
        """Return the value of the sensor entity."""
        if not self._todo_entity.todo_items:
            return "0"

        items = self._todo_entity.todo_items

        if self.entity_description.key == "total_items":
            return str(len(items))
        if self.entity_description.key == "completed_items":
            return str(
                sum(1 for item in items if item.status == TodoItemStatus.COMPLETED)
            )
        if self.entity_description.key == "open_items":
            return str(
                sum(1 for item in items if item.status == TodoItemStatus.NEEDS_ACTION)
            )

        return "0"

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._todo_entity.async_subscribe_updates(self._handle_todo_update)
        )
        # Get initial value
        self.async_write_ha_state()

    @callback
    def _handle_todo_update(
        self, todo_items: list[JsonValueType] | None = None
    ) -> None:
        """Handle updates to the todo list."""
        self.async_write_ha_state()
