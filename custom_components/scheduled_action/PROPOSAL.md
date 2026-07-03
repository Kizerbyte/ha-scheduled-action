# Scheduled Action integration proposal

## Summary

`scheduled_action` is now best understood as a small Home Assistant integration that owns:
- one scheduler queue per config entry
- a managed list of predefined actions per config entry
- per-entry time presets and trigger presets
- a lightweight backend bridge for dashboards/popups

The current direction is:
- keep the backend integration generic and reusable
- keep popup UI optional and external
- use one generic popup launcher/script rather than one popup definition per scheduler
- let the integration provide the persistent config and runtime state
- let the UI layer provide browser-local interaction details such as `browser_id: THIS`

This proposal reflects the current architecture direction rather than the earlier target-policy concept.

---

## Core intent

The integration provides a reusable way to schedule a predefined action for later execution.

Examples:
- turn off a heater in 1 hour
- press an IR button at the next alarm event
- toggle a switch when arriving home
- run an action when going to sleep

This is not meant to be a full planner or calendar system.
It is a compact delayed-action engine for Home Assistant automations and dashboards.

---

## Current design direction

### 1. One config entry = one scheduler instance

Each integration entry represents one scheduler.

Examples:
- `Airco`
- `Bedroom heating`
- `Office fan`
- `Media sleep timer`

Each scheduler instance owns:
- its own queued items
- its own predefined actions
- its own time presets
- its own linked trigger entities
- its own custom events
- its own helper entities exposed by the integration

This keeps unrelated devices and workflows separated cleanly.

### 2. Managed predefined actions per scheduler

The scheduler no longer revolves around target restriction policies such as `allowed_targets` or `target_mode`.

Instead, each scheduler owns an explicit list of actions.

Each action contains:
- `id`
- `label`
- `target_entity_id`
- `action`

Supported action types for now:
- `turn_on`
- `turn_off`
- `toggle`
- `press`

This is simpler than a free-form target picker model and fits the intended popup UX better.
The popup can present a small, human-friendly list of actions rather than asking the user to construct a service call each time.

### 3. Per-entry trigger presets

Each scheduler entry also owns its own trigger options.

Currently the intended preset model is:
- four configurable time presets, stored in hours
- optional linked `home_state_entity`
- optional linked `sleep_state_entity`
- up to two custom named events

This means one scheduler can offer:
- `In 30 mins`
- `In 1 hour`
- `When home`
- `When asleep`
- `Next alarm`

while another scheduler can expose a completely different combination.

### 4. Popup UI remains optional

The integration should not depend on Browser Mod or any specific dashboard stack.

Instead, it should expose enough context for an external UI layer to build a popup or quick-action interface.

That is the preferred boundary:
- integration = data, queue, services, entities, config flow
- popup script/dashboard = interaction layer

---

## Why this direction

This split gives the cleanest separation of responsibilities.

### The integration owns persistent scheduler state

The config entry stores:
- scheduler name
- predefined actions
- time presets
- linked state entities
- custom events

The integration runtime owns:
- the queue
- trigger handling
- execution
- summary entities
- popup context service data

### The UI layer owns browser-local behavior

The popup layer should handle:
- opening the popup on the current device
- passing `browser_id: THIS`
- rendering action and trigger choices
- calling scheduling services after the user clicks something

This is important because `browser_id` is not scheduler configuration.
It is interaction context.
That means it belongs in the dashboard/script layer, not inside the integration entry.

---

## UX model

The intended user flow is:

1. Create a scheduler from **Settings -> Devices & Services**
2. Configure its actions and trigger presets through config/options flows
3. Expose the integration's popup button on a dashboard
4. Tap that button from a browser/device
5. Open a generic popup on that same browser using `browser_id: THIS`
6. Show the scheduler's configured actions and trigger choices
7. Queue the chosen action through `scheduled_action.schedule`

This keeps the scheduler reusable while still giving a smooth popup interaction path.

---

## Preferred popup architecture

### Recommendation: one generic popup launcher/script

This is the preferred architecture.

Use:
- one per-entry integration button as the launch anchor
- one generic Browser Mod popup script/automation pattern
- one integration service call to fetch popup context

The integration button provides the scheduler context.
The dashboard/browser invocation provides the browser context.
The generic script combines the two.

### Why one generic popup is preferred

Benefits:
- one UI implementation to maintain
- one place to solve Browser Mod quirks
- one place to handle `browser_id: THIS`
- avoids duplicating popup YAML per scheduler entry
- keeps scheduler config and popup logic decoupled
- makes iteration easier while the popup flow is still evolving

### Why not one popup per scheduler entry

Per-entry popup definitions would:
- duplicate layout logic
- drift out of sync with integration behavior
- be harder to update when popup behavior changes
- blur the line between scheduler config and UI implementation

That approach might still be useful later if a real limitation appears, but it should not be the default design.

---

## Popup interaction model

The intended popup interaction flow is:

1. User presses `button.<scheduler>_open_popup`
2. A generic popup launcher script is called
3. The script passes:
   - `entry_id`
   - `browser_id: THIS`
