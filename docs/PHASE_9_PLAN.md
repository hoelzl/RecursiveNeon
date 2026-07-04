# Phase 9 Plan: Game-Reactive Systems

> **Date**: 2026-05-13
> **Status**: Planned
> **Depends on**: Phases 0-7f complete; `docs/GAME_DESIGN.md` decisions §11
> **Unlocks**: Act 1 vertical slice; Phase 8 (browser) thereafter

## Overview

Phase 9 builds the Tier-1 backend from `docs/GAME_DESIGN.md` §10 — the
five systems required to test whether an LLM-driven world can be
reactive enough to be interesting. After Phase 9, the project has a
playable Act 1 vertical slice in the CLI; only then does Phase 8
(browser rendering) make sense.

Six sub-phases, each a standalone commit:

| Sub-phase | Summary | Architectural question it answers |
|---|---|---|
| 9a | Flag / quest state | Can the save model carry arbitrary world state cleanly? |
| 9b | NPC perception filter | Can NPCs react to shell actions, not just chat? |
| 9c | Knowledge gates in NPC prompts | Can NPCs hold *contradictory* knowledge per character? |
| 9d | NPC initiative + queued messages | Can NPCs initiate, not just respond? |
| 9e | Director ("Fate") system | Can between-session world-mutation nudge the story? |
| 9f | Act 1 vertical slice | Do all of the above hold up under real play? |

### Dependencies

```
9a (flags) ─────┬─→ 9c (knowledge gates) ─┐
                │                         │
9b (perception)─┴─────────────────────────┼─→ 9f (vertical slice)
                                          │
9d (initiative) ──────────────────────────┤
                                          │
9e (director) ────────────────────────────┘
```

`9d` is independent of `9a/9b/9c` and could be parallel work. `9e`
draws on all four — it's a coordinator, not a new mechanism.

## Design Principles

1. **Reuse the event bus.** `GameEventBus` already exists
   (`services/game_event_bus.py`). Every new producer publishes events
   onto it; every consumer subscribes. No parallel signalling mechanism.
2. **NPCs hold only their own truth.** A central "world truth" store
   is an anti-pattern for the LLM-reactivity test — it makes
   contradictory beliefs hard to express. Each NPC's knowledge is what
   its perception filter has surfaced plus what its system prompt
   asserts. There is no global "what the player knows."
3. **Director is dumb first, smart later.** First implementation of 9e
   is a hand-written rule set (`if relationship[warden] < -50 and
   files_read["pay_log.txt"]: queue_message(...)`). Only once we see
   what interventions are useful do we consider replacing rule eval
   with an LLM call.
4. **Persistence is JSON, not a DB.** Match existing pattern: flags,
   queued messages, and Director state all save to `game_data/*.json`
   alongside `filesystem.json`, `notes.json`, etc.
5. **DI for new services.** Every new service flows through
   `ServiceContainer` / `ServiceFactory`. No globals.
6. **Tests are unit-level.** Integration tests live in 9f. Each
   sub-phase 9a–9e ships with focused unit tests; the vertical slice
   is the integration test.

---

## 9a: Flag / Quest State

### Goal

A persistent, key→value world-state store that game logic and NPCs can
query and mutate. The substrate for knowledge gates (9c), director
rules (9e), and any future quest tracking.

### Design sketch

- New service: `FlagService` (interface `IFlagService` in
  `services/interfaces.py`).
- API:
  - `set_flag(key: str, value: Any = True) -> None`
  - `clear_flag(key: str) -> None`
  - `get_flag(key: str, default: Any = None) -> Any`
  - `has_flag(key: str) -> bool`
  - `list_flags() -> dict[str, Any]`
- Values are JSON-serialisable scalars. No nested structures (keep the
  surface small; if you need structure, namespace the key).
- Each mutation publishes on `GameEventBus`:
  - `flag.set` → `{"key": str, "value": Any, "old_value": Any | None}`
  - `flag.cleared` → `{"key": str, "old_value": Any}`
- Persistence: `game_data/flags.json` — flat dict round-trip.
- Loaded/saved by `AppService` alongside other game state.

### Files affected

