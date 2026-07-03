from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, TRIGGER_DELAY, TRIGGER_EVENT, TRIGGER_HOME, TRIGGER_AWAY, TRIGGER_ASLEEP, TRIGGER_AWAKE
from .entity_base import ScheduledActionEntity
from .text_utils import format_action_key, format_trigger_type, normalize_trigger_label, strip_trigger_suffix


_TRANSLATIONS = {
    "en": {
        "empty": "Empty",
        "queued_one": "1 queued",
        "queued_many": "{count} queued",
        "when_home": "when home",
        "when_away": "when away",
        "when_asleep": "when asleep",
        "when_awake": "when awake",
        "on_label": "on {label}",
        "at_time": "{action} at {time}",
    },
    "nl": {
        "empty": "Leeg",
        "queued_one": "1 ingepland",
        "queued_many": "{count} ingepland",
        "when_home": "wanneer thuis",
        "when_away": "wanneer weg",
        "when_asleep": "wanneer slapend",
        "when_awake": "wanneer wakker",
        "on_label": "bij {label}",
        "at_time": "{action} om {time}",
    },
}


def _language(coordinator) -> str:
    language = str(getattr(coordinator.hass.config, "language", "en") or "en").lower()
    return "nl" if language.startswith("nl") else "en"


def _text(coordinator, key: str, **values) -> str:
    language = _language(coordinator)
    template = _TRANSLATIONS.get(language, _TRANSLATIONS["en"])[key]
    return template.format(**values)


def _trigger_display_text(coordinator, item) -> str:
    trigger = item.trigger_type
    trigger_data = item.trigger_data or {}
    trigger_label = normalize_trigger_label(getattr(item, "trigger_label", None))

    if trigger == TRIGGER_HOME:
        return _text(coordinator, "when_home")
    if trigger == TRIGGER_AWAY:
        return _text(coordinator, "when_away")
    if trigger == TRIGGER_ASLEEP:
        return _text(coordinator, "when_asleep")
    if trigger == TRIGGER_AWAKE:
        return _text(coordinator, "when_awake")
    if trigger == TRIGGER_EVENT:
        if trigger_label:
            return _text(coordinator, "on_label", label=trigger_label)
        event_name = trigger_data.get("event_name")
        if event_name:
            return _text(coordinator, "on_label", label=normalize_trigger_label(event_name))
    trigger_text = str(trigger).strip().replace("_", " ").lower()
    return trigger_text


def _describe_queue_item(coordinator, item) -> str:
    action_label = strip_trigger_suffix(item.label) if item.label else format_action_key(item.action)

    if item.trigger_type == TRIGGER_DELAY and item.due_at:
        parsed = dt_util.parse_datetime(item.due_at)
        if parsed is not None:
            local_dt = dt_util.as_local(parsed)
            return _text(coordinator, "at_time", action=action_label, time=local_dt.strftime('%H:%M'))

    return f"{action_label} {_trigger_display_text(coordinator, item)}"


def _queue_item_display_dict(item) -> dict:
    return {
        "label": strip_trigger_suffix(item.label) if item.label else format_action_key(item.action),
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
            "queue_lines": [_describe_queue_item(self.coordinator, item) for item in items],
            "queue_text": "\n".join(_describe_queue_item(self.coordinator, item) for item in items),
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
        return _describe_queue_item(self.coordinator, item)

    @property
    def extra_state_attributes(self):
        item = self.coordinator.next_item
        if item is None:
            return {"entry_id": self.coordinator.config_entry.entry_id}
        data = item.to_dict()
        data["action"] = format_action_key(data.get("action", ""))
        data["trigger_type"] = format_trigger_type(data.get("trigger_type", ""))
        return {"entry_id": self.coordinator.config_entry.entry_id, **data}
