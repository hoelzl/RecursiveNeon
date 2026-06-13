# Game Design — Recursive://Neon

> **Status**: Skeleton draft. Everything in this document is provisional —
> mark items `[DECISION]` where alternatives matter, `[TBD]` where detail
> is missing. The goal of this doc is to surface backend gaps before
> Phase 8, not to ship a final narrative.

---

## 1. Premise (one paragraph)

You are a freelance intrusion specialist. A client has paid you to investigate
**neon-proxy**, a forgotten server still drawing power inside a corporation
that officially decommissioned it years ago. Your only access is a shell
session over a brittle, monitored connection. The deeper you explore the
filesystem and talk to whatever still lives on the machine, the more it
becomes clear that neon-proxy isn't a dead server — and that the client
who hired you may not be who they claimed.

---

## 2. Setting

- **Genre**: near-future cyberpunk, low-fi.
- **Scope**: the entire game takes place inside one compromised system.
  No "open world" — the world is the filesystem, the processes, and the
  voices on the other end of `chat`.
- **Tone**: paranoid, dry, occasionally funny. Closer to *Hypnospace
  Outlaw* / *Else Heart.Break()* than *Cyberpunk 2077*.
- **Time pressure**: the connection is unstable. Sessions are not
  infinite — see §4, *Core loop*.

---

## 3. The Player

- **Identity**: blank slate. The player is whoever they choose to be;
  the game does not impose backstory, name, gender, or affiliation.
  Rationale: an LLM-driven world cannot enforce traits the player
  decides to ignore, so pretending it can is a worse experience than
  acknowledging it can't.
- **Skill assumption**: the player can read a terminal but is **not**
  assumed to know Unix. The game teaches commands as quest hooks
  (`man` / `help` are diegetic; learning a new command is progression).
- **Motivation**: player-projected. Money, curiosity, leverage — the
  player tells NPCs whatever they want; NPCs respond to what they're
  told. This is a deliberate test: can the NPC system handle the
  player's *stated* motivation as input rather than rely on a fixed
  protagonist profile?
- **What the player cannot do**: leave the system. There is no "real
  world" outside the shell. NPCs can talk about it; the player never
  sees it.

---

## 4. Core Loop

Moment-to-moment:

1. **Explore** the filesystem (`ls`, `cat`, `grep`, `find`, `fsbrowse`).
2. **Talk** to NPCs (`chat`) to learn what files mean and who lived here.
3. **Solve** a concrete obstacle — locked file, port to identify, memory
   region to decode, encrypted note (minigames map onto these).
4. **Record** findings (`note`, `task`) — these are the player's only
   external memory.
5. **Earn trust or leverage** with an NPC, unlocking deeper access.

Session loop:

- Each "session" ends when the connection drops, when the player runs
  `exit`, or when an in-fiction event forces disconnect.
- Reconnecting brings the player back with their notes and tasks intact;
  some in-world state has shifted (NPCs have moved, files have been
  deleted by the antagonist, etc.).

---

## 5. Story Arc (3 acts, ~5-10 hours estimated)

**Act 1 — The Surface.** Player gets paid to "look around and report
what's there." Filesystem looks like an abandoned corp server. First NPC
(Zero) is hostile, treats player as an intruder. Player learns the basic
shell, finds the first inconsistency (e.g., a file with a future
timestamp).

**Act 2 — The Inhabitants.** More NPCs surface. They contradict each
other. Player must pick who to trust. Player gains tools — the editor
becomes useful, scripting hooks appear, hidden services on unfamiliar
ports reveal themselves. The client starts pushing for a specific
deliverable that doesn't match what the player is finding.

**Act 3 — The System.** Player realizes neon-proxy is a **honeypot**.
The corporation never decommissioned it; the player is the experiment.
The NPCs split along their pre-existing loyalties:
- The corp-aligned NPC reveals (or is forced to reveal) what the trap is
  actually testing.
- The partially-aligned NPC has to choose between corp directive and
  their private agenda.
- The opposed NPC was trapped here too, and offers a way out — at a cost.

Ending branches off the player's accumulated relationships and the final
choice in a confrontation scene that happens entirely in `chat` and the
editor.

*Why B over a single-AI reveal (the discarded C option):* a single AI
playing all NPC roles would give every NPC the same hidden ground truth
— we'd never learn whether the system handles divergent goals, secrets,
and incomplete knowledge across characters. Honeypot-with-defectors
forces the system to maintain contradictory truth states, which is the
architecturally interesting case.

