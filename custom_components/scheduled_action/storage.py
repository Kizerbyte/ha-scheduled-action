from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DEFAULT_TIME_PRESETS_HOURS, DOMAIN

STORAGE_VERSION = 1


def _store_key(entry_id: str) -> str:
    return f"{DOMAIN}.{entry_id}"


@dataclass
class CustomEventDef:
    label: str
    event_name: str

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "CustomEventDef":
        return CustomEventDef(
            label=str(data.get("label", "")).strip(),
            event_name=str(data.get("event_name", "")).strip(),
        )


@dataclass
class ScheduledActionDef:
    id: str
    label: str
    target_entity_id: str
    action: str

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ScheduledActionDef":
        return ScheduledActionDef(
            id=str(data.get("id", "")).strip(),
            label=str(data.get("label", "")).strip(),
            target_entity_id=str(data.get("target_entity_id", "")).strip(),
            action=str(data.get("action", "")).strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QueueItem:
    item_id: str
    target_entity_id: str
    action: str
    trigger_type: str
    trigger_data: dict[str, Any]
    created_at: str
    action_id: str | None = None
    due_at: str | None = None
    label: str | None = None
    trigger_label: str | None = None
    status: str = "pending"

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "QueueItem":
        return QueueItem(
            item_id=str(data["item_id"]),
            target_entity_id=str(data["target_entity_id"]),
            action=str(data["action"]),
            trigger_type=str(data["trigger_type"]),
            trigger_data=dict(data.get("trigger_data", {})),
            created_at=str(data["created_at"]),
            action_id=data.get("action_id"),
            due_at=data.get("due_at"),
            label=data.get("label"),
            trigger_label=data.get("trigger_label"),
            status=str(data.get("status", "pending")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SchedulerConfig:
    name: str
    actions: list[ScheduledActionDef] = field(default_factory=list)
    time_presets_hours: list[float] = field(default_factory=lambda: list(DEFAULT_TIME_PRESETS_HOURS))
    home_state_entity: str | None = None
    sleep_state_entity: str | None = None
    custom_events: list[CustomEventDef] = field(default_factory=list)

    @staticmethod
    def from_entry_data(title: str, data: dict[str, Any], options: dict[str, Any]) -> "SchedulerConfig":
        merged = {**data, **options}
        return SchedulerConfig(
            name=str(merged.get("name") or title),
            actions=[ScheduledActionDef.from_dict(v) for v in merged.get("actions", [])],
            time_presets_hours=[float(v) for v in merged.get("time_presets_hours", DEFAULT_TIME_PRESETS_HOURS)],
            home_state_entity=merged.get("home_state_entity") or None,
            sleep_state_entity=merged.get("sleep_state_entity") or None,
            custom_events=[CustomEventDef.from_dict(v) for v in merged.get("custom_events", [])],
        )


class ScheduledActionStore:
    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(hass, STORAGE_VERSION, _store_key(entry_id))
        self.items: list[QueueItem] = []

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self.items = [QueueItem.from_dict(v) for v in data.get("items", [])]

    async def async_save(self) -> None:
        await self._store.async_save({"items": [item.to_dict() for item in self.items]})
