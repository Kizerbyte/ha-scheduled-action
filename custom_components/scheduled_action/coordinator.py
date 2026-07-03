from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    EVENT_TYPE,
    TRIGGER_ASLEEP,
    TRIGGER_AWAKE,
    TRIGGER_AWAY,
    TRIGGER_DATETIME,
    TRIGGER_DELAY,
    TRIGGER_EVENT,
    TRIGGER_HOME,
)
from .storage import ScheduledActionStore, SchedulerConfig

_LOGGER = logging.getLogger(__name__)


class ScheduledActionCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, store: ScheduledActionStore) -> None:
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=f"scheduled_action_{entry.entry_id}",
        )
        self.config_entry = entry
        self.store = store
        self.scheduler = SchedulerConfig.from_entry_data(entry.title, entry.data, entry.options)
        self._unsub_tick = None
        self._unsub_home = None
        self._unsub_sleep = None
        self._unsub_event = None

    async def async_config_entry_first_refresh(self) -> None:
        await self.store.async_load()
        await super().async_config_entry_first_refresh()
        self._ensure_tick()
        self._ensure_state_listeners()
        self._ensure_event_listener()

    async def _async_update_data(self) -> dict[str, Any]:
        return {
            "ts": dt_util.now().isoformat(),
            "queue_count": len(self.store.items),
        }

    @property
    def queue_count(self) -> int:
        return len(self.store.items)

    @property
    def next_item(self):
        if not self.store.items:
            return None
        due_items = [item for item in self.store.items if item.due_at]
        if due_items:
            return sorted(due_items, key=lambda item: item.due_at)[0]
        return self.store.items[0]

    @callback
    def _ensure_tick(self) -> None:
        if self._unsub_tick is None:
            self._unsub_tick = async_track_time_interval(
                self.hass, self._handle_tick, timedelta(seconds=30)
            )

    @callback
    def _ensure_state_listeners(self) -> None:
        if self.scheduler.home_state_entity and self._unsub_home is None:
            self._unsub_home = async_track_state_change_event(
                self.hass, [self.scheduler.home_state_entity], self._handle_home_state
            )
        if self.scheduler.sleep_state_entity and self._unsub_sleep is None:
            self._unsub_sleep = async_track_state_change_event(
                self.hass, [self.scheduler.sleep_state_entity], self._handle_sleep_state
            )

    @callback
    def _ensure_event_listener(self) -> None:
        if self._unsub_event is None:
            self._unsub_event = self.hass.bus.async_listen(EVENT_TYPE, self._handle_named_event)

    async def _handle_tick(self, _now) -> None:
        changed = False
        now = dt_util.now()
        remaining = []
        for item in self.store.items:
            if item.trigger_type in [TRIGGER_DELAY, TRIGGER_DATETIME] and item.due_at:
                due_at = dt_util.parse_datetime(item.due_at)
                if due_at is not None and due_at <= now:
                    ok = await self._execute_item(item)
                    changed = True or changed
                    if not ok:
                        _LOGGER.warning("Failed to execute scheduled action %s", item.item_id)
                    continue
            remaining.append(item)
        if changed:
            self.store.items = remaining
            await self.store.async_save()
            await self.async_request_refresh()
        else:
            self.async_update_listeners()

    async def _execute_item(self, item) -> bool:
        service = None
        domain = "homeassistant"
        if item.action == "turn_on":
            service = "turn_on"
        elif item.action == "turn_off":
            service = "turn_off"
        elif item.action == "toggle":
            service = "toggle"
        elif item.action == "press":
            domain = "button"
            service = "press"

        if service is None:
            return False

        try:
            await self.hass.services.async_call(
                domain,
                service,
                {"entity_id": item.target_entity_id},
                blocking=True,
            )
            return True
        except Exception:
            _LOGGER.exception("Error executing scheduled action %s", item.item_id)
            return False

    async def _run_trigger_type(self, trigger_type: str, event_name: str | None = None) -> None:
        changed = False
        remaining = []
        for item in self.store.items:
            if item.trigger_type == trigger_type:
                if trigger_type == TRIGGER_EVENT and event_name:
                    if str(item.trigger_data.get("event_name", "")) != event_name:
                        remaining.append(item)
                        continue
                await self._execute_item(item)
                changed = True
                continue
            remaining.append(item)
        if changed:
            self.store.items = remaining
            await self.store.async_save()
            await self.async_request_refresh()

    @callback
    def _handle_home_state(self, event) -> None:
        new_state = event.data.get("new_state")
        if new_state is None:
            return
        if new_state.state == "on":
            self.hass.async_create_task(self._run_trigger_type(TRIGGER_HOME))
        elif new_state.state == "off":
            self.hass.async_create_task(self._run_trigger_type(TRIGGER_AWAY))

    @callback
    def _handle_sleep_state(self, event) -> None:
        new_state = event.data.get("new_state")
        if new_state is None:
            return
        if new_state.state == "on":
            self.hass.async_create_task(self._run_trigger_type(TRIGGER_ASLEEP))
        elif new_state.state == "off":
            self.hass.async_create_task(self._run_trigger_type(TRIGGER_AWAKE))

    @callback
    def _handle_named_event(self, event) -> None:
        payload = event.data or {}
        entry_id = payload.get("entry_id")
        if entry_id and entry_id != self.config_entry.entry_id:
            return
        event_name = str(payload.get("event_name", ""))
        self.hass.async_create_task(self._run_trigger_type(TRIGGER_EVENT, event_name=event_name))

    async def async_shutdown(self) -> None:
        for attr in ["_unsub_tick", "_unsub_home", "_unsub_sleep", "_unsub_event"]:
            unsub = getattr(self, attr)
            if unsub is not None:
                unsub()
                setattr(self, attr, None)
