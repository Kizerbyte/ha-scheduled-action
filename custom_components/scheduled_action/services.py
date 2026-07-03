from __future__ import annotations

from datetime import timedelta
import logging
import uuid

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ICON,
    DOMAIN,
    EVENT_TYPE,
    MAX_CUSTOM_EVENTS,
    SERVICE_CANCEL,
    SERVICE_CANCEL_ALL,
    SERVICE_FIRE_EVENT,
    SERVICE_GET_POPUP_CONTEXT,
    SERVICE_OPEN_POPUP,
    SERVICE_SCHEDULE,
    TRIGGER_ASLEEP,
    TRIGGER_AWAKE,
    TRIGGER_AWAY,
    TRIGGER_DATETIME,
    TRIGGER_DELAY,
    TRIGGER_EVENT,
    TRIGGER_HOME,
)
from .storage import QueueItem
from .text_utils import normalize_label, normalize_trigger_label, strip_trigger_suffix

_LOGGER = logging.getLogger(__name__)

_DELAY_ICON_WORDS = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
}


def _coordinator_for_entry(hass: HomeAssistant, entry_id: str):
    return hass.data.get(DOMAIN, {}).get(entry_id)


def _format_time_preset_label(hours: float) -> str:
    if hours < 1:
        minutes = int(round(hours * 60))
        return f"In {minutes} mins"
    if float(hours).is_integer():
        whole = int(hours)
        unit = "hour" if whole == 1 else "hours"
        return f"In {whole} {unit}"
    return f"In {hours:g} hours"


def _entry_slug(name: str) -> str:
    return "_".join(str(name).strip().lower().split())


def _entity_id_for_unique_suffix(hass: HomeAssistant, coordinator, domain: str, suffix: str, fallback: str) -> str:
    entity_registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(entity_registry, coordinator.config_entry.entry_id)
    unique_id = f"{coordinator.config_entry.entry_id}:{suffix}"
    for entry in entries:
        if entry.domain == domain and entry.unique_id == unique_id:
            return entry.entity_id
    return fallback


def _action_select_entity_id(hass: HomeAssistant, coordinator) -> str:
    slug = _entry_slug(coordinator.scheduler.name)
    return _entity_id_for_unique_suffix(
        hass,
        coordinator,
        "select",
        "action_select",
        f"select.{slug}_scheduler_actions",
    )


def _clear_queue_entity_id(hass: HomeAssistant, coordinator) -> str:
    slug = _entry_slug(coordinator.scheduler.name)
    return _entity_id_for_unique_suffix(
        hass,
        coordinator,
        "button",
        "clear_queue",
        f"button.{slug}_scheduler_clear_queue",
    )


def _queue_sensor_entity_id(hass: HomeAssistant, coordinator) -> str:
    slug = _entry_slug(coordinator.scheduler.name)
    return _entity_id_for_unique_suffix(
        hass,
        coordinator,
        "sensor",
        "queue",
        f"sensor.{slug}_scheduler_queue",
    )


