"""Merkezi sabitler ve ayarlanabilir değerler.

Sihirli sayıları oyun mantığından uzak tut - buradan içe aktar.
"""

from __future__ import annotations

from typing import Final

# --- Display ---
WINDOW_TITLE: Final[str] = "Kernel Quest: The Memory Leak"
WINDOW_WIDTH: Final[int] = 1280
WINDOW_HEIGHT: Final[int] = 720
FPS: Final[int] = 60

# --- Grid ---
GRID_WIDTH: Final[int] = 20
GRID_HEIGHT: Final[int] = 20
TILE_SIZE: Final[int] = 32

# --- Fog of War ---
DEFAULT_SCAN_RADIUS: Final[int] = 4

# --- Player defaults ---
PLAYER_START_RAM: Final[int] = 100
PLAYER_START_CPU_CYCLES: Final[int] = 5
PLAYER_CACHE_CAPACITY: Final[int] = 8
PLAYER_START_POSITION: Final[tuple[int, int]] = (1, 1)

# --- Combat ---
PLAYER_BASE_DAMAGE: Final[int] = 10
BAD_SECTOR_DAMAGE: Final[int] = 5

# --- Procedural generation ---
ROOM_MIN_SIZE: Final[int] = 4
ROOM_MAX_SIZE: Final[int] = 7
ROOM_MAX_ATTEMPTS: Final[int] = 30
BAD_SECTORS_PER_LEVEL: Final[int] = 3

# --- Enemies (per-class base stats) ---
SYNTAX_ERROR_HP: Final[int] = 8
SYNTAX_ERROR_DAMAGE: Final[int] = 4
LOGIC_BOMB_HP: Final[int] = 12
LOGIC_BOMB_DAMAGE: Final[int] = 18
LOGIC_BOMB_RADIUS: Final[int] = 1
KERNEL_PANIC_HP: Final[int] = 60
KERNEL_PANIC_DAMAGE: Final[int] = 12
KERNEL_PANIC_PHASE_THRESHOLD: Final[float] = 0.5

# --- Spawning per depth ---
ENEMIES_BASE_COUNT: Final[int] = 3
ITEMS_BASE_COUNT: Final[int] = 2
LOOT_DROP_CHANCE: Final[float] = 0.35
KERNEL_PANIC_DEPTH: Final[int] = 5

# --- Item effects ---
GC_HEAL_AMOUNT: Final[int] = 25
OPTIMIZATION_CYCLES: Final[int] = 3
SCAN_BOOST_TURNS: Final[int] = 5

# --- Score rewards ---
SCORE_PER_MOVE: Final[int] = 1
SCORE_PER_KILL_SYNTAX_ERROR: Final[int] = 25
SCORE_PER_KILL_LOGIC_BOMB: Final[int] = 50
SCORE_PER_KILL_KERNEL_PANIC: Final[int] = 250
SCORE_PER_DESCENT: Final[int] = 100

# --- Persistence ---
DATABASE_FILENAME: Final[str] = "database.db"

# --- Game-over name input ---
PLAYER_NAME_MAX_LENGTH: Final[int] = 16

# --- Console log ---
CONSOLE_LOG_CAPACITY: Final[int] = 6

# --- Fog of war ---
SCAN_BOOST_RADIUS_BONUS: Final[int] = 3

# --- Juice / FX ---
SCREEN_SHAKE_DAMAGE_INTENSITY: Final[int] = 6
SCREEN_SHAKE_KILL_INTENSITY: Final[int] = 4
SCREEN_SHAKE_DECAY: Final[float] = 0.85
PARTICLE_LIFETIME_FRAMES: Final[int] = 24
HUD_CPU_WAVE_WIDTH: Final[int] = 232
HUD_CPU_WAVE_HEIGHT: Final[int] = 28
HUD_MINIMAP_TILE: Final[int] = 6

# --- Audio ---
AUDIO_SAMPLE_RATE: Final[int] = 22050
