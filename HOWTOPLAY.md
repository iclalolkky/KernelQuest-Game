# How to Play — Kernel Quest: The Memory Leak

You are a rogue process trying to survive inside a corrupted kernel. Descend through sectors of memory, evict the malware, stack **Programs**, **Daemons**, and **Patch Notes**, and earn enough **bits** to upgrade your next process before the next crash.

> First time? Pick **Tutorial** from the main menu — a guided sector walks you through every mechanic in seven steps. The first launch routes you there automatically.

---

## 1. Launching

```bash
python -m kernelquest.main
```

Or, on macOS, double-click `KernelQuest.app` (right-click → **Open** the first time, since the build is unsigned).

---

## 2. Main Menu

The default main menu is a **Boot Map**: `init(0)` walks between labelled kiosks
along the bottom of the screen. Use **← / →** to move, **Enter / Space** to
activate the closest kiosk, **Tab** to jump to the next kiosk, and **Esc** to
quit. Prefer the original keyboard list? Toggle Settings → "Main Menu Layout"
to **Classic**.

The top-level menu collapses six entries into terminal-style hubs:

| Kiosk      | Tabs                                                                  |
| ---------- | --------------------------------------------------------------------- |
| Launch     | New Run · Daily Run                                                   |
| Manual     | Tutorial · How to Play · Codex                                        |
| Records    | High Scores · Daily Board · Stats · Bestiary                          |
| Shop       | Spend `bits` on permanent upgrades.                                   |
| Settings   | Audio, theme, layout, accessibility, key glyphs.                      |
| Quit       | Halt the kernel.                                                      |

Inside any hub, **Tab / ← / →** cycle tabs, **1..n** jump directly, **Enter**
opens the focused entry, **Esc** returns to the main menu.

> **Dev menu.** Launch with `KQ_DEV=1` set in the environment to expose a
> hidden **Boss Test Range** kiosk. The dev range never writes to your
> `runs`, `scores`, or `bits`.

---

## 3. In-Game Controls

| Key                           | Action                                                                  |
| ----------------------------- | ----------------------------------------------------------------------- |
| **W A S D** or **Arrow Keys** | Move one tile (or attack adjacent enemy by walking into it).            |
| **Space**                     | Wait one turn (skip your action; world still ticks).                    |
| **1 – 9**                     | Use cache item in slot N (RAM restore, cycle refund, scan boost, …).    |
| **Q / E / R**                 | Cast the Program in loadout slot 1 / 2 / 3 (`fork()`, `kill -9`, …).    |
| **? / / / F1**                | Toggle the in-game **help overlay** (full controls cheat-sheet).        |
| **F11**                       | Toggle fullscreen.                                                      |
| **M**                         | Toggle mute (persisted across sessions).                                |
| **Esc**                       | Self-terminate — instant Game Over (records as `Manual shutdown`).      |

The game is **turn-based**: time advances only when you act. Each action costs **1 CPU cycle**.

A mini help-bar at the bottom of the screen always lists the 4–5 most relevant keys for your current state.

---

## 4. Reading the HUD

- **RAM bar** — your health. Color shifts to magenta as it drops. RAM ≤ 0 = crash.
- **CPU sine-wave** — live oscilloscope of cycles consumed per turn.
- **Score** — comma-separated readout. **+score** floating numbers pop on every kill / pickup.
- **Multiplier widget** — Balatro-style chain bonus (e.g. `× 4.20`) that grows on consecutive kills/pickups and breaks on damage taken or ~3 idle turns.
- **Sector** — current depth (0x00, 0x01, …). Deeper = more enemies, more loot.
- **Cache** — your inventory; numbered slots correspond to **1 – 9** keys.
- **Loadout bar** — your equipped Programs in slots **Q / E / R**.
- **Daemon strip** — up to 5 equipped passives with synergy tag chips.
- **Patch chips** — Patch Notes you've taken this run.
- **Console log** — bottom feed: `[INFO]`, `[WARN]`, `[ERROR]`, `[CRIT]` events.
- **Fog of war** — only tiles within your scan radius are bright; explored tiles dim.

---

## 5. Entities

### Tiles

- **Empty** — walkable.
- **System Data** — wall; blocks movement and vision.
- **Bad Sector** — wall; same as above, just uglier.
- **Exit** — descend to the next sector. **Locked while a boss is alive.**

### Items (spawn on the floor; step on them to pick up)

