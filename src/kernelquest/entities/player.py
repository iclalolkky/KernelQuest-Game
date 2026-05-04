"""The player-controlled `Process`."""

from __future__ import annotations

from dataclasses import dataclass, field

from kernelquest.core.config import (
    PLAYER_CACHE_CAPACITY,
    PLAYER_START_CPU_CYCLES,
    PLAYER_START_POSITION,
    PLAYER_START_RAM,
)
from kernelquest.entities.entity import Entity
from kernelquest.world.grid import MemoryGrid


@dataclass
class Player(Entity):
    """The avatar exploring the memory grid.

    Attributes use OS-architecture metaphors:

    - ``ram``         — current health.
    - ``cpu_cycles``  — energy budget for actions this turn.
    - ``cache``       — inventory list of collected packets.
    - ``crash_cause`` — set when ``ram`` reaches zero.
    """

    position: tuple[int, int] = PLAYER_START_POSITION
    name: str = "process_0"
    max_ram: int = PLAYER_START_RAM
    ram: int = PLAYER_START_RAM
    max_cpu_cycles: int = PLAYER_START_CPU_CYCLES
    cpu_cycles: int = PLAYER_START_CPU_CYCLES
    cache_capacity: int = PLAYER_CACHE_CAPACITY
    cache: list[str] = field(default_factory=list)
    score: int = 0
    depth_reached: int = 1
    crash_cause: str | None = None
    scan_boost_turns: int = 0

    # ----- state queries -----

    @property
    def is_alive(self) -> bool:
        return self.ram > 0

    @property
    def has_scan_boost(self) -> bool:
        return self.scan_boost_turns > 0

    # ----- mutations -----

    def take_damage(self, amount: int, source: str) -> None:
        """Apply damage to RAM, recording the crash cause if fatal."""
        if amount < 0:
            raise ValueError("damage amount must be non-negative")
        self.ram = max(0, self.ram - amount)
        if self.ram == 0 and self.crash_cause is None:
            self.crash_cause = source

    def heal(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("heal amount must be non-negative")
        self.ram = min(self.max_ram, self.ram + amount)

    def grant_cycles(self, amount: int) -> None:
        """Add cycles to the current turn budget (capped at max)."""
        if amount < 0:
            raise ValueError("cycle amount must be non-negative")
        self.cpu_cycles = min(self.max_cpu_cycles, self.cpu_cycles + amount)

    def grant_scan_boost(self, turns: int) -> None:
        """Stack additional scan-boost turns onto the player."""
        if turns < 0:
            raise ValueError("turns must be non-negative")
        self.scan_boost_turns += turns

    def tick_status_effects(self) -> None:
        """Decrement timed status effects by one turn."""
        if self.scan_boost_turns > 0:
            self.scan_boost_turns -= 1

    def end_turn(self) -> None:
        """Refill CPU cycles for the next turn."""
        self.cpu_cycles = self.max_cpu_cycles

    def spend_cycle(self) -> bool:
        """Consume a single CPU cycle. Returns ``False`` if none available."""
        if not self.is_alive or self.cpu_cycles <= 0:
            return False
        self.cpu_cycles -= 1
        return True

    def try_move(self, dx: int, dy: int, grid: MemoryGrid) -> bool:
        """Attempt to move by `(dx, dy)`.

        Returns ``True`` if the move succeeded (and a cycle was spent),
        ``False`` if blocked (no cycle spent).
        """
        if not self.is_alive:
            return False
        if self.cpu_cycles <= 0:
            return False
        new_x = self.position[0] + dx
        new_y = self.position[1] + dy
        if not grid.is_walkable(new_x, new_y):
            return False
        self.position = (new_x, new_y)
        self.cpu_cycles -= 1
        return True

    def add_to_cache(self, item: str) -> bool:
        """Append `item` to the cache. Returns ``False`` if full."""
        if len(self.cache) >= self.cache_capacity:
            return False
        self.cache.append(item)
        return True
