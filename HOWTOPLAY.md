# How to Play — Kernel Quest: The Memory Leak

You are a rogue process trying to survive inside a corrupted kernel. Descend through sectors of memory, evict the malware, and earn enough **bits** to upgrade your next process before the next crash.

---

## 1. Launching

```bash
python -m kernelquest.main
```

Or, on macOS, double-click `KernelQuest.app` (right-click → **Open** the first time, since the build is unsigned).

---

## 2. Main Menu

Use **↑ / ↓** (or **W / S**) to move, **Enter / Space** to confirm, **Esc** to go back.

| Option        | What it does                                                       |
| ------------- | ------------------------------------------------------------------ |
| New Run       | Start a fresh procedurally-generated run.                          |
| High Scores   | Top runs by score, then depth.                                     |
| Stats         | Lifetime stats: best run, average depth, deaths per malware type.  |
| Shop          | Spend `bits` on permanent upgrades that apply to future runs.      |
| Settings      | Adjust master volume and difficulty.                               |
| Quit          | Exit the game.                                                     |

---

## 3. In-Game Controls

| Key                           | Action                                                                 |
| ----------------------------- | ---------------------------------------------------------------------- |
| **W A S D** or **Arrow Keys** | Move one tile (or attack adjacent enemy by walking into it).           |
| **Space**                     | Wait one turn (skip your action; world still ticks).                   |
| **1 – 9**                     | Use cache item in slot N (RAM restore, cycle refund, scan boost, …).  |
| **Esc**                       | Self-terminate — instant Game Over (records as `Manual shutdown`).    |

The game is **turn-based**: time advances only when you act. Each action costs **1 CPU cycle**.

---

## 4. Reading the HUD

- **RAM bar** — your health. Color shifts to magenta as it drops. RAM ≤ 0 = crash.
- **CPU sine-wave** — live oscilloscope of cycles consumed per turn.
- **Sector** — current depth (0x00, 0x01, …). Deeper = more enemies, more loot.
- **Cache** — your inventory; numbered slots correspond to **1 – 9** keys.
- **Console log** — bottom feed: `[INFO]`, `[WARN]`, `[ERROR]`, `[CRIT]` events.
- **Fog of war** — only tiles within your scan radius are bright; explored tiles dim.

---

## 5. Entities

### Tiles

- **Empty** — walkable.
- **System Data** — wall; blocks movement and vision.
- **Bad Sector** — wall; same as above, just uglier.

### Items (spawn on the floor; step on them to pick up)

| Item               | Effect                                                |
| ------------------ | ----------------------------------------------------- |
| `GarbageCollector` | Restore RAM.                                          |
| `Optimization`     | Refund CPU cycles.                                    |
| `ScanBoost`        | Temporarily extend field-of-view (scan radius).       |

### Malware

| Enemy          | Behavior                                                                |
| -------------- | ----------------------------------------------------------------------- |
| `SyntaxError`  | Patrols/random walk. Easy fodder.                                       |
| `LogicBomb`    | Charges at you, detonates in an AoE when adjacent — back off or burst.  |
| `KernelPanic`  | Boss. Multi-phase, larger footprint, hits hard. Appears at depth.       |

---

## 6. Combat

- **Bump-to-attack**: walking into an adjacent enemy strikes it.
- Damage is applied immediately; dead enemies may drop loot into your **cache**.
- When **RAM ≤ 0**, the game records the killing malware as your `crash_cause`.

---

## 7. Game Over → Save Run

On death:

1. Type your handle (Backspace edits, Esc cancels).
2. Press **Enter** to save the run.
3. Your score, depth, seed, duration, and crash cause are persisted to the local SQLite DB.
4. **Bits** earned during the run are added to your meta-currency wallet.
5. You return to the main menu — spend bits in the **Shop** before your next run.

---

## 8. Meta-Progression (Shop)

In the **Shop** screen:

- **↑ / ↓** to browse upgrades, **Enter** to buy, **Esc** to leave.
- Upgrades are permanent and stack across runs (e.g. `+10 Starting RAM`, `+1 Starting Cycle`, `Wider Scan`).
- Costs scale with current upgrade level.

---

## 9. Settings

- **Volume** — master audio (0% – 100%).
- **Difficulty** — cycles between presets affecting enemy density and damage.

Use **← / →** (or **A / D**) to adjust the highlighted row, **Esc** to return.

---

## 10. Tips

- **Don't waste cycles.** Every move is a tick the world uses to hunt you.
- **Press Space to wait** — sometimes letting a `LogicBomb` walk past costs less RAM than fighting it.
- **Hoard `GarbageCollector`** items for boss floors.
- **Save bits for `Wider Scan`** early; seeing further is the single biggest survivability boost.
- Each run records its **seed** — share a seed with a friend to play the same dungeon.

---

Good luck, process. Stay resident.