def _popup_context_for_coordinator(coordinator) -> dict:
    scheduler = coordinator.scheduler

    time_presets = [
        {
            "key": f"preset_{idx}",
            "hours": hours,
            "label": _format_time_preset_label(hours),
            "trigger": {"type": TRIGGER_DELAY, "hours": hours},
        }
        for idx, hours in enumerate(scheduler.time_presets_hours, start=1)
        if hours is not None
    ]

    event_presets = []
    if scheduler.home_state_entity:
        event_presets.extend(
            [
                {"key": "home", "label": "When home", "trigger": {"type": TRIGGER_HOME}},
                {"key": "away", "label": "When away", "trigger": {"type": TRIGGER_AWAY}},
            ]
        )
    if scheduler.sleep_state_entity:
        event_presets.extend(
            [
                {"key": "asleep", "label": "When asleep", "trigger": {"type": TRIGGER_ASLEEP}},
                {"key": "awake", "label": "When awake", "trigger": {"type": TRIGGER_AWAKE}},
            ]
        )

    custom_events = [
        {
            "key": item.event_name or f"event_{idx}",
            "label": normalize_label(item.label),
            "event_name": item.event_name,
            "icon": item.icon or "mdi:alarm",
            "trigger": {"type": TRIGGER_EVENT, "event_name": item.event_name},
        }
        for idx, item in enumerate(scheduler.custom_events, start=1)
        if item.label and item.event_name
    ]
    event_presets.extend(custom_events)

    actions = [
        {
            "id": item.id,
            "label": normalize_label(item.label),
            "target_entity_id": item.target_entity_id,
            "action": item.action,
        }
        for item in scheduler.actions
        if item.id and item.label and item.target_entity_id and item.action
    ]

    context = {
        "entry_id": coordinator.config_entry.entry_id,
        "scheduler_name": scheduler.name,
        "device_name": f"{scheduler.name} Scheduler",
        "home_state_entity": scheduler.home_state_entity,
        "sleep_state_entity": scheduler.sleep_state_entity,
        "has_home_state": bool(scheduler.home_state_entity),
        "has_sleep_state": bool(scheduler.sleep_state_entity),
        "has_custom_events": bool(custom_events),
        "has_home_trigger": bool(scheduler.home_state_entity),
        "has_away_trigger": bool(scheduler.home_state_entity),
        "has_asleep_trigger": bool(scheduler.sleep_state_entity),
        "has_awake_trigger": bool(scheduler.sleep_state_entity),
        "actions": actions,
        "action_labels": [item["label"] for item in actions],
        "action_select_entity": _action_select_entity_id(coordinator.hass, coordinator),
        "time_presets": time_presets,
        "event_presets": event_presets,
        "custom_events": custom_events,
        "custom_event_labels": [item["label"] for item in custom_events],
    }

    for idx, item in enumerate(time_presets[:4], start=1):
        context[f"preset_{idx}_label"] = item["label"]
        context[f"preset_{idx}_hours"] = item["hours"]

    for idx in range(len(time_presets) + 1, 5):
        context[f"preset_{idx}_label"] = None
        context[f"preset_{idx}_hours"] = None

    for idx in range(1, MAX_CUSTOM_EVENTS + 1):
        if idx <= len(custom_events):
            item = custom_events[idx - 1]
            context[f"custom_event_{idx}_label"] = item["label"]
            context[f"custom_event_{idx}_name"] = item["event_name"]
            context[f"custom_event_{idx}_icon"] = item.get("icon") or "mdi:alarm"
        else:
            context[f"custom_event_{idx}_label"] = None
            context[f"custom_event_{idx}_name"] = None
            context[f"custom_event_{idx}_icon"] = None

    return context