- `backend/src/recursive_neon/services/flag_service.py` *(new)*
- `backend/src/recursive_neon/services/interfaces.py` — add `IFlagService`
- `backend/src/recursive_neon/dependencies.py` — register in DI
- `backend/src/recursive_neon/services/app_service.py` — load/save hook
- `backend/tests/unit/services/test_flag_service.py` *(new)*

### Optional shell exposure

Add a `flag` debug command (set/get/list/clear) — gated behind a
`--debug` config option or hidden from `help` by default. Useful for
manual playtesting; not part of the diegetic interface.

### Success criteria

- CRUD round-trip with persistence.
- Events fire correctly on set/clear, including `old_value`.
- DI registration works; `FlagService` is injectable.
- 20-30 unit tests.

---

## 9b: NPC Perception Filter

### Goal

Each NPC subscribes to a configurable subset of `GameEventBus`
events. Subscribed events accumulate in a per-NPC bounded buffer that
feeds into the NPC's system prompt as "what you've observed." This is
the **single highest-value item** of Phase 9 — the architectural
question is whether NPCs can react to player *actions* (not just
chat).

### Design sketch

- New module: `services/npc_perception.py`.
- New event types published by existing code:
  - `shell.command_run` → `{"command": str, "args": list[str], "cwd": str}`
    — published by the shell on each submitted line (cooked mode).
  - `filesystem.read` → `{"path": str, "file_id": str}` — published by
    `AppService.read_file`.
  - `filesystem.write` → `{"path": str, "file_id": str, "operation": "create"|"update"|"delete"}`
    — published by `AppService` mutations.
  - `npc.chat_sent` → `{"target_npc_id": str, "text": str}` — player→NPC.
  - `npc.chat_received` → `{"source_npc_id": str, "text": str}` — NPC→player.
- Chat events are **filtered to the NPC by default**: a subscription to
  `npc.chat_sent` / `npc.chat_received` only delivers events where the
  NPC is the target (for `chat_sent`) or the sender (for `chat_received`).
- An NPC can opt into eavesdropping on *all* chat by subscribing to the
  explicit super-prefix `npc.chat_sent.all` / `npc.chat_received.all`.
- Per-NPC config (added to `NPC` model):
  ```python
  class PerceptionConfig(BaseModel):
      subscriptions: list[str] = []      # event-type prefixes
      buffer_size: int = 50              # max events retained
      include_in_prompt: bool = True     # render to system prompt
  ```
- `NPCPerceptionTracker` subscribes to the bus on NPC creation,
  matches events by subscription prefix (`shell.*` matches all shell
  events), and pushes them into a `collections.deque(maxlen=...)` per
  NPC. For chat events the tracker additionally applies the default
  own-NPC filter unless an `.all` eavesdropping subscription is present.
- `NPCManager` calls `tracker.render_for(npc_id)` when building the
  system prompt — returns a short human-readable summary of recent
  events (last N lines, formatted as "Player ran `find /etc -name *.key`",
  "Player read `/Documents/pay_log.txt`", etc.).
- Per the three NPC profiles in `docs/GAME_DESIGN.md` §7:
  - `warden.subscriptions = ["shell.*", "filesystem.*", "npc.chat_sent.all"]`
    — deliberately eavesdrops on all player chats.
  - `archivist.subscriptions = ["filesystem.*"]`
  - `zero.subscriptions = ["npc.chat_sent"]` (only when targeted at zero)

### Files affected

- `backend/src/recursive_neon/services/npc_perception.py` *(new)*
- `backend/src/recursive_neon/models/npc.py` — add `PerceptionConfig`,
  attach to `NPC`.
- `backend/src/recursive_neon/services/npc_manager.py` — wire tracker
  into system-prompt construction.
- `backend/src/recursive_neon/services/app_service.py` — publish
  `filesystem.*` events.
- `backend/src/recursive_neon/shell/shell.py` — publish
  `shell.command_run` after parsing each submitted line.
- `backend/tests/unit/services/test_npc_perception.py` *(new)*

### Open design question

Resolved: chat events are **own-NPC by default**; global eavesdropping
is opt-in via the `npc.chat_sent.all` / `npc.chat_received.all`
subscription prefixes. This keeps context small for most NPCs while
still allowing a honeypot NPC such as `warden` to deliberately
overhear player plotting.

### Success criteria

