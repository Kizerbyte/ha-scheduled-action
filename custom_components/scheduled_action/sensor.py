from __future__ import annotations

from homeassistant.components.sensor import SensorEntity

from .const import DOMAIN
from .entity_base import ScheduledActionEntity
from .text_utils import format_action_key, format_trigger_type


_TRANSLATIONS = {
    "en": {
        "empty": "Empty",
        "queued_one": "1 queued",
        "queued_many": "{count} queued",
    },
    "nl": {
        "empty": "Leeg",
        "queued_one": "1 ingepland",
        "queued_many": "{count} ingepland",
    },
}


def _language(coordinator) -> str:
    language = str(getattr(coordinator.hass.config, "language", "en") or "en").lower()
    return "nl" if language.startswith("nl") else "en"


def _text(coordinator, key: str, **values) -> str:
    language = _language(coordinator)
    template = _TRANSLATIONS.get(language, _TRANSLATIONS["en"])[key]
    return template.format(**values)


def _describe_queue_item(item) -> str:
    if item.label:
        return str(item.label).strip()
    return format_action_key(item.action)


def _queue_item_display_dict(item) -> dict:
    return {
        "item_id": item.item_id,
        "label": str(item.label).strip() if item.label else format_action_key(item.action),
        "target_entity_id": item.target_entity_id,
        "action": format_action_key(item.action),
        "trigger_type": format_trigger_type(item.trigger_type),
        "trigger_label": getattr(item, "trigger_label", None),
        "due_at": item.due_at,
        "status": item.status,
    }


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ScheduledActionQueueCountSensor(coordinator),
            ScheduledActionQueueSensor(coordinator),
            ScheduledActionNextActionSensor(coordinator),
        ]
    )


class ScheduledActionQueueCountSensor(ScheduledActionEntity, SensorEntity):
    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "queue_count")
        self._attr_translation_key = "queue_count"
        self._attr_icon = "mdi:playlist-edit"

    @property
    def native_value(self) -> int:
        return self.coordinator.queue_count

    @property
    def extra_state_attributes(self):
        return {
            "entry_id": self.coordinator.config_entry.entry_id,
            "time_presets_hours": self.coordinator.scheduler.time_presets_hours,
            "home_state_entity": self.coordinator.scheduler.home_state_entity,
            "sleep_state_entity": self.coordinator.scheduler.sleep_state_entity,
            "custom_events": [
                {"label": item.label, "event_name": item.event_name}
                for item in self.coordinator.scheduler.custom_events
            ],
        }


class ScheduledActionQueueSensor(ScheduledActionEntity, SensorEntity):
    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "queue")
        self._attr_translation_key = "queue"
        self._attr_icon = "mdi:format-list-bulleted"

    @property
    def native_value(self) -> str:
        count = self.coordinator.queue_count
        if count == 0:
            return _text(self.coordinator, "empty")
        if count == 1:
            return _text(self.coordinator, "queued_one")
        return _text(self.coordinator, "queued_many", count=count)

    @property
    def extra_state_attributes(self):
        items = list(self.coordinator.store.items)
        return {
            "entry_id": self.coordinator.config_entry.entry_id,
            "queue_lines": [_describe_queue_item(item) for item in items],
            "queue_text": "\n".join(_describe_queue_item(item) for item in items),
            "queue_items": [_queue_item_display_dict(item) for item in items],
        }


class ScheduledActionNextActionSensor(ScheduledActionEntity, SensorEntity):
    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "next_action")
        self._attr_translation_key = "next_action"
        self._attr_icon = "mdi:clock-end"

    @property
    def native_value(self) -> str:
        item = self.coordinator.next_item
        if item is None:
            return _text(self.coordinator, "empty")
        return _describe_queue_item(item)

    @property
    def extra_state_attributes(self):
        item = self.coordinator.next_item
        if item is None:
            return {"entry_id": self.coordinator.config_entry.entry_id}
        data = item.to_dict()
        data["action"] = format_action_key(data.get("action", ""))
        data["trigger_type"] = format_trigger_type(data.get("trigger_type", ""))
        return {"entry_id": self.coordinator.config_entry.entry_id, **data}
