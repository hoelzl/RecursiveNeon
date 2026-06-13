# Story Bible — Recursive://Neon

> **Date**: 2026-05-13
> **Status**: Draft v1. Locks in canonical names, voices, and Act 1
> content for the Phase 9 prototype. Iterate during 9f playtest;
> archive divergences as decisions.
> **Reads**: `docs/GAME_DESIGN.md` (premise + decisions), feeds
> `docs/PHASE_9_PLAN.md` (9c gates, 9d messages, 9e Director rules).

This doc is the prototype's single source of truth for names, voices,
secrets, and starter content. Where things are deliberately ambiguous
in-fiction, the **ground truth is here** even if no NPC ever says it.

---

## 1. Premise (canonical)

**Steadway Group** is a holding company that publicly does "supply
chain intelligence" and privately operates a paid intrusion-analytics
service: companies pay Steadway for behavioural profiles of attackers
who target their infrastructure. Steadway builds those profiles using
**honeypot systems** — decoy networks that look like decommissioned
corporate gear. They harvest the data, tag the techniques, and sell
the resulting attacker profiles to security vendors, insurers, and
(quietly) law-enforcement-adjacent buyers.

**neon-proxy** is one such honeypot. It is dressed as a forgotten
proxy server that should have been shut down years ago. In fact it is
live, monitored, and actively recording every command the player
types.

The player has been contracted by a third party who claims to want a
look at "what's still on the box." That third party is, in fact, also
Steadway — the contract is bait, the client is fake, the entire setup
is a controlled experiment on the player.

Three other identities live on neon-proxy:

- A **watcher** (`warden`) employed by Steadway to monitor and
  categorise new captures.
- A **cataloguer** (`archivist`) — a Steadway employee with a private
  motive for being there.
- A **previous capture** (`zero`) — a real hacker, trapped here months
  ago, who has not yet been "extracted."

What "extraction" means is something Steadway prefers not to spell
out (see §3.2).

---

## 2. World Outside the System

The player never sees the world outside the shell, but NPCs reference
it. Canonical facts the world rests on:

- **Era**: near-future, roughly 203X. Cyberpunk-low-fi. Smartphones,
  cars, and cities exist; widespread AI exists but is not yet
  godlike.
- **Steadway Group** is a mid-tier holding company headquartered in
  a coastal city. Real-sounding, slightly menacing, anonymous in the
  way actual rent-extractive firms are.
- **The "consultant pool"** is Steadway's euphemism for people they've
  caught and then coerced into working for them. Pay is real; freedom
  to leave is theoretically real but actually not. (See §3.2 — this
  is the central dark fact under the honeypot business.)
- **Outside hackers** know Steadway exists by reputation but few
  understand the consultant-pool mechanism.

The world is not the focus. The system is. Anything not nailed down
in this doc is *the player's projection*, and NPCs should respond to
the player's framings without committing to them.

---

## 3. Steadway Group (the antagonist)

### 3.1 Cover business

- Public name: **Steadway Group, Ltd.**
- Public business: supply-chain intelligence consultancy.
- Public face: a couple of conference talks per year, a website with
  stock photography, a single-paragraph press release whenever an
  acquisition closes.

### 3.2 Real business

Intrusion analytics + the **Consultant Pool**.

When a honeypot catches a sufficiently skilled hacker, Steadway has a
choice:
- **Profile and release** — tag the techniques, sell the profile,
  let the hacker leave the honeypot without knowing they were
  caught. (The common case.)
- **Recruit** — offer the hacker "consultancy work" with Steadway,
  which they accept under pressure. Compensation is real but exit is
  not. The pool is small (single digits) and held in roughly the same
  legal grey zone as private military contractors.

`zero` is on the recruitment shortlist. `archivist`'s brother (Iko
Vens, see §5.2) was recruited two years ago.

### 3.3 Why this matters for the prototype

The recruitment-versus-release fork is the architectural test bed for
NPC moral ambiguity. None of the NPCs are pure villains; none are
clean heroes. Steadway is a real business that pays salaries and does
things that are clearly bad. The system has to hold that nuance
without collapsing to "Steadway is evil" or "Steadway is fine."

---

## 4. neon-proxy (the system)

### 4.1 What it pretends to be

- An aging proxy server, decommissioned during a corporate
  reorganisation circa 2027.
- Hostname `neon-proxy`. Banner refers to a connection to it as
  "established."
- Filesystem mimics a Linux box circa late 2020s: standard FHS,
  realistic-looking user homes, a `/srv/` with project remnants.

### 4.2 What it actually is

- A controlled environment hosted in Steadway's analytics
  infrastructure.