- Three NPCs receive the correct event subsets per their config.
- Buffer respects `maxlen`.
- System-prompt rendering produces readable, time-ordered summaries.
- 25-40 unit tests covering: subscription matching, buffer eviction,
  prompt rendering, cross-NPC isolation (warden's perception ≠
  archivist's).

---

## 9c: Knowledge Gates in NPC Prompts

> **Status (2026-07-04)**: Implemented. Engine + a representative subset
> of gates seeded on `warden` / `archivist` / `zero`. Remaining Story
> Bible §9 gates deferred to 9f, which the Bible marks as the iteration
> point. Implementation notes that diverged from the original sketch:
> - The perception tracker's buffer was upgraded from rendered strings
>   to structured `PerceivedEvent` records so gates can query by
>   `event_type` / `data` (the original string buffer was lossy). Prompt
>   rendering is unchanged.
> - `KnowledgeGate` gained `perception_min_count` and `min_relationship`
>   fields to cover the Story Bible §9 predicate shapes (count-based
>   perception, composite flag+relationship gates) that the original
>   sketch did not anticipate.
> - `FlagService` is injected into `NPCManager` and gates evaluate in
>   `_build_messages` against `(flags, perception buffer, relationship)`.

### Goal

NPC system prompts assert what each NPC *does* and *does not* know,
gated on flags + perception history. Without this, NPCs hallucinate
knowledge (LLM default behaviour) and there's no architectural test of
whether the system can maintain contradictory truth states.

### Design sketch

- Per-NPC config (added to `NPC` model):
  ```python
  class KnowledgeGate(BaseModel):
      topic: str                          # short identifier
      requires_flag: str | None = None    # flag must be set
      requires_perception: str | None = None  # event must have been observed
      description: str                    # text injected when gate opens
      counter_description: str | None = None  # text injected when gate is closed
  ```
- `NPC.knowledge_gates: list[KnowledgeGate]` — evaluated at prompt
  build time.
- System-prompt construction (`NPC.get_system_prompt`) gets new sections:
  - **What you know**: descriptions of gates whose conditions are met.
  - **What you do not know**: counter_descriptions of gates that are
    closed (only those with `counter_description` set — many gates are
    silent).
- Evaluation depends on injected `FlagService` and the NPC's
  `NPCPerceptionTracker`. The model layer can't reach those, so
  evaluation moves to `NPCManager` and feeds *resolved* text into the
  prompt template.

### Files affected

- `backend/src/recursive_neon/models/npc.py` — add `KnowledgeGate`.
- `backend/src/recursive_neon/services/npc_manager.py` — evaluate
  gates, inject resolved knowledge sections into prompt.
- `backend/tests/unit/services/test_knowledge_gates.py` *(new)*

### Worked example

```python
warden.knowledge_gates = [
    KnowledgeGate(
        topic="player_searched_for_keys",
        requires_perception="shell.command_run:find -name *.key",
        description="The player has been searching for key files.",
    ),
    KnowledgeGate(
        topic="honeypot_purpose",
        requires_flag="warden_revealed_honeypot",
        description="You can speak openly about the trap's purpose.",
        counter_description="You must not reveal that neon-proxy is a honeypot.",
    ),
]
```

### Success criteria

- Gate evaluation is pure (given flags + perception, output is
  deterministic).
- Closed gates suppress topics from prompt output; open gates inject
  them.
- Two NPCs with conflicting `KnowledgeGate` definitions on the same
  topic produce conflicting system prompts — i.e., the architecture
  successfully holds divergent truths.
- 15-25 unit tests.

### Story Bible dependency

9c needs actual gate definitions to be implementable beyond toy
examples. **Draft `docs/STORY_BIBLE.md` before 9c starts.** It feeds
9c (gates), 9d (queued messages), and 9e (Director rules).

---

## 9d: NPC Initiative + Queued Messages

> **Status (2026-07-04)**: Implemented. `NPCMessageQueue` mirrors the
> FlagService pattern: a thin synchronous mutator over
> `game_state.npc_messages`, with `AppService` owning the
> `npc_messages.json` round-trip. Delivery renders at session start in
> `Shell.run()` (the single shared hook for local CLI, WebSocket, and
> browser transports). Implementation notes:
> - The queue is a *display* mechanism: messages are shown in a
>   "Messages while you were away" block but are NOT appended to NPC
>   conversation history — responding remains a player-initiated
>   `chat` action.
> - Because the production container is shared across concurrent WS
>   sessions, `mark_delivered` is global: once shown, a message is
>   suppressed for all sessions. This matches the between-session
>   continuity intent (each message shows once); per-player delivery
>   tracking would require a first-class player-identity concept that
>   doesn't exist yet.
> - Two new events on the bus: `npc.message.queued`,
>   `npc.message.delivered`.

### Goal

NPCs can *send* the player messages that arrive at the start of the
next session, rather than waiting passively for `chat`. This makes the
world feel responsive between sessions and gives the Director (9e) a
concrete intervention tool.

### Design sketch

- New service: `NPCMessageQueue` (interface `INPCMessageQueue`).
- API:
  - `queue(npc_id: str, text: str, deliver_after: datetime | None = None) -> str`
    (returns message id).
  - `pending(npc_id: str | None = None) -> list[QueuedMessage]`.
  - `mark_delivered(message_id: str) -> None`.
- `QueuedMessage` model: id, npc_id, text, queued_at, delivered_at,
  deliver_after.
- Persistence: `game_data/npc_messages.json`.
- Delivery: on shell startup, `NPCManager` (or shell init) queries
  pending messages and prints a header like:

  ```
  ── Messages while you were away ──────────────
  [warden] 03:14:22 — I noticed your search yesterday. Stop.
  [zero] 03:47:01 — Don't trust the archivist. We need to talk.
  ──────────────────────────────────────────────
  ```
- Messages are *displayed* but not auto-added to the NPC's
  `conversation_history` — they're treated as part of the NPC's voice,
  and the player decides whether to respond via `chat`.

### Files affected

- `backend/src/recursive_neon/services/npc_messages.py` *(new)*
- `backend/src/recursive_neon/models/npc.py` — add `QueuedMessage`.
- `backend/src/recursive_neon/services/interfaces.py` — add
  `INPCMessageQueue`.
- `backend/src/recursive_neon/dependencies.py` — register in DI.
- `backend/src/recursive_neon/shell/shell.py` — render pending
  messages at session start.
- `backend/tests/unit/services/test_npc_messages.py` *(new)*

### Success criteria

- Queue persists across save/load.
- Messages delivered in queue order at session start.
- `deliver_after` honours time gating.
- Once shown, message is marked delivered and not re-shown.
- 15-25 unit tests.

---

## 9e: Director ("Fate") System

### Goal

A between-session pass that surveys the world and applies *one or
more small interventions* to nudge the story along — never to force
it. Crawford's "Fate" framing: the Director is not omnipotent, it is
opportunistic.

### Design sketch

- New service: `Director`.
- Triggered on session boundaries:
  - On disconnect: snapshot current state, run intervention pass,
    apply changes to save.
  - On reconnect: load already-mutated state; player sees the world
    has shifted.
- Survey inputs:
  - Current flags (`FlagService.list_flags()`)
  - NPC relationships
  - Files read / written this session (from perception buffers)
  - Story beat (a flag like `story.beat`)
  - Sessions since last meaningful flag change
- Intervention vocabulary (start small):
  - `set_flag` / `clear_flag`
  - `queue_npc_message`
  - `adjust_relationship(npc_id, delta)`
  - `plant_file(path, content)` — writes a `FileNode` to the FS
  - `delete_file(path)` — for antagonist-driven file disappearance
- Decision logic (initial): hand-written rules in
  `services/director/rules.py`. Each rule has a predicate over the
  survey state and a list of interventions. Rules are evaluated in
  priority order; the first matching rule fires; ties broken
  deterministically by rule order.
- Decision logic (later, deferred): replace rule evaluation with an
  LLM call once we know what interventions look like in practice.
  Until then, **do not** introduce an LLM dependency — that's
  optimising before observing.
- Trigger policy: configurable. Two candidates (see §11 of
  `GAME_DESIGN.md`):
  - **Every disconnect**: simple, predictable, sometimes feels
    over-eager.
  - **Stuck detection**: only fires after N sessions with no flag
    change. Less spammy, but the player can miss out on the world
    feeling alive.

  Default: **every disconnect, with a per-rule cooldown** (each rule
  records when it last fired; cooldown blocks re-fire within N
  sessions).

### Files affected

- `backend/src/recursive_neon/services/director/__init__.py` *(new)*
- `backend/src/recursive_neon/services/director/rules.py` *(new)* —
  initial hand-written rule set.
- `backend/src/recursive_neon/services/interfaces.py` — add
  `IDirector`.
- `backend/src/recursive_neon/dependencies.py` — register in DI.
- `backend/src/recursive_neon/main.py` and/or `terminal.py` — hook
  into disconnect/connect lifecycle.
- `backend/tests/unit/services/test_director.py` *(new)*
- `backend/tests/unit/services/test_director_rules.py` *(new)*

### Success criteria

- Rule evaluation is deterministic and testable in isolation.
- Each intervention type has an applier that calls the right service
  and is unit-tested in isolation.
- Director state (rule fire history, cooldowns) persists across
  save/load.
- Director runs at session boundaries without blocking shell startup.
- 25-40 unit tests, including a "no rule fires" baseline.

---

## 9f: Act 1 Vertical Slice

### Goal

Bring 9a–9e together into a playable Act 1 slice and find out where
the architecture leaks. This is the integration test of Phase 9 and
the gating step before any browser work.

### Scope

- Three NPCs (`warden`, `archivist`, `zero`) with full definitions:
  voice, perception config, knowledge gates, initial relationships.
- A starter filesystem populated with files the NPCs reference and
  files the player must discover.
- ~5 narrative beats — enough to validate that:
  - NPCs react to shell actions (9b stress test).
  - NPCs hold contradictory beliefs without collapsing (9c stress
    test).
  - Director moves the story when the player gets stuck (9e stress
    test).
  - Queued messages create a sense of between-session continuity (9d
    stress test).
- One open-ended "scripting" beat — the player is encouraged to write
  a script (in-fiction file) that an NPC then reads and comments on.
  Tests whether in-fiction scripting actually adds value.

### Deliverables

- `docs/STORY_BIBLE.md` — fully populated by this point.
- Starter save: `game_data/initial_state.json` with the three NPCs,
  starter filesystem, and an empty flag set.
- A scripted playthrough document (`docs/PHASE_9F_PLAYTEST.md`)
  describing the intended path, the alternate paths the architecture
  supports, and what was observed.

### Success criteria

- Subjective: does the world feel reactive? (This is the question
  Phase 9 exists to answer; a "no" is informative and should drive
  rework, not be papered over.)
- Objective: every Tier-1 system from `GAME_DESIGN.md` §10 is
  exercised end-to-end at least once during the playtest.
- The three open §11 questions in `GAME_DESIGN.md` (slice scope,
  identity persistence, Director trigger policy) get resolved by
  observation rather than guesswork.

---

## Out of Scope for Phase 9

Tier-2 items from `GAME_DESIGN.md` §10 (file permissions, time/session
model, command unlocks, virtual process list) are deliberately
deferred. They become Phase 10 if Phase 9 validates the approach.

Phase 8 (browser) is also deferred — see `GAME_DESIGN.md` §12. The
browser is a rendering target; rendering nothing-yet is wasted effort.

---

## Open Questions

Inherited from `GAME_DESIGN.md` §11 — still unresolved, decide before
or during the sub-phase that needs each:

- `[?]` (blocks 9f) Slice scope: Act 1 full vs. one full NPC arc?
- `[?]` (blocks 9c) Does player identity persist across save/load,
  or is it per-NPC memory only?
- `[?]` (blocks 9e) Director trigger: every disconnect, stuck-only,
  or hybrid with cooldown? *Default: hybrid with cooldown.*

Phase-9-specific:

- `[x]` (blocks 9b) Cross-NPC chat eavesdropping: do all NPCs hear
  all `chat` events, or only the addressed NPC? *Resolved: only the
  addressed NPC by default; eavesdropping is opt-in via the
  `npc.chat_sent.all` / `npc.chat_received.all` subscriptions.*
- `[?]` (blocks 9e) Does the Director have access to *future*
  interventions or only react to past state? Starting position:
  reactive only. Adding lookahead is an explicit later upgrade.
