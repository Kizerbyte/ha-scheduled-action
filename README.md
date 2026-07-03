# Scheduled Action

Home Assistant custom component for scheduling device actions through delays, state triggers, and custom events, with Browser Mod popup support.

## Install

Copy this repo's `custom_components/scheduled_action` folder into your Home Assistant `custom_components/` directory.

## Features

- delayed actions from presets
- home/away and asleep/awake triggers
- custom event triggers
- queue sensor and next-action sensor
- Browser Mod popup launcher via `scheduled_action.open_popup`

## Notes

See files inside `custom_components/scheduled_action/` for popup examples and service docs:
- `README_popup_bridge.md`
- `EXAMPLE_popup_bridge.yaml`
- `services.yaml`