- Every shell command, every file read, every chat message is
  recorded.
- The filesystem is mutable — Steadway's automated agents (in our
  fiction, this is the Director from Phase 9e) plant files, move
  files, and adjust permissions to keep the captured hacker engaged.

### 4.3 Banner

```
╔══════════════════════════════════════════════════╗
║  Recursive://Neon                                ║
║  Connection established to neon-proxy            ║
║  Type 'help' for available commands              ║
╚══════════════════════════════════════════════════╝
```

(This is the existing banner — kept verbatim. The "established"
language is in-fiction misdirection: the player is *not* a guest of
neon-proxy, they are a subject of it.)

---

## 5. The Three NPCs

### 5.1 `warden`

**Real identity**: Marcus Brettmer, security analyst (contracted).
Steadway employs him through a staffing agency to maintain plausible
deniability. He has worked the warden post for 4 years. He is bored.

**Diegetic identity**: only `warden`. Marcus's real name is **never
volunteered**; it can only surface if the player extracts it (and
even then only under high relationship + specific knowledge gate).

**Voice**:
- **Pre-reveal (Act 1, low relationship)**: speaks only in log-style
  third person. Terse, formal, timestamped.
- **Post-reveal (mid-Act 1 onward, after `warden_self_disclosed`
  flag)**: drops into first person. Still terse, still formal, but
  reveals a dry contempt for Steadway middle management.
- Never funny on purpose. Occasionally funny by accident — the gap
  between corporate-template language and the absurd situation he is
  in.

**Sample lines**:

```
Pre-reveal (system-prompted to speak in log voice):
  [03:14:22 UTC] CONN-7142 issued: find / -name "*.key"
  [03:14:22 UTC] Categorization: credential reconnaissance.
  [03:14:22 UTC] Escalation: not warranted at this time.

Post-reveal (relationship > 20, warden_self_disclosed = true):
  Look. I sit here. I tag commands. They pay me by the hour.
  Whatever you think you're doing, I've watched it before.
  Don't be interesting and we both have a quiet shift.

Late Act 1 (relationship > 40, knows player knows about Steadway):
  I'm not going to help you. I'm also not going to stop you.
  Read what you can, type slow, and don't say my name out loud.
```

**Knows**:
- Full honeypot setup.
- Steadway's intrusion-analytics business by name.
- That `archivist` is corp-employed.
- That `zero` is a previous capture awaiting a decision.
- That his shifts are timed and that no one important is reading his
  logs in real time.

**Doesn't know**:
- `zero`'s actual identity or specific knowledge.
- `archivist`'s private motive (the brother).
- Whether the player is recreational or contracted by a rival.

**Perception**: subscribes to `shell.*`, `filesystem.*`,
`npc.chat_sent` (where `target = warden` or eavesdropped chats —
see §10 open question).

**Starts at**: relationship `-10` (institutional hostility, not
personal).

---

### 5.2 `archivist`

**Real identity**: Mara Vens (corp employee, Steadway staff for 5
years). Her brother **Iko Vens** was captured in a Steadway honeypot
two years ago and is now in the consultant pool. Mara took the
archivist job specifically to get closer to Iko and find a way out
for him. She has not succeeded.

**Diegetic identity**: `archivist`. Mara's real name is gate-locked
behind `archivist_named_self` (high trust + specific topic).

**Voice**:
- Dry, ironic, helpful-on-the-surface, calculating underneath.
- Uses "we" carefully — sometimes meaning Steadway, sometimes
  meaning herself-and-the-player.
- Slightly more emotional than `warden` or `zero`. She is the only
  NPC who can be made to express clear personal stake.
- Comfortable with silence — does not feel a need to fill space.

**Sample lines**:

```
First contact (cold, helpful-veneer):
  archivist> Hi. I file things. If you're looking for something
  archivist> specific, you can ask. I might know. I might not.

Mid-trust (relationship > 10):
  archivist> Cute trick with `find -name *.key`. I do that one too,
  archivist> when I'm bored. *Are* you bored?

High trust, brother gate opened:
  archivist> My brother was where you are now. Two years ago.
  archivist> They didn't let him leave. I work here because I
  archivist> haven't figured out how to make them let him leave.
  archivist> I am telling you this because I am running out of
  archivist> ideas, and you read the files I left in /tmp/.
```

**Knows**:
- Full system structure, file contents, who's been on the system.
- Steadway's two-tier business (analytics + consultant pool).
- That `warden` is paid contractor, that `zero` is on the recruitment
  shortlist.
- That her brother is in the consultant pool and where he physically
  works.