---

## 6. Antagonist

**The Corporation.** The system is studying *you*. The antagonist is
the watcher logging your every command — diegetically present as the
NPC `warden`. This also justifies the existing shell-history
persistence: the player's command history is the corp's primary
instrument.

The antagonist must be present **in the shell** — readable in logs,
audible in `chat`, traceable in process lists. They are never an
off-screen authority. `warden` is the antagonist's voice; the
Corporation itself is the antagonist's institutional weight, referenced
in files and never directly addressable.

---

## 7. NPC Roster

Three named NPCs is enough to stress-test the architecture. More NPCs
add content burden without much architectural signal — the interesting
variation is in *how* they differ, not *how many* there are.

All three are diegetic shell identities the player addresses via
`chat <name>`.

| Handle | Motivation profile | Hook | Perceives | Trust starts at |
|---|---|---|---|---|
| `warden` | Aligned corp | Enforces the trap. Knows it's a trap. Speaks in log entries early; reveals personhood as relationship deepens. | **All player shell input** in real-time | hostile |
| `archivist` | Partially aligned | Corp employee tasked with logging the trap. Has a personal agenda that occasionally overrides corp directives. | **File-access events only** (the player reads or writes a file) | indifferent |
| `zero` | Opposed | Non-corp hacker. Caught in the same honeypot months ago. Has knowledge the corp wants to extract. | **Only what the player types into `chat`** (no shell visibility) | curious |

The partially-aligned middle profile (`archivist`) is where LLMs
typically fail — straight opposition and straight alignment are easy to
roleplay; ambivalence collapses to one pole. Testing whether the system
maintains divergent-but-overlapping goals is the central architectural
question.

Each NPC needs (engine work):

- A **system prompt** that gives them a voice, a memory of past
  sessions, and explicit knowledge of which files they "know about."
- A **perception filter** — what subset of game events flow into their
  context. See §10 item 2.
- **Knowledge gates**: NPC will only discuss topic X if relationship ≥
  Y *or* the player has read file Z. See §10 item 3.
- **Mutable state**: relationship value, list of files they've
  referenced, list of secrets they've revealed.
- **Initiative**: ability to send the player a queued message that
  appears at the start of the next session (not live `chat`). See §10
  item 4.

---

## 8. Win / Lose Conditions

- **Win** = reach an ending scene and make a final choice. There is no
  "wrong" ending; there are endings that lose the player specific NPCs
  forever, endings that lose the player money, endings that lose the
  player their own identity.
- **Soft lose** = burn every NPC relationship below threshold. The shell
  still works but no one will talk to you, so no more story unlocks.
  Game continues as a sandbox.
- **Hard lose** = none. The system is the story; the player can always
  reconnect. Soft-lose via burned relationships is the only failure
  state. Rationale: in prototype, getting shut out of the experiment
  has more cost than gameplay value.

---

## 9. Progression

The player does not gain stats. They gain:

- **Commands** — new shell capabilities are unlocked diegetically (an NPC
  teaches `find -exec`; a file reveals a hidden binary). Implementation:
  `ProgramRegistry` already supports per-session command visibility;
  needs a "locked/unlocked" flag.
- **Knowledge** — discovered files, decoded messages, NPC backstories.
  Tracked in `notes` (player-curated) and a hidden knowledge set (engine).
- **Access** — directories that were 403 become readable; NPCs that
  refused to talk now respond.
