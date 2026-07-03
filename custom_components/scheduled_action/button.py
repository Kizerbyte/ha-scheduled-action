from __future__ import annotations

from homeassistant.components.button import ButtonEntity

from .const import DOMAIN
from .entity_base import ScheduledActionEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ScheduledActionClearQueueButton(coordinator)])


class ScheduledActionClearQueueButton(ScheduledActionEntity, ButtonEntity):
    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "clear_queue")
        self._attr_translation_key = "clear_queue"
        self._attr_icon = "mdi:playlist-remove"

    async def async_press(self) -> None:
        self.coordinator.store.items.clear()
        await self.coordinator.store.async_save()
        await self.coordinator.async_request_refresh()
