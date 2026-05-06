"""Grid tabanlı AI için BFS yol bulma yardımcıları."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from kernelquest.world.grid import MemoryGrid

Position = tuple[int, int]
_CARDINALS: tuple[Position, ...] = ((1, 0), (-1, 0), (0, 1), (0, -1))


def chebyshev_distance(a: Position, b: Position) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def manhattan_distance(a: Position, b: Position) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def bfs_next_step(
    grid: MemoryGrid,
    start: Position,
    goal: Position,
    blocked: Iterable[Position] = (),
) -> Position | None:
    """`start`'tan `goal`'a en kısa yol boyunca bir sonraki adımı döndür.

    `blocked` diğer varlıklar tarafından işgal edilen pozisyonların bir koleksiyonudur.
    Hedef kare kendisi `blocked`'de görünse bile **engellenmiş olarak kabul edilmez**
    (böylece bir düşman oyuncuyu hedefleyebilir, filtrelenmeden).
    """
    if start == goal:
        return None

    blocked_set = set(blocked)
    blocked_set.discard(goal)

    came_from: dict[Position, Position] = {}
    queue: deque[Position] = deque([start])
    visited: set[Position] = {start}

    while queue:
        current = queue.popleft()
        if current == goal:
            break
        for dx, dy in _CARDINALS:
            nx, ny = current[0] + dx, current[1] + dy
            neighbor = (nx, ny)
            if neighbor in visited:
                continue
            if not grid.is_walkable(nx, ny):
                continue
            if neighbor != goal and neighbor in blocked_set:
                continue
            visited.add(neighbor)
            came_from[neighbor] = current
            queue.append(neighbor)
    else:
        return None

    if goal not in came_from:
        return None

    # Walk back to the step adjacent to start.
    cursor = goal
    while came_from[cursor] != start:
        cursor = came_from[cursor]
    return cursor