async def async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_SCHEDULE):
        return

    async def _open_popup(call: ServiceCall) -> None:
        entry_id = str(call.data["entry_id"])
        browser_id = str(call.data["browser_id"])
        _LOGGER.debug(
            "open_popup called: entry_id=%s browser_id=%r raw_data=%s",
            entry_id,
            browser_id,
            dict(call.data),
        )
        coordinator = _coordinator_for_entry(hass, entry_id)
        if coordinator is None:
            _LOGGER.warning("open_popup: no coordinator found for entry_id=%s", entry_id)
            return

        popup = _popup_context_for_coordinator(coordinator)
        action_select_entity = popup.get("action_select_entity")
        _LOGGER.debug(
            "open_popup: resolved scheduler=%s action_select_entity=%s actions=%s",
            popup.get("scheduler_name"),
            action_select_entity,
            len(popup.get("actions", [])),
        )
        if not action_select_entity:
            _LOGGER.warning("open_popup: missing action_select_entity for entry_id=%s", entry_id)
            return

        def _delay_icon(hours: float) -> str:
            if hours < 1:
                return "mdi:clock-fast"
            if float(hours).is_integer():
                word = _DELAY_ICON_WORDS.get(int(hours))
                if word:
                    return f"mdi:clock-time-{word}-outline"
            return "mdi:clock-outline"

        time_preset_cards = []
        for idx in range(1, 5):
            preset_label = popup.get(f"preset_{idx}_label")
            preset_hours = popup.get(f"preset_{idx}_hours")
            if preset_label is None or preset_hours is None:
                continue
            time_preset_cards.append(
                {
                    "type": "button",
                    "show_name": True,
                    "show_icon": True,
                    "show_state": False,
                    "name": preset_label,
                    "icon": _delay_icon(float(preset_hours)),
                    "tap_action": {
                        "action": "call-service",
                        "service": "script.scheduled_action_schedule_from_select",
                        "data": {
                            "browser_id": browser_id,
                            "entry_id": entry_id,
                            "action_select_entity": action_select_entity,
                            "trigger_type": "delay",
                            "trigger_hours": preset_hours,
                            "trigger_label": preset_label,
                        },
                    },
                }
            )

        cards = [
            {
                "type": "clock",
                "clock_style": "digital",
                "clock_size": "small",
                "show_seconds": False,
                "no_background": True,
                "face_style": "markers",
            },
            {
                "type": "markdown",
                "text_only": True,
                "content": (
                    "<ha-icon icon=\"mdi:select-place\"></ha-icon> "
                    "<strong>Select action</strong>"
                ),
            },
            {
                "type": "entities",
                "show_header_toggle": False,
                "state_color": False,
                "entities": [
                    {
                        "entity": action_select_entity,
                        "name": "Selected action",
                    }
                ],
            },
            {
                "type": "markdown",
                "text_only": True,
                "content": (
                    "<ha-icon icon=\"mdi:clock-start\"></ha-icon> "
                    "<strong>Select trigger</strong>"
                ),
            },
        ]

        if time_preset_cards:
            cards.append(
                {
                    "type": "grid",
                    "square": False,
                    "columns": min(4, len(time_preset_cards)),
                    "cards": time_preset_cards,
                }
            )

        state_cards = []
        if popup.get("has_home_trigger"):
            state_cards.extend(
                [
                    {
                        "type": "button",
                        "show_name": True,
                        "show_icon": True,
                        "name": "On home",
                        "icon": "mdi:home-import-outline",
                        "icon_height": "32px",
                        "tap_action": {
                            "action": "call-service",
                            "service": "script.scheduled_action_schedule_from_select",
                            "data": {
                                "browser_id": browser_id,
                                "entry_id": entry_id,
                                "action_select_entity": action_select_entity,
                                "trigger_type": "home",
                                "trigger_label": "On home",
                            },
                        },
                    },
                    {
                        "type": "button",
                        "show_name": True,
                        "show_icon": True,
                        "name": "On away",
                        "icon": "mdi:home-export-outline",
                        "icon_height": "32px",
                        "tap_action": {
                            "action": "call-service",
                            "service": "script.scheduled_action_schedule_from_select",
                            "data": {
                                "browser_id": browser_id,
                                "entry_id": entry_id,
                                "action_select_entity": action_select_entity,
                                "trigger_type": "away",
                                "trigger_label": "On away",
                            },
                        },
                    },
                ]
            )

        if popup.get("has_asleep_trigger"):
            state_cards.extend(
                [
                    {
                        "type": "button",
                        "show_name": True,
                        "show_icon": True,
                        "name": "On asleep",
                        "icon": "mdi:sleep",
                        "icon_height": "32px",
                        "tap_action": {
                            "action": "call-service",
                            "service": "script.scheduled_action_schedule_from_select",
                            "data": {
                                "browser_id": browser_id,
                                "entry_id": entry_id,
                                "action_select_entity": action_select_entity,
                                "trigger_type": "asleep",
                                "trigger_label": "On asleep",
                            },
                        },
                    },
                    {
                        "type": "button",
                        "show_name": True,
                        "show_icon": True,
                        "name": "On awake",
                        "icon": "mdi:sleep-off",
                        "icon_height": "32px",
                        "tap_action": {
                            "action": "call-service",
                            "service": "script.scheduled_action_schedule_from_select",
                            "data": {
                                "browser_id": browser_id,
                                "entry_id": entry_id,
                                "action_select_entity": action_select_entity,
                                "trigger_type": "awake",
                                "trigger_label": "On awake",
                            },
                        },
                    },
                ]
            )

        if state_cards:
            cards.append(
                {
                    "type": "grid",
                    "square": False,
                    "columns": 2,
                    "cards": state_cards,
                }
            )

        custom_event_cards = []
        for idx in range(1, MAX_CUSTOM_EVENTS + 1):
            label = popup.get(f"custom_event_{idx}_label")
            event_name = popup.get(f"custom_event_{idx}_name")
            icon = popup.get(f"custom_event_{idx}_icon") or "mdi:alarm"
            if label and event_name:
                custom_event_cards.append(
                    {
                        "type": "button",
                        "show_name": True,
                        "show_icon": True,
                        "name": label,
                        "icon": icon,
                        "icon_height": "32px",
                        "tap_action": {
                            "action": "call-service",
                            "service": "script.scheduled_action_schedule_from_select",
                            "data": {
                                "browser_id": browser_id,
                                "entry_id": entry_id,
                                "action_select_entity": action_select_entity,
                                "trigger_type": "event",
                                "trigger_event_name": event_name,
                                "trigger_label": label,
                            },
                        },
                    }
                )

        if custom_event_cards:
            cards.append(
                {
                    "type": "grid",
                    "square": False,
                    "columns": 1 if len(custom_event_cards) == 1 else 2,
                    "cards": custom_event_cards,
                }
            )

        queue_entity_id = _queue_sensor_entity_id(hass, coordinator)
        clear_queue_entity_id = _clear_queue_entity_id(hass, coordinator)
        if coordinator.queue_count > 0:
            cards.append(
                {
                    "type": "markdown",
                    "text_only": True,
                    "content": (
                        f"<ha-alert title=\"Current queue\">"
                        f"{{{{ (state_attr('{queue_entity_id}', 'queue_text') or 'Empty') | replace('\\n', '<br>') }}}}"
                        f"</ha-alert>"
                    ),
                }
            )
            cards.append(
                {
                    "type": "tile",
                    "entity": clear_queue_entity_id,
                    "name": {"type": "entity"},
                    "color": "red",
                    "show_entity_picture": False,
                    "hide_state": True,
                    "vertical": False,
                    "tap_action": {"action": "none"},
                    "icon_tap_action": {
                        "action": "perform-action",
                        "perform_action": "button.press",
                        "target": {"entity_id": clear_queue_entity_id},
                    },
                    "features_position": "bottom",
                }
            )

        _LOGGER.debug(
            "open_popup: calling browser_mod.popup browser_id=%r title=%r card_count=%s",
            browser_id,
            popup.get("scheduler_name") or "Scheduled action",
            len(cards),
        )
        await hass.services.async_call(
            "browser_mod",
            "popup",
            {
                "browser_id": browser_id,
                "title": popup.get("device_name") or popup.get("scheduler_name") or "Scheduled action",
                "dismissable": False,
                "timeout": 120000,
                "timeout_hide_progress": True,
                "icon": "mdi:window-close",
                "icon_close": True,
                "dismiss_icon": "",
                "adaptive": True,
                "content": {
                    "type": "vertical-stack",
                    "cards": cards,
                },
            },
            blocking=True,
        )
        _LOGGER.debug("open_popup: browser_mod.popup call completed for entry_id=%s", entry_id)

    async def _schedule(call: ServiceCall) -> None:
        entry_id = str(call.data["entry_id"])
        coordinator = _coordinator_for_entry(hass, entry_id)
        if coordinator is None:
            return

        trigger = dict(call.data.get("trigger", {}))
        trigger_type = str(trigger.get("type", TRIGGER_DELAY))
        due_at = None
        if trigger_type == TRIGGER_DELAY:
            hours = float(trigger.get("hours", 0))
            due_at = (dt_util.now() + timedelta(hours=hours)).isoformat()
        elif trigger_type == TRIGGER_DATETIME:
            due_at = trigger.get("at")

        if trigger_type not in [TRIGGER_DELAY, TRIGGER_DATETIME, TRIGGER_EVENT, TRIGGER_HOME, TRIGGER_AWAY, TRIGGER_ASLEEP, TRIGGER_AWAKE]:
            return

        action_id = str(call.data.get("action_id", "")).strip()
        selected_action = None
        if action_id:
            selected_action = next((item for item in coordinator.scheduler.actions if item.id == action_id), None)
            if selected_action is None:
                return

        target_entity_id = str(call.data.get("target_entity_id", "")).strip()
        action = str(call.data.get("action", "")).strip()

        if selected_action is not None:
            target_entity_id = selected_action.target_entity_id
            action = selected_action.action

        if not target_entity_id or not action:
            return

        item = QueueItem(
            item_id=uuid.uuid4().hex,
            action_id=selected_action.id if selected_action is not None else None,
            target_entity_id=target_entity_id,
            action=action,
            trigger_type=trigger_type,
            trigger_data=trigger,
            created_at=dt_util.now().isoformat(),
            due_at=due_at,
            label=strip_trigger_suffix(call.data.get("label") or (selected_action.label if selected_action is not None else None)),
            trigger_label=normalize_trigger_label(call.data.get("trigger_label")),
        )
        coordinator.store.items.append(item)
        await coordinator.store.async_save()
        await coordinator.async_request_refresh()

    async def _cancel(call: ServiceCall) -> None:
        entry_id = str(call.data["entry_id"])
        item_id = str(call.data["item_id"])
        coordinator = _coordinator_for_entry(hass, entry_id)
        if coordinator is None:
            return
        coordinator.store.items = [item for item in coordinator.store.items if item.item_id != item_id]
        await coordinator.store.async_save()
        await coordinator.async_request_refresh()

    async def _cancel_all(call: ServiceCall) -> None:
        entry_id = str(call.data["entry_id"])
        coordinator = _coordinator_for_entry(hass, entry_id)
        if coordinator is None:
            return
        coordinator.store.items.clear()
        await coordinator.store.async_save()
        await coordinator.async_request_refresh()

    async def _fire_event(call: ServiceCall) -> None:
        hass.bus.async_fire(
            EVENT_TYPE,
            {
                "event_name": str(call.data["event_name"]),
                "entry_id": call.data.get("entry_id"),
            },
        )

    async def _get_popup_context(call: ServiceCall) -> dict:
        entry_id = str(call.data["entry_id"])
        _LOGGER.debug("get_popup_context called: entry_id=%s raw_data=%s", entry_id, dict(call.data))
        coordinator = _coordinator_for_entry(hass, entry_id)
        if coordinator is None:
            _LOGGER.warning("get_popup_context: no coordinator found for entry_id=%s", entry_id)
            return {}
        context = _popup_context_for_coordinator(coordinator)
        _LOGGER.debug(
            "get_popup_context: returning scheduler=%s actions=%s time_presets=%s event_presets=%s",
            context.get("scheduler_name"),
            len(context.get("actions", [])),
            len(context.get("time_presets", [])),
            len(context.get("event_presets", [])),
        )
        return context

    hass.services.async_register(DOMAIN, SERVICE_OPEN_POPUP, _open_popup)
    hass.services.async_register(DOMAIN, SERVICE_SCHEDULE, _schedule)
    hass.services.async_register(DOMAIN, SERVICE_CANCEL, _cancel)
    hass.services.async_register(DOMAIN, SERVICE_CANCEL_ALL, _cancel_all)
    hass.services.async_register(DOMAIN, SERVICE_FIRE_EVENT, _fire_event)
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_POPUP_CONTEXT,
        _get_popup_context,
        supports_response="only",
    )
