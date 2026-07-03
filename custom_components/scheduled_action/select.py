from __future__ import annotations

from homeassistant.components.select import SelectEntity

from .const import DOMAIN
from .entity_base import ScheduledActionEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ScheduledActionActionSelect(coordinator)])


class ScheduledActionActionSelect(ScheduledActionEntity, SelectEntity):
    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "action_select")
        self._attr_translation_key = "actions"
        self._attr_icon = "mdi:format-list-bulleted"
        self._attr_current_option = None

    @property
    def options(self) -> list[str]:
        return [item.label for item in self.coordinator.scheduler.actions if item.label]

    @property
    def current_option(self) -> str | None:
        options = self.options
        if self._attr_current_option in options:
            return self._attr_current_option
        if options:
            return options[0]
        return None

    async def async_select_option(self, option: str) -> None:
        if option not in self.options:
            raise ValueError(f"Invalid option: {option}")
        self._attr_current_option = option
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        return {
            "entry_id": self.coordinator.config_entry.entry_id,
            "actions": [
                {
                    "id": item.id,
                    "label": item.label,
                    "target_entity_id": item.target_entity_id,
                    "action": item.action,
                }
                for item in self.coordinator.scheduler.actions
                if item.id and item.label and item.target_entity_id and item.action
            ],
        }