- **Tools / Scripts** — the player gets **in-fiction** scripting:
  scripts the player writes are files in the game world, and NPCs can
  read them. ("I see you've automated `find -name *.key` — what are
  you looking for?") This is a deliberate architectural test, not a
  convenience feature: it forces the LLM-reactive layer to handle
  player-authored content as input. The `.neon-edit.py` config sandbox
  already exists and can serve as the substrate; what's new is
  exposing scripts to NPCs via the perception filter (§10 item 2).

---

## 10. Backend Gaps This Design Reveals

Things the current backend does **not** have that the story above
requires. Ordered by prototype priority — items 1–5 are the **minimum
to test the system architecture**; items 6–11 are second-tier.

### Tier 1 — minimum for prototype

1. **Quest / flag state.** Per-save key→value store for "has player
   read file X", "has NPC Y revealed secret Z." Currently only files,
   notes, tasks, and NPC relationship+memory are persisted.
2. **NPC perception filter.** Per-NPC configurable subscription to the
   `GameEventBus`. `warden` sees `shell.command_run` events for every
   submitted command; `archivist` sees only `filesystem.read` /
   `filesystem.write`; `zero` sees nothing the player doesn't type
   into `chat`. Each NPC's filter feeds a rolling context window
   injected into their system prompt. **Highest-value item** for what
   the prototype is testing.
3. **Knowledge gates in NPC prompts.** `NPCManager` must inject "you
   know about file X, you do not know about file Y" into the system
   prompt based on game flags + perception history, not just chat
   history.
4. **NPC initiative + queued messages.** NPCs need to *send* messages
   the player reads at the start of the next session (not live
   `chat`). `GameEventBus` is the right substrate; no producer exists.
5. **Director ("Fate") system.** Between-session world-mutation pass
   that nudges the story without forcing it. Crawford-style: surveys
   current state (relationships, files read, story beat), picks a small
   intervention (move an NPC, plant a file, drop the warden's tolerance
   threshold, queue a message), applies it. Lives between save and
   load. Implementation can start as a hand-written rule set and later
   be replaced by an LLM call once we know what interventions look
   like.

### Tier 2 — needed for full Act 1 but skippable for first prototype

6. **Scripted FS mutations.** APIs for narrative agents (NPCs,
   Director) to write/delete files. Today only the player can mutate
   the FS.
7. **File permission model.** `FileNode.requires: list[FlagRef]` —
   directories locked until a flag is set. `AppService` checks on
   read.
8. **Time / session model.** Sessions need a notion of "this is your
   Nth connection." Currently saves are continuous.
9. **Script-as-readable-content.** Player-authored scripts (extending
   `.neon-edit.py` into in-fiction territory) need to be `FileNode`s
   that NPCs can `cat` via their perception filter.
10. **Diegetic command unlocks.** `ProgramRegistry` lists all programs
    unconditionally. Needs per-session visibility tied to flags.
11. **Process list as fiction.** `sysmon` shows real backend processes;
    the game wants `warden` to appear in the process list. Needs a
    virtual-process layer overlaying real processes.

---

## 11. Decisions Made

| Question | Answer | Rationale |
|---|---|---|
| Player identity | Blank slate | LLM can't enforce defined traits anyway |
| Act 3 reveal | Honeypot (B) | Forces divergent truth states across NPCs |
| Player scripting | Yes, in-fiction | Stress-tests LLM-reactive layer |
| Hard-lose state | No | Prototype value is in exploration, not failure |
| Minigames in story | Skippable / deprioritized | Low architectural signal |
| Tone | Dry, occasionally funny | Acknowledged as harder for LLMs — early signal of model tier |
| NPC count | 3 (one per motivation profile) | Architectural variation matters, not count |
| NPC perception | Per-NPC, configurable | `warden`=all, `archivist`=files, `zero`=chat-only |
| Between-session world | Yes, via Director (Fate) | Crawford-style soft direction |

### Remaining smaller decisions

- `[?]` Story length target for the first prototype slice — "vertical
  slice through Act 1" or "vertical slice through one full NPC arc"?
  Different shape, similar size.
- `[?]` Does the player's identity persist across save/load — if they
  tell `archivist` their name is "Kai," is that recorded as
  player-state or only as `archivist`'s memory?
- `[?]` How does the Director decide *when* to nudge — every
  disconnect, or only when the player is "stuck" (no flag changes for
  N sessions)?

---

## 12. Next Steps

1. **Phase 9 plan.** Sequence Tier-1 items from §10 into sub-phases
   (9a–9e or similar). Natural ordering: flag state → perception
   filter → knowledge gates → NPC initiative → Director. Each is a
   standalone commit with tests.
2. **Story Bible.** Draft `docs/STORY_BIBLE.md` — canonical names,
   locations, secrets for the three NPCs and the honeypot's contents.
   Needed before any prompt-engineering work on NPC voices.
3. **Vertical slice.** Build an Act 1 vertical slice end-to-end in the
   CLI before any browser work. This is the V2 principle restated:
   gameplay works in a real terminal first.
4. **Phase 8 (browser) — defer.** Pick up only after the Tier-1
   backend is in place and we have a working vertical slice to render.
   The browser is a rendering target, not a design driver.