| Item               | Effect                                                |
| ------------------ | ----------------------------------------------------- |
| `GarbageCollector` | Restore RAM.                                          |
| `Optimization`     | Refund CPU cycles.                                    |
| `ScanBoost`        | Temporarily extend field-of-view (scan radius).       |

### Malware

| Enemy            | Behavior                                                                       |
| ---------------- | ------------------------------------------------------------------------------ |
| `SyntaxError`    | Patrols/random walk. Easy fodder.                                              |
| `LogicBomb`      | Charges at you, detonates in an AoE when adjacent — back off or burst.         |
| `ZombieProcess`  | Elite. Revives once after death.                                               |
| `KernelPanic`    | **Boss.** Multi-phase, larger footprint, hits hard. **Locks the EXIT.**        |
| `SegFault`       | **Boss.** Teleports, splits the grid into halves. **Locks the EXIT.**          |

When a boss spawns: a flashing red banner appears, the BGM swaps to a dedicated boss track, a screen-glitch overlay kicks in, and a full-width red HP bar pins to the top of the screen until the boss dies. Walking onto the EXIT while a boss is alive is rejected with a `[CRIT] EXIT LOCKED` log line.

---

## 6. Programs (active abilities)

Programs are card-like cooldown abilities slotted into your loadout (**Q / E / R**). Each costs CPU cycles and may have charges.

| Program     | Effect                                                                |
| ----------- | --------------------------------------------------------------------- |
| `fork()`    | Spawn a 1-turn decoy clone that draws aggro.                          |
| `kill -9`   | Instakill a non-boss adjacent enemy. Large cycle cost.                |
| `sudo`      | Next attack deals 3× damage.                                          |
| `grep`      | Reveal the whole sector for 1 turn.                                   |
| `nice`      | Skip enemy turns for 2 turns.                                         |
| `nohup`     | Negate the next damage you would take.                                |
| `chmod +x`  | Permanently empower one Program slot.                                 |

---

## 7. Daemons (passive modifiers)

Daemons are passive processes you keep equipped (up to 5 at once). They tag with synergies — `arithmetic`, `io`, `network`, `memory`, `signal` — and stacking shared tags triggers combo bonuses.

| Daemon       | Effect                                                                   |
| ------------ | ------------------------------------------------------------------------ |
| `cron`       | Every 10 turns, restore 5 RAM.                                           |
| `swapd`      | Convert overflow RAM into bonus score on pickup.                         |
| `oom-killer` | When RAM < 20%, deal AoE damage to nearby enemies.                       |
| `tcpdump`    | See enemy intent arrows.                                                 |
| `niced`      | +1 cycle per turn while no enemy is in FoV.                              |

Bosses drop a **guaranteed** Daemon on death.

---

## 8. Patch Notes (run modifiers)

Between sectors, you're offered a choice of **3 Patch cards** — pick one. The catalog has 20 cards including:

- `kernel-bypass` — extra damage to bosses.
- `dark-mode` — reduce field-of-view but boost score multiplier.
- `swap-thrash` — double item drops, half RAM regen.
- `root-kit` — start each new sector with bonus RAM.
- `page-fault` — every action costs RAM; everything else hits harder.
- `lazy-eval`, `noatime`, `thermal-throttle`, `stack-trace`, `zero-copy`, `ddos`, `heap-spray`, `opportunistic`, `fragmented`, …

Picked patches persist for the whole run and render as small chips in the HUD.

---

## 9. Combo / chain scoring

Score is `base × multiplier`. The multiplier ticks up on consecutive turns where you **kill** or **pick up loot**. It pops and scales when it grows. It breaks when:

- you take damage, or
- you stand idle for ~3 turns.

---

## 10. Combat

- **Bump-to-attack**: walking into an adjacent enemy strikes it.
- Damage is applied immediately; dead enemies may drop loot into your **cache**.
- Boss damage scales with `kernel-bypass` and other relevant patches.
- When **RAM ≤ 0**, the game records the killing malware as your `crash_cause`.

---

## 11. Game Over → Save Run

On death:

1. Type your handle (Backspace edits, Esc cancels).
2. Press **Enter** to save the run.
3. Your score, depth, seed, duration, and crash cause are persisted to the local SQLite DB (and to the daily board if you were on a daily seed).
4. **Bits** earned during the run are added to your meta-currency wallet.
5. You return to the main menu — spend bits in the **Shop** before your next run.

