"""Daemon hooks — passive modifiers fire here based on game events."""

from __future__ import annotations

from kernelquest.entities.daemon import (
    DAEMON_CRON,
    DAEMON_NICED,
    DAEMON_OOM_KILLER,
    DAEMON_SWAPD,
    DAEMON_TCPDUMP,
    Daemon,
    synergy_count,
)
from kernelquest.entities.player import Player
from kernelquest.world.world import World


def is_equipped(player: Player, daemon: Daemon) -> bool:
    return daemon in player.daemons


def on_turn_end(world: World, turn_counter: int) -> list[str]:
    """Run periodic daemon effects. Returns log messages."""
    messages: list[str] = []
    player = world.player

    # cron — restore 5 RAM every 10 turns.
    if is_equipped(player, DAEMON_CRON) and turn_counter > 0 and turn_counter % 10 == 0:
        player.heal(5)
        messages.append("cron: +5 RAM restored.")

    # niced — +1 cycle per turn while no enemies in FoV.
    if is_equipped(player, DAEMON_NICED):
        in_fov = any(e.is_alive and e.position in world.visible for e in world.enemies)
        if not in_fov:
            player.grant_cycles(1)

    # Synergy: 2+ memory tag → +1 RAM regen per turn end.
    syn = synergy_count(player.daemons)
    if syn.get("memory", 0) >= 2:
        player.heal(1)

    return messages


def on_pickup(world: World) -> int:
    """Run pickup-time daemon effects. Returns bonus score."""
    player = world.player
    bonus = 0
    if is_equipped(player, DAEMON_SWAPD):
        bonus += max(1, player.combo_count) * 5
    syn = synergy_count(player.daemons)
    if syn.get("io", 0) >= 2:
        bonus += 10
    return bonus


def damage_multiplier_on_attack(player: Player) -> float:
    """Combined daemon-driven multiplier for a single player attack."""
    mult = 1.0
    if is_equipped(player, DAEMON_OOM_KILLER) and player.ram <= max(1, player.max_ram // 5):
        mult *= 1.5
    syn = synergy_count(player.daemons)
    if syn.get("signal", 0) >= 2:
        mult *= 1.15
    return mult


def reveals_through_fog(player: Player) -> bool:
    """Whether the player should see all enemies regardless of FoV."""
    return is_equipped(player, DAEMON_TCPDUMP)


__all__ = [
    "damage_multiplier_on_attack",
    "is_equipped",
    "on_pickup",
    "on_turn_end",
    "reveals_through_fog",
]
