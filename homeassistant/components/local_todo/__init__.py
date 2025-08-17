"""The Local To-do integration."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.util import slugify

from .const import CONF_STORAGE_KEY, CONF_TODO_LIST_NAME
from .store import LocalTodoListStore

if TYPE_CHECKING:
    from .todo import LocalTodoListEntity

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.TODO]

STORAGE_PATH = ".storage/local_todo.{key}.ics"


class LocalTodoData:
    """Local todo data stored in runtime_data."""

    def __init__(self, store: LocalTodoListStore) -> None:
        """Initialize LocalTodoData."""
        self.store = store
        self.todo_entity: LocalTodoListEntity | None = None


type LocalTodoConfigEntry = ConfigEntry[LocalTodoData]


async def async_setup_entry(hass: HomeAssistant, entry: LocalTodoConfigEntry) -> bool:
    """Set up Local To-do from a config entry."""
    path = Path(hass.config.path(STORAGE_PATH.format(key=entry.data[CONF_STORAGE_KEY])))
    store = LocalTodoListStore(hass, path)
    try:
        await store.async_load()
    except OSError as err:
        raise ConfigEntryNotReady("Failed to load file {path}: {err}") from err

    entry.runtime_data = LocalTodoData(store)

    # Setup todo platform first to create the todo entity
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.TODO])

    # Then setup sensor platform which depends on the todo entity
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry."""
    key = slugify(entry.data[CONF_TODO_LIST_NAME])
    path = Path(hass.config.path(STORAGE_PATH.format(key=key)))

    def unlink(path: Path) -> None:
        path.unlink(missing_ok=True)

    await hass.async_add_executor_job(unlink, path)
