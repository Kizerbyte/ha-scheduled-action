from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, TRIGGER_DELAY, TRIGGER_EVENT, TRIGGER_HOME, TRIGGER_AWAY, TRIGGER_ASLEEP, TRIGGER_AWAKE
from .entity_base import ScheduledActionEntity
from .text_utils import format_action_key, format_trigger_type, normalize_trigger_label


def _trigger_display_text(item) -> str:
    trigger = item.trigger_type
    trigger_data = item.trigger_data or {}
    trigger_label = normalize_trigger_label(getattr(item, "trigger_label", None))

    if trigger == TRIGGER_HOME:
        return "when home"
    if trigger == TRIGGER_AWAY:
        return "when away"
    if trigger == TRIGGER_ASLEEP:
        return "when asleep"
    if trigger == TRIGGER_AWAKE:
        return "when awake"
    if trigger == TRIGGER_EVENT:
        if trigger_label:
            return f"on {trigger_label}"
        event_name = trigger_data.get("event_name")
        if event_name:
            return f"on {normalize_trigger_label(event_name)}"
    trigger_text = str(trigger).strip().replace("_", " ").lower()
    return trigger_text


def _describe_queue_item(item) -> str:
    if item.label:
        return str(item.label).strip()

    action_label = format_action_key(item.action)

    if item.trigger_type == TRIGGER_DELAY and item.due_at:
        parsed = dt_util.parse_datetime(item.due_at)
        if parsed is not None:
            local_dt = dt_util.as_local(parsed)
            return f"{action_label} at {local_dt.strftime('%H:%M')}"

    return f"{action_label} {_trigger_display_text(item)}"


def _queue_item_display_dict(item) -> dict:
    return {
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
            return "Empty"
        if count == 1:
            return "1 queued"
        return f"{count} queued"

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
            return "Empty"
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
