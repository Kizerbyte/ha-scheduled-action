from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity


class ScheduledActionEntity(CoordinatorEntity):
    _attr_should_poll = False

    def __init__(self, coordinator, suffix: str) -> None:
        super().__init__(coordinator)
        self._entry = coordinator.config_entry
        self._scheduler = coordinator.scheduler
        self._attr_unique_id = f"{self._entry.entry_id}:{suffix}"
        self._attr_has_entity_name = True

    @property
    def device_info(self):
        return {
            "identifiers": {("scheduled_action", self._entry.entry_id)},
            "name": f"{self._scheduler.name} Scheduler",
            "manufacturer": "Custom",
            "model": "Scheduled Action Scheduler",
        }