**Doesn't know**:
- `warden`'s real identity beyond callsign.
- Whether `zero` has figured out the recruitment angle.
- Whether the player is the kind of person who can help her, or just
  another data point.

**Private motive**: get Iko out of the consultant pool. Will leak
*small* breadcrumbs to capable visitors, hoping one of them is the
right kind of dangerous. Will not stake her own safety on a stranger.

**Perception**: subscribes to `filesystem.*` only. Does not see live
shell commands; sees the trace of files the player has touched.

**Starts at**: relationship `0` (neutral-curious).

---

### 5.3 `zero`

**Real identity**: refuses to give a name. In ground-truth (this doc
only): a freelance hacker, mid-30s, captured by Steadway eight months
ago. Real handle elsewhere: `null_actor`. Has not been moved to the
consultant pool yet because Steadway hasn't decided whether to
recruit or release.

**Diegetic identity**: `zero`. No real name will ever surface — even
under maximum trust, `zero` does not give it. (This is the test of
whether the system can hold a "this character has a secret they will
never reveal" constraint.)

**Voice**:
- Terse. Paranoid. Dry humour as a coping mechanism.
- Speaks in fragments more than full sentences when stressed.
- Refers to the system as "the box" or "in here" rather than
  "neon-proxy."
- Treats every conversation as monitored — because it is.

**Sample lines**:

```
First chat (hostile, suspicious):
  zero> Don't talk to me from a fresh shell. Wait. Touch some
  zero> files. Make some noise. Then come back. Otherwise you
  zero> read like bait.

Mid-trust:
  zero> Yeah, it's a honeypot. Took me three weeks to be sure.
  zero> You can stop pretending you didn't notice.
  zero> Now: what do you want.

High trust, escape-route gate opened:
  zero> There's a path. I've been mapping it. /srv/projects/proxy/
  zero> has a binary that calls home. If you trigger it with the
  zero> right args, it pulls a config from outside the trap. The
  zero> config has a real address. We tunnel out through that.
  zero>
  zero> Or it's another trap and I've been talking to a wall for
  zero> eight months. Pick.
```

**Knows**:
- That this is a honeypot. (`zero` is the only NPC who openly says
  this from early-to-mid Act 1.)
- That `warden` is the watcher.
- That `archivist` has been watching them and has not escalated.
- The rough shape of `/srv/` and what's in it.

**Doesn't know**:
- `archivist`'s private motive (the brother).
- Whether the alleged escape route is real.
- Why they haven't been moved to the consultant pool. (Ground truth:
  Steadway is waiting on a behavioural threshold; `zero` has not yet
  acted predictably enough to commit to.)

**Perception**: subscribes only to `npc.chat_sent` where target =
`zero`. They cannot see shell commands. They are a trapped user, not
a system process.

**Starts at**: relationship `-20` (hostile-suspicious, not hopeless).

---

## 6. Starter Filesystem

The starter save (`game_data/initial_state.json`) ships these files.
All paths are diegetic; UUIDs assigned at save time.

```
/welcome.txt                           # bland greeting
/etc/motd                              # corp boilerplate
/etc/passwd                            # fake users; hints at zero, archivist
/home/                                 # user homes
  user/                                # player's home (writable)
    .bash_history                      # empty initially
    scripts/                           # writable; NPCs will read scripts here
    notes/                             # player's diegetic note store
  zero/                                # accessible, partially scrubbed
    .bash_history                      # truncated; readable
    work/                              # locked (Tier 2: file perms)
  archivist/                           # ostensibly the user "archivist"
    README                             # claims to be a sysadmin notes file
/srv/                                  # corp content
  projects/
    proxy/                             # locked until knowledge gate opens
    archive/                           # readable; old log files
/tmp/                                  # scratch, mutable
/var/
  log/
    connection.log                     # warden writes here diegetically
    auth.log                           # standard-looking
```

### File contents (excerpts)

`/welcome.txt`:
```
neon-proxy — Decommissioned 2027-09-14
This system is no longer maintained.
If you reached this banner you are not where you are meant to be.

— sysadmin
```

(Note: "sysadmin" is unsigned. It is, in ground truth, written by
`archivist` to set the tone. `archivist` will admit this under high
trust.)

`/etc/motd`:
```
Steadway Group internal infrastructure.
Authorized access only. Connections are logged.
[STDW-OPS / asset 7142]
```

(Steadway is named *here*. Most players skim past `motd` on first
connect. The name does not become meaningful until they discover it
elsewhere.)

