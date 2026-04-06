# Game Events Schema

Events are published via `GameEventBus` (in `services/game_event_bus.py`).
Subscribers receive `(event_type: str, data: dict)`.

## Events

### `editor.buffer_saved`

Published after a buffer is successfully saved (via `save-buffer`, `write-file`, or `save-some-buffers`).

| Field         | Type         | Description                        |
|---------------|--------------|------------------------------------|
| `buffer_name` | `str`        | Name of the saved buffer           |
| `filepath`    | `str | None` | Virtual filesystem path, if any    |
| `contents`    | `str`        | Full text content after save       |

**Example subscriber:**

```python
def on_save(event_type: str, data: dict) -> None:
    if data["buffer_name"].startswith("*note:"):
        print(f"Note saved: {data['filepath']}")

bus.subscribe("editor.buffer_saved", on_save)
```

## Subscribing

```python
from recursive_neon.services.game_event_bus import GameEventBus

bus = GameEventBus()
bus.subscribe("editor.buffer_saved", handler)
bus.unsubscribe("editor.buffer_saved", handler)
```

The bus is available on `ServiceContainer.event_bus`.  Errors in
handlers are logged but do not prevent other handlers from running.

## Future Events

Additional events (quest triggers, NPC state changes, etc.) will be
added as game scripts are implemented in later phases.
