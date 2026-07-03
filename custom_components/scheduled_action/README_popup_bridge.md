# Scheduled Action popup bridge

This file documents the current popup bridge contract for the `scheduled_action` integration.

---

## Purpose

The integration keeps popup UI optional, but it now exposes an integration-owned popup launcher service.

That means the recommended user-facing flow is:
- Lovelace tap action passes only:
  - `entry_id`
  - `browser_id: THIS`
- the integration resolves the matching scheduler entry
- the integration builds the popup payload
- Browser Mod opens the popup on the current browser/device

This keeps the public YAML small and reusable while leaving scheduler details in the backend.

---

## Recommended architecture

Use this split:

- **integration entry** = persistent scheduler config
- **integration services** = popup opening + popup context + scheduling
- **dashboard YAML** = transparent launch snippet
- **Browser Mod** = popup transport to the current browser/device

Recommended popup model:
- one integration-owned popup service
- many scheduler entries
- one public Lovelace pattern
- `browser_id: THIS` supplied at click time by the dashboard layer

---

## Public services

### `scheduled_action.open_popup`

Open the popup for one scheduler entry on one Browser Mod browser target.

Inputs:
- `entry_id`
- `browser_id`

Canonical Lovelace pattern:

```yaml
tap_action:
  action: fire-dom-event
  browser_mod:
    service: scheduled_action.open_popup
    data:
      entry_id: YOUR_ENTRY_ID
      browser_id: THIS
```

This is the main public launch contract.

Important:
- `browser_id: THIS` is resolved correctly when Browser Mod handles the `fire-dom-event` path
- plain `perform-action` does not resolve `THIS` for this use case

### `scheduled_action.get_popup_context`

Return dynamic popup context for one scheduler entry.

```yaml
action: scheduled_action.get_popup_context
data:
  entry_id: YOUR_ENTRY_ID
response_variable: popup
```

This remains useful for alternate UI flows, debugging, and future convenience cards.

### `scheduled_action.schedule`

Schedule the selected action with a structured trigger payload.

---

## Popup context

The integration exposes entry-specific popup context.

Useful fields include:
- `entry_id`
- `scheduler_name`
- `actions`
- `time_presets`
- `event_presets`
- `has_home_state`
- `has_sleep_state`
- `has_custom_events`

Example response shape:

```yaml
popup:
  entry_id: abc123
  scheduler_name: Airco
  has_home_state: false
  has_sleep_state: false
  has_custom_events: true
  action_select_entity: select.airco_action
  actions:
    - id: act_8f3c2b1a
      label: Airco off
      target_entity_id: button.airco_power_off_ir
      action: press
  time_presets:
    - key: preset_1
      hours: 0.5
      label: In 30 mins
      trigger:
        type: delay
        hours: 0.5
  event_presets:
    - key: next_alarm
      label: Next alarm
      trigger:
        type: event
        event_name: next_alarm
```

Notes:
- current phase-1 implementation may still use the integration-owned action select internally
- that helper is **backend plumbing**, not part of the public Lovelace launch contract

---

## Intended use

The intended popup flow is:

1. user taps a dashboard control for a specific scheduler
2. Lovelace passes:
   - `entry_id`
   - `browser_id: THIS`
   through a Browser Mod `fire-dom-event` action
3. the integration resolves popup context for that entry
4. the integration opens a Browser Mod popup on that browser/device
5. the popup schedules actions through `scheduled_action.schedule`

---

## Browser Mod note

If Browser Mod is used, the recommended targeting model is:

```yaml
browser_id: THIS
```

Why:
- it targets the browser/device where the user initiated the interaction
- it avoids storing browser-specific routing inside scheduler config
- it keeps the integration reusable and UI-agnostic

The integration should not persist or manage browser ids.

---

## Current recommendation

Use `scheduled_action.open_popup` as the canonical public entry point.

Recommended:
- transparent Lovelace YAML
- integration-owned popup logic
- backend-owned scheduler config

Not recommended as the public default:
- requiring extra Lovelace fields like `action_select_entity`
- one-off per-entry popup scripts maintained by the user

---

## Future direction

Later phases can improve internals without changing the public launch snippet:
- reduce or remove reliance on the internal select helper
- move popup scheduling fully to `action_id`-driven flow
- optionally add a thin convenience card/editor

The public launch shape should stay:
- `entry_id`
- `browser_id: THIS`