4. The script calls `scheduled_action.get_popup_context`
5. The popup renders:
   - scheduler name
   - available actions
   - time preset buttons
   - event/state trigger buttons
6. User chooses an action and a trigger
7. The UI calls `scheduled_action.schedule`

This is the intended high-level contract.

---

## Browser Mod / browser targeting note

A known concern in the earlier design discussion was browser targeting.

The current recommendation is:
- do not store browser ids in integration config
- do not make scheduler entries responsible for browser selection
- let the popup invocation use Browser Mod's local targeting concept, such as `browser_id: THIS`

That keeps browser targeting tied to the current interaction context, which is the right place for it.

---

## Popup context bridge

The integration should expose a small backend bridge for popup consumers.

### Entities exposed per scheduler

Per scheduler entry, the integration can expose entities such as:
- popup/open button
- clear queue button
- queue count sensor
- next action sensor
- has-pending binary sensor
- optional action select helper

### Popup context service

The integration should expose a response-capable service such as:
- `scheduled_action.get_popup_context`

The returned structure should include enough information for a generic popup to render itself, for example:
- `entry_id`
- `scheduler_name`
- `actions`
- `time_presets`
- `event_presets`
- booleans like:
  - `has_home_state`
  - `has_sleep_state`
  - `has_custom_events`

This gives the popup layer a stable contract without making the integration depend on any popup implementation.

---

## Action selection approach

There are two ways the popup layer can choose an action.

### Option A — use an integration `select` entity

A `select.<scheduler>_action` entity can expose the configured action labels.

Pros:
- simple Lovelace wiring
- easy to inspect manually
- can be convenient as a UI helper

Cons:
- it is shared state
- it may not be ideal if multiple users/devices interact at once
- labels may not be unique unless enforced

### Option B — select action directly inside the popup flow

Preferred direction if practical:
- popup renders actions from `get_popup_context`
- selected item resolves directly to `action_id`
- scheduling happens immediately using that `action_id`

This avoids relying on persistent shared UI state for a transient interaction.

### Recommendation

Keep the `select` entity optional/helpful, but prefer an `action_id`-driven popup flow where possible.

---

## Config flow direction

The config flow should stay conservative and Home Assistant-safe.

Initial setup should focus on:
- scheduler name
- four time presets
- optional home state entity
- optional sleep state entity
- up to two custom events

The integration entry is mainly about defining the scheduler and its trigger context.
Predefined actions can then be maintained in the options flow.

---

## Options flow direction

The options flow should act as the functional management surface.

It should support actions such as:
- manage predefined actions
- edit trigger links and custom events
- edit time presets

This follows the current simplified model better than the older ideas around target policy editing.

---

## Service/API direction

The core service remains:
- `scheduled_action.schedule`

Expected use:
- schedule by `entry_id`
- preferably schedule a predefined action by `action_id`
- include a trigger payload such as delay, datetime, event, home, away, asleep, or awake

Related services:
- `scheduled_action.cancel`
- `scheduled_action.cancel_all`
- `scheduled_action.fire_event`
- `scheduled_action.get_popup_context`

This gives both automations and popup scripts a clear interface.

---

## Entity model direction

Per scheduler instance, expose a small useful set of entities.

Recommended current set:
- popup/open button
- clear queue button
- queue count sensor
- next action sensor
- has-pending binary sensor
- optional action select helper

The queue itself should primarily live in storage and sensor attributes rather than as a large set of slot entities.

---

## Storage and execution model

Each scheduler stores its own queue persistently.

Each queued item should contain roughly:
- item id
- action id if using predefined actions
- target entity id
- action type
- trigger type
- trigger payload
- created timestamp
- due timestamp when relevant
- optional display label
- status

Execution should remain intentionally small in scope for now:
- `turn_on` -> `homeassistant.turn_on`
- `turn_off` -> `homeassistant.turn_off`
- `toggle` -> `homeassistant.toggle`
- `press` -> `button.press`

The backend is already considered good enough for now; the main missing piece was interaction flow.

---

## Non-goals for now

To keep scope sane, this direction does not try to solve:
- full recurring schedules
- calendar sync
- complex condition trees
- fully generated dashboard packages per scheduler
- hard dependency on Browser Mod\n- embedding browser-specific behavior inside integration config

---

## Practical recommendation

The clean design boundary is:
- **integration entry** = persistent scheduler config
- **integration entities/services** = backend interface and state
- **open popup button** = entry-specific launch anchor
- **generic Browser Mod script** = reusable interaction engine
- **`browser_id: THIS`** = runtime browser context from the current device

In one sentence:

> Keep scheduler data in the integration, keep browser targeting in the UI layer, and use one generic popup script that renders from integration-provided context.

---

## Next implementation-oriented step

After this proposal, the next practical step should be to document or build:
- one generic popup launcher script
- one example dashboard/button invocation
- one action-selection path that prefers `action_id` over label-only state
\nThat would complete the missing interaction story without bloating the integration itself.
