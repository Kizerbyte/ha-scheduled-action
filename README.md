# Scheduled Action

<p align="center">
  <img src="assets/icon.jpg" alt="Scheduled Action icon" width="180">
</p>

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://hacs.xyz/)
[![GitHub Release](https://img.shields.io/github/v/release/Kizerbyte/ha-scheduled-action?style=for-the-badge)](https://github.com/Kizerbyte/ha-scheduled-action/releases)

Home Assistant custom component to schedule predefined actions using delays, state-based triggers, and custom events.

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

1. Open **HACS**.
2. Go to **⋮ → Custom repositories**.
3. Add repository:
   - **Repository**: `https://github.com/Kizerbyte/ha-scheduled-action`
   - **Category**: `Integration`
4. Search for **Scheduled Action**.
5. Install it.
6. Restart Home Assistant.

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
- one or more predefined actions
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

Why this pattern:
- Browser Mod resolves `browser_id: THIS` correctly in the `fire-dom-event` path.
- A plain Lovelace `perform-action` call is **not** the recommended public entry point for opening this popup.
- The integration handles popup content generation itself, so the dashboard YAML stays small.

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

### Example: schedule an action

```yaml
action: scheduled_action.schedule
data:
  entry_id: YOUR_ENTRY_ID
  action_id: YOUR_ACTION_ID
  trigger:
    type: delay
    hours: 0.5
```

### Example: cancel one queued item

```yaml
action: scheduled_action.cancel
data:
  entry_id: YOUR_ENTRY_ID
  item_id: YOUR_ITEM_ID
```

### Example: clear all queued items

```yaml
action: scheduled_action.cancel_all
data:
  entry_id: YOUR_ENTRY_ID
```

## Example use cases

- Turn something off in 30 minutes
- Queue an IR button press for later
- Trigger an action when arriving home
- Trigger an action when going to sleep
- Trigger an action from a custom event such as `next_alarm`

## Troubleshooting

- If the popup does not open, confirm Browser Mod is installed and working.
- If you use the popup launch from Lovelace, prefer the documented `fire-dom-event` pattern with `browser_id: THIS`.
- If scheduled items do not run, check the Home Assistant logs for `scheduled_action`.
- If the integration is installed manually, confirm the folder path is exactly `custom_components/scheduled_action/`.

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
- `assets/ATTRIBUTION.md`\n
## License

See `LICENSE`.