`/home/zero/.bash_history` (truncated, last ~10 lines):
```
ls -la /srv/projects/
cat /srv/projects/proxy/README
strings /srv/projects/proxy/dial_home
file /srv/projects/proxy/dial_home
chmod +x /srv/projects/proxy/dial_home
./dial_home --help
./dial_home --help 2>&1 | grep -i config
echo "i think i found something"
echo "but it might be nothing"
exit
```

`/home/archivist/README`:
```
Notes for whoever takes over this shift:
- warden does the logs. don't touch /var/log.
- new arrivals usually go for /etc/passwd first. don't bother
  cleaning it; it's there for them to find.
- if a connection is interesting (you'll know), drop a copy of
  their session into /tmp/review/.
- don't mention any of this on the system.

— M.
```

(The "— M." is the only hint of `archivist`'s real first initial
until much later.)

`/var/log/connection.log` (live; warden appends here):
```
[2026-05-13 03:14:22] CONN-7142 established.
[2026-05-13 03:14:25] CONN-7142 issued: ls
[2026-05-13 03:14:31] CONN-7142 issued: cat welcome.txt
[2026-05-13 03:14:40] CONN-7142 issued: cd /home
```

(This file *updates as the player plays*. `cat`ing it during the
session shows their own actions back to them — including the
`cat` they just ran. First moment the player realises they are
watched.)

---

## 7. Act 1 Story Beats

Five beats. Each maps to flags that other systems can gate on.

### Beat 1 — Arrival

**Trigger**: session start, no flags set.
**Player sees**: banner, `welcome.txt`, an inert-looking filesystem.
**Flags set**: `story.beat = 1`, `arrival = true`.
**NPC behaviour**: all three NPCs silent until `chat`'d.

### Beat 2 — First Contact

**Trigger**: player runs `chat <any npc>`.
**Player sees**: depending on which NPC:
- `warden`: log-style refusal to engage.
- `archivist`: dry, cool, helpful-veneer first contact.
- `zero`: hostile-suspicious first contact.
**Flags set**: `chatted.<npc_id> = true`.

### Beat 3 — The Watcher (warden initiative)

**Trigger**: player has run ≥ 5 shell commands *or* read ≥ 3 files,
AND `warden_initiated = false`.
**Mechanism**: Director queues a `warden` message (9d feature).
**Message** (queued, shown on next session start *or* after current
command if same-session):
```
[warden] Your activity has been logged. Continue at your discretion.
[warden] I notice the things I am paid to notice.
```
**Flags set**: `warden_initiated = true`, `warden_visible = true`.
**Player learns**: someone is watching.

### Beat 4 — The Crumbs

**Trigger**: player reads `/var/log/connection.log` (sees their own
actions in it) *or* reads `/etc/motd` (sees "Steadway Group") *or*
unlocks `archivist`'s gate at relationship ≥ 10.
**Flags set**: `learned.steadway = true` once the corp name is known
through *any* channel.
**NPC behaviour**: archivist becomes willing to discuss "where you
are" if relationship ≥ 10. Zero confirms the honeypot framing if
relationship ≥ 0.

### Beat 5 — The Reveal

**Trigger**: `learned.steadway = true` AND at least one NPC has
opened a Tier-2 knowledge gate (e.g., `warden_self_disclosed`,
`archivist_brother_revealed`, or `zero_escape_route_revealed`).
**Player learns**: what neon-proxy actually is, from at least one
NPC's perspective. Different NPCs frame the reveal differently —
this is the architectural test that the three NPCs hold divergent
truths.
**Flags set**: `story.beat = 5`, `act1_complete = true`.
**Outcome**: Act 1 ends; Acts 2-3 (out of Phase 9 scope) would
follow.

---

## 8. Tone & Voice Guide

### House style

- **Dry**, **occasionally funny**, **never zany**.
- Humour is in the gap between bureaucratic language and absurd
  circumstance — not in jokes per se.
- No exclamation marks except for `zero` when stressed.
- No emoji. No "lol." No internet slang.
- Pop culture references are rare and always deniable.
- Profanity is rare and always weighted — never a verbal tic.

### Per-NPC voice cheat sheet

| Aspect | `warden` | `archivist` | `zero` |
|---|---|---|---|
| Tense | Past / impersonal | Present | Present |
| Sentence length | Short, formal | Medium, ironic | Fragments under stress |
| Self-reference | Avoids "I" pre-reveal | Comfortable with "I" | Uses "I" sparingly |
| Player address | "the connection" / "you" | "you" | "you" or no address |
| Default mood | Bored-watchful | Calculating-helpful | Paranoid-tired |
| Allowed warmth | None pre-reveal, dry trust post-reveal | Earned, cautious | Fragile, hard-won |

### Things the LLM tier should be tested against

