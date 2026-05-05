# Kernel Quest — Lore Bible

> Source of truth for every user-facing string in **Kernel Quest: The Memory Leak**.
> Anything written for menus, tutorials, console-log voices, codex entries, or
> cutscenes must be consistent with the rules in this document.
>
> **Read order:** §1 premise → §2 timeline → §3 cast → §4 rules → §5 tone → §6 do/don't.

---

## 1. Premise

The machine is dying.

Somewhere deep in the kernel, a single misallocated page never came back. Cycle
after cycle, the leak grew, until the kernel — sentient, exhausted, running on
fumes — could no longer schedule anything but a panic. With its last clean
context switch the kernel forked one final process: **`init(0)`**, a recovery
init handcrafted from the last known-good snapshot.

The player *is* `init(0)`. Their job is to descend through the corrupted memory
sectors, purge the malware processes that mutated out of leftover heap, and
reach **`/proc/1`** before the leak — now self-aware as **`THE_LEAK`** —
consumes the last megabyte of free RAM.

> **One-line pitch:** "You are a recovery process trying to reach init before
> the memory leak does."

## 2. Internal timeline

| t (ms since boot) | event                                                           |
|-------------------|-----------------------------------------------------------------|
| 0                 | kernel boots, all daemons green                                 |
| 14 700 000        | first malloc without a free — the leak is born                  |
| 31 200 000        | leak achieves recursion; corrupted segments spawn `SyntaxError` |
| 41 800 000        | OOM-killer fired, missed the real culprit, killed itself        |
| 49 999 998        | kernel panics, forks `init(0)` from snapshot                    |
| 49 999 999        | game starts                                                     |

Every "sector" the player descends through is one logical page of RAM, deeper
in the address space than the last. Bosses live at page boundaries.

## 3. Cast

### 3.1 `init(0)` — protagonist
- **Role:** recovery init, restored from snapshot. Player avatar.
- **Voice:** terse, sysadmin-y, dry humor. Uses imperative verbs.
- **Drives:** restore uptime; reach `/proc/1`; do not become the next leak.
- **Visual:** stylized process glyph — pulsing diamond core, four rotating I/O
  fins, faint cyan halo. Distinct silhouette versus every enemy at a glance.
- **Defeat line:** `init(0) dumped core — signal: <crash_cause>`.

### 3.2 `THE_LEAK` — antagonist
- **Role:** corrupted PID 0 fragment. Final boss of every run.
- **Voice:** fragmented, all-caps, glitchy. Speaks in malloc/realloc metaphors.
- **Mannerism:** never refers to itself with a pronoun, only `0xFFFF…`.
- **Sample line:** `[THE_LEAK] HEAP_GROWS. CYCLE_TAX_DUE.`

### 3.3 Supporting cast (vendor daemons / mentors)
- **`/sbin/cron`** — punctual, helpful, never small-talks. Mentor in the tutorial range.
- **`vendord`** — between-milestone shopkeeper. Speaks in invoice form.
- **`bashrc`** — tutorial narrator and hint daemon. Friendly, slightly nostalgic.
- **`/dev/null`** — silent witness; only ever logs `(eaten)` after the player loses an item.
- **`oom-killer`** — disgraced ex-daemon, neutral; gives ominous warnings.

## 4. Rules of the world

- The machine is **one** machine. No internet, no cloud — every metaphor stays
  inside a single OS.
- **Time is cycles.** Nothing is "seconds"; every duration is "cycles" or "turns".
- **Death is a core dump,** not a death. Reincarnation = re-fork from the last
  snapshot.
- **Items are real artifacts** of the OS: garbage collectors, scan-boost
  packets, optimization stubs. Never call them "potions".
- **Currency is `bits`.** Always lower-case. Never "coins" or "gold".
- **Magic does not exist.** Anything supernatural-feeling is just an
  undocumented syscall.

## 5. Tone

- **Voice:** cyber-noir meets sysadmin folklore. Imagine a man-page written
  while a server room is on fire.
- **Humor:** dry, comes from real-world Unix friction (permissions, segfaults,
  `rm -rf`). Never breaks the fourth wall.
- **Pacing:** every line under 80 columns. Every cutscene under 12 frames.
- **Color:** lean into terminal palettes (cyan/magenta/amber/green); never
  reference real-world colors that don't appear on a CRT.

## 6. Do / Don't list for writers

| ✅ Do                                              | ❌ Don't                              |
|-----------------------------------------------------|----------------------------------------|
| "init(0) dumped core — signal: SIGTERM"             | "You died."                            |
| "EXIT locked — terminate the boss process first."   | "The door is locked. Defeat the boss." |
| "+12 bits credited to /var/wallet."                 | "+12 gold."                            |
| "Heap fragmented. Combo broken."                    | "You lost your streak."                |
| "[KERNEL] Scheduler online."                        | "Welcome to the game!"                 |
| Reference real Unix concepts (fork, signal, mmap).  | Invent fake jargon ("zorptronic feed").|
| Lower-case `bits`, `daemon`, `cron`.                | Capitalize them mid-sentence.          |

## 7. Console-log voices

The console log is a real journald-style feed. Every story-relevant line is
spoken by exactly one of these voices, written before the message tag:

| Voice tag    | Speaker         | When to use                                         |
|--------------|-----------------|-----------------------------------------------------|
| `[KERNEL]`   | the kernel      | system-level events, boss spawns, exit unlocking    |
| `[init]`     | the player      | rare interjections (game-over line, true ending)    |
| `[THE_LEAK]` | the antagonist  | only during boss fights and the ending              |
| `[VENDOR]`   | `vendord`       | shop / between-milestone exchanges                  |
| `[CRON]`     | `/sbin/cron`    | tutorial / hint nudges                              |

Severity tags (`[INFO] / [WARN] / [ERROR] / [CRIT]`) still go in front of the
voice tag. Example:

```
[INFO]  [KERNEL] Sector 0x04 mapped.
[CRIT]  [THE_LEAK] HEAP_GROWS. CYCLE_TAX_DUE.
```

## 8. Naming consistency cheat-sheet

| Generic concept | In-world term                          |
|-----------------|----------------------------------------|
| Player          | `init(0)`                              |
| Health          | `RAM`                                  |
| Energy          | `cycles`                               |
| Inventory       | `cache`                                |
| Level           | `sector`                               |
| Death           | `core dump`                            |
| Quitting        | `SIGINT` / `manual exit`               |
| Save            | `snapshot`                             |
| Currency        | `bits`                                 |
| Shop            | `vendor` / `vendord`                   |
| Tutorial range  | `/dev/sandbox`                         |

When in doubt, **say it in `man`-page voice**.