> **Graceful shutdown vs. core dump.** If you abort a run via the in-game pause
> menu (`SIGINT`), the engine logs `[init] graceful shutdown` and grants 25%
> of your would-be meta-bits. Dying outright still logs `[init] dumped core`
> and forfeits the bonus. Aborted runs do **not** unlock distros or lore.

### Sector ladder & cinematic transitions

- The right-hand HUD shows a **sector ladder** strip: 8 releases × 3 milestones
  with bosses marked. Press **L** for the fullscreen view with target scores.
- Each sector transition plays a short typewriter `cd /sector/0xNN/` cinematic
  (skippable with **Space**).
- Boss phase shifts trigger a `[KERNEL] !!! phase shift !!!` console banner,
  a hard flash, letterbox, and chroma tint.

---

## 12. Meta-Progression (Shop)

In the **Shop** screen:

- **↑ / ↓** to browse upgrades, **Enter** to buy, **Esc** to leave.
- Upgrades are permanent and stack across runs (e.g. `+10 Starting RAM`, `+1 Starting Cycle`, `Wider Scan`, `+Damage`, `+Cache slots`).
- Costs scale with current upgrade level.

---

## 13. Settings

Each row scrolls with **↑ / ↓**, adjust with **← / → / Enter / Space**, save & exit with **Esc**.

| Row          | Notes                                                                  |
| ------------ | ---------------------------------------------------------------------- |
| Music        | Background music volume (0% – 100%).                                   |
| SFX          | Sound-effect volume (0% – 100%).                                       |
| Mute         | Master mute (also bound to **M** in-game).                             |
| Difficulty   | `EASY` / `NORMAL` / `HARD` — scales player and enemy damage.           |
| Theme        | `Kernel` / `Phosphor Green` / `Amber CRT` / `High Contrast`.           |
| Fullscreen   | Also toggleable in-game with **F11**.                                  |
| UI scale     | 0.75× – 1.5× for hi-DPI displays.                                      |
| Reduce motion| Disables screen shake and particle pops.                               |
| CRT          | Toggle CRT scanline overlay.                                           |
| Large text   | Bumps every font size by +25%.                                         |

All settings persist in the `meta` table.

---

## 14. Tips

- **Don't waste cycles.** Every move is a tick the world uses to hunt you.
- **Press Space to wait** — sometimes letting a `LogicBomb` walk past costs less RAM than fighting it.
- **Hoard `GarbageCollector`** items for boss floors — the EXIT is locked until the boss dies.
- **Pair your daemons by tag.** Three `signal` daemons together scale much harder than three random ones.
- **Save `kill -9` for elites** like `ZombieProcess` so they can't revive.
- **`grep` before bosses** — knowing the room layout decides the fight.
- **Daily seed** is shared with everyone today; perfect for comparing scores.
- **Save bits for `Wider Scan`** early; seeing further is the single biggest survivability boost.
- Each run records its **seed** — share a seed with a friend to play the same dungeon.

---

## 15. Distros & Structured Runs (Phase 11)

Selecting **New Run** now opens the **Distro Select** screen instead of dropping you directly into a sector. Pick the build that fits the run you want.

- The run is laid out as **8 Releases × 3 Milestones** (Sector A → Sector B → Boss). Each milestone has a **target score** you must hit before exiting.
- After every cleared milestone, the **Vendor** opens so you can spend in-run `bits` on Programs, Daemons, Patches, or a reroll.
- You may **Skip** non-boss milestones from the result screen — you forfeit that milestone's score and vendor visit but earn a one-shot **Skip Tag** (free vendor, double bits, +1 daemon slot, or +score boost).
- A run is **successful** only when you clear all 8 Releases. Only successful runs bank `bits` to the meta shop and unlock the next Distro in the chain. A failed run is recorded for stats but yields no meta progress.
- Six starter Distros unlock sequentially: `Vanilla → Minimal → Hardened → Realtime → Bleeding-Edge → Recovery`.

## 16. Language / Dil

The game supports **English** and **Türkçe**. Open **Settings → Language** and press **←/→** to switch; the change is immediate and is persisted between launches.

Oyun **İngilizce** ve **Türkçe** dillerini destekler. **Ayarlar → Dil** menüsünden **←/→** tuşlarıyla anında değiştirebilirsiniz; tercih kalıcı olarak kaydedilir.

---

Good luck, process. Stay resident.
