# Scheduled Action

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://hacs.xyz/)
[![GitHub Release](https://img.shields.io/github/v/release/Kizerbyte/ha-scheduled-action?style=for-the-badge)](https://github.com/Kizerbyte/ha-scheduled-action/releases)

Home Assistant custom component to schedule actions for entities using delays, state-based triggers, and custom events.

`Scheduled Action` is useful when you want a lightweight scheduler that can:
- queue an action for later
- trigger actions when you get home or leave
- trigger actions when you fall asleep or wake up
- react to custom events
- offer a popup-based scheduling UI through Browser Mod

## Features

- Config flow support
- Multiple configured actions per scheduler
- Delay presets
- Home / away triggers
- Asleep / awake triggers
- Custom event triggers
- Queue sensor
- Next action sensor
- Clear queue button
- Browser Mod popup support through `scheduled_action.open_popup`

## Installation

### HACS (Custom Repository)

1. Open **HACS**
2. Go to **⋮ → Custom repositories**
3. Add repository:
   - **Repository**: `https://github.com/Kizerbyte/ha-scheduled-action`
   - **Category**: `Integration`
4. Search for **Scheduled Action**
5. Install
6. Restart Home Assistant

### Manual

1. Copy `custom_components/scheduled_action` into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration**.
4. Search for **Scheduled Action**.

Expected folder structure:

```text
config/
└── custom_components/
    └── scheduled_action/
        ├── __init__.py
        ├── manifest.json
        ├── ...
```

## Configuration

This integration is configured through the Home Assistant UI.

During setup you can configure:
- scheduler name
- delay presets
- optional home-state entity
- optional sleep-state entity
- optional custom events

After setup, the options flow lets you:
- add actions
- edit actions
- remove actions
- edit triggers

## How it works

A scheduler entry contains:
- one or more actions
- a set of preset delays
- optional state triggers
- optional custom event triggers

When something is scheduled, it is added to the queue.
The integration then exposes queue state through entities and executes the action when its trigger condition is met.

## Entities

Depending on your scheduler configuration, the integration exposes entities such as:

- **Select**: choose the active action
- **Button**: clear queue
- **Binary sensor**: whether items are pending
- **Sensor**: queue count
- **Sensor**: queue
- **Sensor**: next action

## Popup support

This integration can open a Browser Mod popup through the integration-owned service:

- `scheduled_action.open_popup`

Recommended Lovelace pattern:

```yaml
tap_action:
  action: fire-dom-event
  browser_mod:
    service: scheduled_action.open_popup
    data:
      entry_id: YOUR_ENTRY_ID
      browser_id: THIS
```

This keeps dashboard YAML small while the integration builds the popup content itself.

More popup details and examples are included here:
- `custom_components/scheduled_action/README_popup_bridge.md`
- `custom_components/scheduled_action/EXAMPLE_popup_bridge.yaml`

## Services

Main services exposed by the integration:

- `scheduled_action.open_popup`
- `scheduled_action.get_popup_context`
- `scheduled_action.schedule`
- `scheduled_action.cancel`
- `scheduled_action.cancel_all`
- `scheduled_action.fire_event`

See also:
- `custom_components/scheduled_action/services.yaml`

## Example use cases

- Turn something off in 30 minutes
- Queue an IR button press for later
- Trigger an action when arriving home
- Trigger an action when going to sleep
- Trigger an action from a custom event such as `next_alarm`

## Notes

- Browser Mod is optional, but recommended if you want the popup flow.
- The popup flow is designed so the backend owns the popup context and scheduler logic.
- The recommended Browser Mod target is `browser_id: THIS`.

## Repository contents

Main integration code lives in:

- `custom_components/scheduled_action/`

Supporting docs included in the repo:

- `custom_components/scheduled_action/README_popup_bridge.md`
- `custom_components/scheduled_action/EXAMPLE_popup_bridge.yaml`

## License

See `LICENSE`.
