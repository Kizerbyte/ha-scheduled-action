from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity

from .const import DOMAIN
from .entity_base import ScheduledActionEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ScheduledActionHasPendingBinarySensor(coordinator)])


class ScheduledActionHasPendingBinarySensor(ScheduledActionEntity, BinarySensorEntity):
    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "has_pending")
        self._attr_translation_key = "has_pending"
        self._attr_icon = "mdi:timeline-clock-outline"

    @property
    def is_on(self) -> bool:
        return self.coordinator.queue_count > 0
