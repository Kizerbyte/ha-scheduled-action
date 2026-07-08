DOMAIN = "scheduled_action"

PLATFORMS = ["sensor", "binary_sensor", "button", "select"]

CONF_NAME = "name"
CONF_ACTIONS = "actions"
CONF_TIME_PRESETS_HOURS = "time_presets_hours"
CONF_HOME_STATE_ENTITY = "home_state_entity"
CONF_SLEEP_STATE_ENTITY = "sleep_state_entity"
CONF_CUSTOM_EVENTS = "custom_events"
CONF_ICON = "icon"

ACTION_TYPES = ["turn_on", "turn_off", "toggle", "press"]
DEFAULT_TIME_PRESETS_HOURS = [0.5, 1, 2, 5]
MAX_CUSTOM_EVENTS = 2
EVENT_TYPE = "scheduled_action_event"

TRIGGER_DELAY = "delay"
TRIGGER_DATETIME = "datetime"
TRIGGER_EVENT = "event"
TRIGGER_HOME = "home"
TRIGGER_AWAY = "away"
TRIGGER_ASLEEP = "asleep"
TRIGGER_AWAKE = "awake"

SERVICE_OPEN_POPUP = "open_popup"
SERVICE_SCHEDULE = "schedule"
SERVICE_SCHEDULE_FROM_SELECT = "schedule_from_select"
SERVICE_CANCEL = "cancel"
SERVICE_CANCEL_ALL = "cancel_all"
SERVICE_FIRE_EVENT = "fire_event"
SERVICE_GET_POPUP_CONTEXT = "get_popup_context"
