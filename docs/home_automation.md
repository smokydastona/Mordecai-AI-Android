# Home Automation Integration

Mordecai now supports a policy-gated home automation provider that can talk to:

- Home Assistant through its REST API
- Philips Hue directly through the local CLIP v2 bridge API

The goal of this slice is intentionally narrow and explicit:

- list allowlisted light entities and scenes
- toggle allowlisted lights
- activate allowlisted scenes

Everything remains behind the existing outbound proxy and policy model. There is no hidden auto-discovery, no silent fallback to cloud routes, and no wildcard control of every device on the network.

## Safety and policy model

- Home automation is disabled unless `MORDECAI_ENABLE_HOME_AUTOMATION=true`.
- Backends are selected through `MORDECAI_HOME_AUTOMATION_MODE` with `home-assistant`, `philips-hue`, or `both`.
- Home Assistant hosts and Hue bridge hosts must be explicitly allowlisted through the dedicated `*_ALLOWED_HOSTS` settings.
- Device control is restricted to explicit allowlists for entity IDs, light IDs, and scene IDs.
- `home.toggle_light` and `home.activate_scene` are high-risk tools with `confirmation_policy="always"` and `safe_mode_behavior="deny"` in the runtime manifest.
- If `MORDECAI_HOME_AUTOMATION_REQUIRE_CONFIRMATION=false`, state-changing home-automation tools fail closed instead of silently running without confirmation metadata.

## Configuration

### Shared settings

```text
MORDECAI_ENABLE_HOME_AUTOMATION=true
MORDECAI_HOME_AUTOMATION_MODE=both
MORDECAI_HOME_AUTOMATION_REQUIRE_CONFIRMATION=true
MORDECAI_HOME_AUTOMATION_TIMEOUT_SECONDS=10.0
```

### Home Assistant

```text
MORDECAI_HOME_ASSISTANT_BASE_URL=https://ha.internal
MORDECAI_HOME_ASSISTANT_ACCESS_TOKEN=your-home-assistant-token
MORDECAI_HOME_ASSISTANT_ALLOWED_HOSTS=["ha.internal"]
MORDECAI_HOME_ASSISTANT_ALLOWED_ENTITY_IDS=["light.kitchen","light.desk"]
MORDECAI_HOME_ASSISTANT_ALLOWED_SCENE_IDS=["scene.relax","scene.movie"]
```

Use a long-lived Home Assistant access token and only allowlist the exact light and scene entity IDs that Mordecai is meant to touch.

### Philips Hue

```text
MORDECAI_PHILIPS_HUE_BRIDGE_URL=https://192.168.1.20
MORDECAI_PHILIPS_HUE_APPLICATION_KEY=your-hue-application-key
MORDECAI_PHILIPS_HUE_ALLOWED_HOSTS=["192.168.1.20"]
MORDECAI_PHILIPS_HUE_ALLOWED_LIGHT_IDS=["a1b2c3d4-light-id"]
MORDECAI_PHILIPS_HUE_ALLOWED_SCENE_IDS=["e5f6g7h8-scene-id"]
```

The direct Hue path is bridge-local and does not use a cloud discovery fallback. The configured bridge host must remain on the explicit allowlist.

## Runtime behavior

When configured, the runtime manifest includes these tools:

- `home.list_entities`
- `home.list_scenes`
- `home.toggle_light`
- `home.activate_scene`

The list tools aggregate results across every configured backend and return normalized records with:

- `id`: stable runtime-facing ID such as `home-assistant:light.kitchen` or `philips-hue:a1b2c3d4-light-id`
- `backend`: `home-assistant` or `philips-hue`
- `backend_id`: the raw upstream entity or resource ID
- `name`: operator-facing display name
- `type`: `light` or `scene`
- `state`: current light state where applicable
- `attributes`: selected backend-specific metadata

If one backend fails while another succeeds, the list result includes an `errors` array so the operator can see the partial failure instead of receiving a silent fallback.

State-changing tool results include:

- the backend that handled the action
- the normalized entity or scene record
- previous and current state for light toggles
- explicit activation status for scenes

## Example API calls

List configured lights and scenes through the generic tool execution spine:

```json
POST /api/tools/execute
{
  "tool": "home.list_entities",
  "granted_permissions": ["network", "home-automation"]
}
```

Toggle a Home Assistant light by raw allowlisted entity ID:

```json
POST /api/tools/execute
{
  "tool": "home.toggle_light",
  "arguments": {"entity_id": "light.kitchen"},
  "granted_permissions": ["network", "home-automation"],
  "safe_mode": false
}
```

Toggle a Philips Hue light by normalized backend-prefixed ID:

```json
POST /api/tools/execute
{
  "tool": "home.toggle_light",
  "arguments": {"entity_id": "philips-hue:a1b2c3d4-light-id"},
  "granted_permissions": ["network", "home-automation"],
  "safe_mode": false
}
```

Activate an allowlisted scene:

```json
POST /api/tools/execute
{
  "tool": "home.activate_scene",
  "arguments": {"scene_id": "scene.movie"},
  "granted_permissions": ["network", "home-automation"],
  "safe_mode": false
}
```

## Operational constraints

- This slice does not implement webhook subscriptions or live state sync.
- This slice does not implement wildcard allowlists.
- This slice does not implement Home Assistant automation service execution beyond scene activation and light toggling.
- This slice does not implement Philips Hue bridge discovery or registration flows.

If broader device categories or event subscriptions are added later, they should be implemented as additional explicit tools and remain behind the same proxy, allowlist, and confirmation boundaries.