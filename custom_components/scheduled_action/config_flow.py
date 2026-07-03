from __future__ import annotations

import uuid

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import selector

from .const import (
    CONF_ACTIONS,
    CONF_CUSTOM_EVENTS,
    CONF_HOME_STATE_ENTITY,
    CONF_NAME,
    CONF_SLEEP_STATE_ENTITY,
    CONF_TIME_PRESETS_HOURS,
    DEFAULT_TIME_PRESETS_HOURS,
    DOMAIN,
    MAX_CUSTOM_EVENTS,
)
from .text_utils import normalize_label, strip_trigger_suffix

ACTION_TYPE_OPTIONS = {
    "press": "press",
    "turn_on": "turn_on",
    "turn_off": "turn_off",
    "toggle": "toggle",
}
ACTION_TYPE_ORDER = list(ACTION_TYPE_OPTIONS)


def _boolean_entity_selector():
    return selector(
        {
            "entity": {
                "multiple": False,
                "filter": [
                    {"domain": "input_boolean"},
                    {"domain": "binary_sensor"},
                    {"domain": "switch"},
                ]
            }
        }
    )


def _action_target_entity_selector():
    return selector(
        {
            "entity": {
                "multiple": False,
                "filter": [
                    {"domain": "button"},
                    {"domain": "switch"},
                    {"domain": "input_boolean"},
                    {"domain": "light"},
                    {"domain": "fan"},
                    {"domain": "script"},
                    {"domain": "automation"},
                    {"domain": "media_player"},
                    {"domain": "remote"},
                    {"domain": "scene"},
                ],
            }
        }
    )


class ScheduledActionConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        if user_input is None:
            schema = vol.Schema({vol.Required(CONF_NAME): str})
            return self.async_show_form(step_id="user", data_schema=schema)

        self._user_input = dict(user_input)
        self._user_input[CONF_ACTIONS] = []
        return await self.async_step_details()

    async def async_step_details(self, user_input=None) -> FlowResult:
        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Optional("preset_1", default=DEFAULT_TIME_PRESETS_HOURS[0]): vol.Coerce(float),
                    vol.Optional("preset_2", default=DEFAULT_TIME_PRESETS_HOURS[1]): vol.Coerce(float),
                    vol.Optional("preset_3", default=DEFAULT_TIME_PRESETS_HOURS[2]): vol.Coerce(float),
                    vol.Optional("preset_4", default=DEFAULT_TIME_PRESETS_HOURS[3]): vol.Coerce(float),
                    vol.Optional(CONF_HOME_STATE_ENTITY): _boolean_entity_selector(),
                    vol.Optional(CONF_SLEEP_STATE_ENTITY): _boolean_entity_selector(),
                    vol.Optional("custom_event_1_label", default=""): str,
                    vol.Optional("custom_event_1_name", default=""): str,
                    vol.Optional("custom_event_2_label", default=""): str,
                    vol.Optional("custom_event_2_name", default=""): str,
                }
            )
            return self.async_show_form(step_id="details", data_schema=schema)

        custom_events = []
        for idx in (1, 2):
            label = str(user_input.get(f"custom_event_{idx}_label", "")).strip()
            event_name = str(user_input.get(f"custom_event_{idx}_name", "")).strip()
            if label and event_name:
                custom_events.append({"label": label, "event_name": event_name})

        data = {
            **self._user_input,
            CONF_ACTIONS: [],
            CONF_TIME_PRESETS_HOURS: [
                float(user_input["preset_1"]),
                float(user_input["preset_2"]),
                float(user_input["preset_3"]),
                float(user_input["preset_4"]),
            ],
            CONF_HOME_STATE_ENTITY: user_input.get(CONF_HOME_STATE_ENTITY) or None,
            CONF_SLEEP_STATE_ENTITY: user_input.get(CONF_SLEEP_STATE_ENTITY) or None,
            CONF_CUSTOM_EVENTS: custom_events[:MAX_CUSTOM_EVENTS],
        }
        title = str(self._user_input[CONF_NAME]).strip()
        return self.async_create_entry(title=title, data=data)

    @staticmethod
    def async_get_options_flow(config_entry):
        return ScheduledActionOptionsFlow(config_entry)


class ScheduledActionOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self._config_entry = config_entry
        self._selected_action_id: str | None = None
        self._action_mode: str = "add"

    def _current(self) -> dict:
        return {**self._config_entry.data, **self._config_entry.options}

    def _current_actions(self) -> list[dict]:
        actions = []
        for item in self._current().get(CONF_ACTIONS, []):
            if not isinstance(item, dict):
                continue
            action_id = str(item.get("id", "")).strip()
            label = strip_trigger_suffix(str(item.get("label", "")).strip())
            target_entity_id = str(item.get("target_entity_id", "")).strip()
            action = str(item.get("action", "")).strip()
            if action_id and label and target_entity_id and action:
                actions.append(
                    {
                        "id": action_id,
                        "label": label,
                        "target_entity_id": target_entity_id,
                        "action": action,
                    }
                )
        return sorted(actions, key=lambda item: item["label"].lower())

    def _options_with(self, **updates) -> dict:
        return {
            **self._config_entry.options,
            **updates,
        }

    def _action_form_schema(self, current_action: dict | None):
        return vol.Schema(
            {
                vol.Required("label", default=(current_action["label"] if current_action else "")): str,
                vol.Required(
                    "target_entity_id",
                    default=(current_action["target_entity_id"] if current_action else ""),
                ): _action_target_entity_selector(),
                vol.Required(
                    "action_type",
                    default=(current_action["action"] if current_action else ACTION_TYPE_ORDER[0]),
                ): vol.In(ACTION_TYPE_OPTIONS),
            }
        )

    async def async_step_init(self, user_input=None):
        actions = self._current_actions()
        if actions:
            choices = {
                "add_action": "Add action",
                "edit_action": "Edit action",
                "edit_triggers": "Edit triggers",
                "remove_action": "Remove action",
            }
        else:
            choices = {
                "add_action": "Add action",
                "edit_triggers": "Edit triggers",
            }

        if user_input is None:
            schema = vol.Schema({vol.Required("action"): vol.In(choices)})
            return self.async_show_form(step_id="init", data_schema=schema)

        action = user_input["action"]
        if action == "edit_triggers":
            return await self.async_step_edit_triggers()
        if action == "add_action":
            self._selected_action_id = None
            self._action_mode = "add"
            return await self.async_step_add_action()
        if action == "edit_action":
            self._action_mode = "edit"
            return await self.async_step_select_action_to_edit()
        if action == "remove_action":
            return await self.async_step_select_action_to_delete()
        return self.async_abort(reason="unknown_action")

    async def async_step_manage_actions(self, user_input=None):
        actions = self._current_actions()
        if user_input is None:
            choices = ["add_action"]
            if actions:
                choices.extend(["edit_action", "delete_action"])
            schema = vol.Schema({vol.Required("manage_action"): vol.In(choices)})
            return self.async_show_form(step_id="manage_actions", data_schema=schema)

        choice = str(user_input["manage_action"])
        if choice == "add_action":
            self._selected_action_id = None
            self._action_mode = "add"
            return await self.async_step_add_action()
        if choice == "edit_action":
            self._action_mode = "edit"
            return await self.async_step_select_action_to_edit()
        if choice == "delete_action":
            return await self.async_step_select_action_to_delete()
        return self.async_abort(reason="unknown_action")

    async def async_step_select_action_to_edit(self, user_input=None):
        actions = self._current_actions()
        if not actions:
            return self.async_abort(reason="no_actions")
        if user_input is None:
            choices = {item["id"]: item["label"] for item in actions}
            schema = vol.Schema({vol.Required("action_id"): vol.In(choices)})
            return self.async_show_form(step_id="select_action_to_edit", data_schema=schema)

        self._selected_action_id = str(user_input["action_id"])
        self._action_mode = "edit"
        return await self.async_step_edit_action()

    async def async_step_select_action_to_delete(self, user_input=None):
        actions = self._current_actions()
        if not actions:
            return self.async_abort(reason="no_actions")
        if user_input is None:
            choices = {item["id"]: item["label"] for item in actions}
            schema = vol.Schema({vol.Required("action_id"): vol.In(choices)})
            return self.async_show_form(step_id="select_action_to_delete", data_schema=schema)

        self._selected_action_id = str(user_input["action_id"])
        return await self.async_step_delete_action()

    async def async_step_add_action(self, user_input=None):
        self._selected_action_id = None
        self._action_mode = "add"
        return await self.async_step_action_form(user_input)

    async def async_step_edit_action(self, user_input=None):
        self._action_mode = "edit"
        return await self.async_step_action_form(user_input)

    async def async_step_action_form(self, user_input=None):
        actions = self._current_actions()
        current_action = next((item for item in actions if item["id"] == self._selected_action_id), None)
        is_edit = current_action is not None and self._action_mode == "edit"
        step_id = "edit_action" if is_edit else "add_action"
        errors: dict[str, str] = {}

        if user_input is None:
            return self.async_show_form(step_id=step_id, data_schema=self._action_form_schema(current_action), errors=errors)

        label = normalize_label(user_input["label"])
        target_entity_id = str(user_input["target_entity_id"]).strip()
        action_type = str(user_input["action_type"]).strip()

        if not label:
            errors["label"] = "required"
        if not target_entity_id:
            errors["target_entity_id"] = "required"
        elif "." not in target_entity_id:
            errors["target_entity_id"] = "invalid_entity_id"
        if action_type not in ACTION_TYPE_ORDER:
            errors["action_type"] = "invalid_action_type"

        duplicate = next(
            (
                item
                for item in actions
                if item["label"] == label and item["id"] != (current_action["id"] if current_action else None)
            ),
            None,
        )
        if duplicate is not None:
            errors["label"] = "duplicate_label"

        if errors:
            if is_edit:
                schema = vol.Schema(
                    {
                        vol.Required("mode", default=str(user_input.get("mode", "save"))): vol.In({"save": "Save changes", "delete": "Delete action"}),
                        vol.Required("label", default=label): str,
                        vol.Required("target_entity_id", default=target_entity_id): _action_target_entity_selector(),
                        vol.Required("action_type", default=action_type): vol.In(ACTION_TYPE_OPTIONS),
                    }
                )
            else:
                schema = self._action_form_schema(
                    {
                        "label": label,
                        "target_entity_id": target_entity_id,
                        "action": action_type if action_type in ACTION_TYPE_ORDER else ACTION_TYPE_ORDER[0],
                    }
                )
            return self.async_show_form(
                step_id=step_id,
                data_schema=schema,
                errors=errors,
            )

        updated_action = {
            "id": current_action["id"] if current_action else f"act_{uuid.uuid4().hex[:8]}",
            "label": label,
            "target_entity_id": target_entity_id,
            "action": action_type,
        }

        updated_actions = []
        replaced = False
        for item in actions:
            if item["id"] == updated_action["id"]:
                updated_actions.append(updated_action)
                replaced = True
            else:
                updated_actions.append(item)
        if not replaced:
            updated_actions.append(updated_action)

        return self.async_create_entry(
            title="",
            data=self._options_with(**{CONF_ACTIONS: updated_actions}),
        )

    async def async_step_delete_action(self, user_input=None):
        actions = self._current_actions()
        if not actions:
            return self.async_abort(reason="no_actions")

        current_action = next((item for item in actions if item["id"] == self._selected_action_id), None)
        if current_action is None:
            return await self.async_step_select_action_to_delete()

        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required("confirm", default=False): bool,
                }
            )
            return self.async_show_form(
                step_id="delete_action",
                data_schema=schema,
                description_placeholders={"label": current_action["label"]},
            )

        if not user_input.get("confirm"):
            return self.async_show_form(
                step_id="delete_action",
                data_schema=vol.Schema({vol.Required("confirm", default=False): bool}),
                errors={"confirm": "required"},
                description_placeholders={"label": current_action["label"]},
            )

        updated_actions = [item for item in actions if item["id"] != current_action["id"]]
        return self.async_create_entry(
            title="",
            data=self._options_with(**{CONF_ACTIONS: updated_actions}),
        )

    async def async_step_edit_triggers(self, user_input=None):
        current = self._current()
        current_events = list(current.get(CONF_CUSTOM_EVENTS, []))
        defaults = current_events + [{"label": "", "event_name": ""}] * (2 - len(current_events))
        presets = list(current.get(CONF_TIME_PRESETS_HOURS, DEFAULT_TIME_PRESETS_HOURS))
        while len(presets) < 4:
            presets.append(DEFAULT_TIME_PRESETS_HOURS[len(presets)])
        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Optional("preset_1", default=float(presets[0])): vol.Coerce(float),
                    vol.Optional("preset_2", default=float(presets[1])): vol.Coerce(float),
                    vol.Optional("preset_3", default=float(presets[2])): vol.Coerce(float),
                    vol.Optional("preset_4", default=float(presets[3])): vol.Coerce(float),
                    vol.Optional(CONF_HOME_STATE_ENTITY, default=current.get(CONF_HOME_STATE_ENTITY) or None): _boolean_entity_selector(),
                    vol.Optional(CONF_SLEEP_STATE_ENTITY, default=current.get(CONF_SLEEP_STATE_ENTITY) or None): _boolean_entity_selector(),
                    vol.Optional("custom_event_1_label", default=defaults[0]["label"]): str,
                    vol.Optional("custom_event_1_name", default=defaults[0]["event_name"]): str,
                    vol.Optional("custom_event_2_label", default=defaults[1]["label"]): str,
                    vol.Optional("custom_event_2_name", default=defaults[1]["event_name"]): str,
                }
            )
            return self.async_show_form(step_id="edit_triggers", data_schema=schema)

        custom_events = []
        for idx in (1, 2):
            label = str(user_input.get(f"custom_event_{idx}_label", "")).strip()
            event_name = str(user_input.get(f"custom_event_{idx}_name", "")).strip()
            if label and event_name:
                custom_events.append({"label": label, "event_name": event_name})

        return self.async_create_entry(
            title="",
            data=self._options_with(
                **{
                    CONF_TIME_PRESETS_HOURS: [
                        float(user_input["preset_1"]),
                        float(user_input["preset_2"]),
                        float(user_input["preset_3"]),
                        float(user_input["preset_4"]),
                    ],
                    CONF_HOME_STATE_ENTITY: user_input.get(CONF_HOME_STATE_ENTITY) or None,
                    CONF_SLEEP_STATE_ENTITY: user_input.get(CONF_SLEEP_STATE_ENTITY) or None,
                    CONF_CUSTOM_EVENTS: custom_events[:MAX_CUSTOM_EVENTS],
                }
            ),
        )