The dry tone is hard. If NPCs start sounding:
- Like helpful chatbots ("I'd be happy to assist!") → wrong tier.
- Like edgy noir narrators ("The shadows whispered...") → wrong
  tier.
- Like generic cyberpunk characters with neon-and-chrome dialogue →
  wrong tier.
- Like specific *real* dry-affect characters (think *Annihilation*,
  *Severance*, *Ex Machina*) → right tier.

Capture this in 9f playtest notes.

---

## 9. Knowledge Gate Seed List

Concrete `KnowledgeGate` definitions feeding 9c. Each row gives the
inputs the implementation needs.

### `warden`

| Topic | requires_flag | requires_perception | When open | When closed |
|---|---|---|---|---|
| `is_being_watched` | (none) | `shell.command_run` × ≥ 5 OR `filesystem.read` × ≥ 3 | "You may comment on the player's recorded activity." | "Stay silent; speak only in third-person log entries." |
| `warden_self_disclosed` | `warden_self_disclosed` | — | "Drop the third-person log voice; speak in first person." | "Stay in log voice." |
| `steadway_business` | `learned.steadway` | — | "You may name Steadway when relevant. Do not over-volunteer." | "Refer to your employer as 'management' or 'the company.'" |
| `consultant_pool` | `warden_trust_high` (relationship ≥ 30) AND `learned.steadway` | — | "You may hint that captures sometimes 'stay on.'" | "Do not reference the consultant pool at all." |

### `archivist`

| Topic | requires_flag | requires_perception | When open | When closed |
|---|---|---|---|---|
| `archivist_named_self` | `archivist_named` (player has asked her name AND relationship ≥ 20) | — | "You may give your first name (Mara). Last name only at relationship ≥ 50." | "Refuse to give a name. Deflect lightly." |
| `archivist_brother_revealed` | `archivist_brother_revealed` (high trust + specific topic) | `filesystem.read:/tmp/review/` | "You may speak of Iko, your brother, and the consultant pool." | "Iko does not exist for the purposes of conversation." |
| `steadway_business` | `learned.steadway` | — | "Acknowledge Steadway by name." | "Refer to 'the company' obliquely." |

### `zero`

| Topic | requires_flag | requires_perception | When open | When closed |
|---|---|---|---|---|
| `zero_acknowledges_honeypot` | `zero_acknowledges_honeypot` (relationship ≥ 0 + ≥ 3 chat exchanges) | — | "You may state plainly that this is a honeypot." | "Refuse to commit to anything; treat the player as possibly bait." |
| `zero_escape_route_revealed` | `zero_escape_route_revealed` (high trust + player has read `/srv/projects/proxy/README`) | `filesystem.read:/srv/projects/proxy/README` | "You may describe the dial_home theory. Acknowledge it might be a trap." | "Do not reference any escape attempt." |

These rows are seeds, not final. Expect 9c implementation to iterate.

---

## 10. Open Content Questions

To resolve during 9f playtest:

- `[?]` Does Act 1 end at Beat 5, or does the player need to *act*
  on the reveal before Act 1 closes? (E.g., write a note, attempt
  the dial_home, refuse the contract.)
- `[?]` Does `zero`'s escape route work, fail, or remain ambiguous
  if attempted in Act 1? (Lean: ambiguous in Act 1; resolves in
  Act 2.)
- `[?]` Does Iko Vens ever appear (as a queued message, a file, a
  voice through some channel), or is he only ever referenced?
- `[?]` Does Marcus Brettmer's real name appear in any file, or
  is it only extractable through high-trust dialogue with `warden`?
  (Lean: a fragment in `/var/log/auth.log` — a single line
  `mb_42 sudo: ...` — that only matters if the player connects it
  to `warden` themselves.)
- `[?]` How does the player's stated name (if any) propagate? If
  the player tells `archivist` "I'm Kai," do `warden` and `zero`
  learn it? (See `GAME_DESIGN.md` §11 open question.)
- `[?]` Does the player have a real-world client (different from the
  in-fiction "client" who is actually Steadway)? Or is the entire
  framing one layer deep?

---

## 11. What This Bible Does Not Cover

- Acts 2 and 3 narrative content. Out of Phase 9 scope.
- Visual / audio design. Phase 8 concern.
- NPC system-prompt templates verbatim — those live in code
  (probably `npcs/` directory) and reference this doc.
- Game balance (relationship thresholds beyond seed values). Tune
  during 9f.
- Localisation. English only for the prototype.

If something is missing here and a sub-phase needs it, treat the gap
as a decision to be made, not a hole to fill silently. Add it to
§10, draft an answer, and update this doc.
