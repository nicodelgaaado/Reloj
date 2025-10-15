"""Chronograph engine that wraps timekeeping with doubly circular linked lists."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from .linked_list import DoublyCircularLinkedList


@dataclass(frozen=True)
class HandState:
    """Represents a discrete step on a clock hand."""

    index: int
    angle_degrees: float


@dataclass(frozen=True)
class ChronographSnapshot:
    """Angles for each hand at a specific instant."""

    seconds_angle: float
    minutes_angle: float
    hours_angle: float


class HandRing:
    """Clock hand backed by a doubly circular linked list."""

    def __init__(self, positions: int, degrees_per_step: float) -> None:
        if positions <= 0:
            raise ValueError("positions must be positive.")
        self._positions = positions
        self._degrees_per_step = degrees_per_step
        self._ring = DoublyCircularLinkedList(
            HandState(index=i, angle_degrees=i * degrees_per_step) for i in range(positions)
        )
        self._current_index = 0

    @property
    def degrees_per_step(self) -> float:
        return self._degrees_per_step

    @property
    def current_index(self) -> int:
        return self._current_index

    @property
    def base_angle(self) -> float:
        return self._ring.current_value.angle_degrees

    def move_to_index(self, target_index: int) -> None:
        """Step along the ring to the desired index."""
        normalized_target = target_index % self._positions
        forward_steps = (normalized_target - self._current_index) % self._positions
        backward_steps = (self._current_index - normalized_target) % self._positions
        if forward_steps <= backward_steps:
            self._ring.step_forward(forward_steps)
        else:
            self._ring.step_backward(backward_steps)
        self._current_index = self._ring.current_value.index

    def angle_with_fraction(self, fraction: float) -> float:
        """Return the current angle plus a fractional progression."""
        clamped_fraction = max(0.0, min(1.0, fraction))
        return self.base_angle + (clamped_fraction * self._degrees_per_step)


class ChronographEngine:
    """Coordinates hour, minute, and second hands using circular linked lists."""

    def __init__(self, time_source: Callable[[], datetime] | None = None) -> None:
        self._time_source = time_source or datetime.now
        self._seconds_hand = HandRing(positions=60, degrees_per_step=6.0)
        self._minutes_hand = HandRing(positions=60, degrees_per_step=6.0)
        self._hours_hand = HandRing(positions=720, degrees_per_step=0.5)  # 12h * 60 minutes

    def set_time_source(self, time_source: Callable[[], datetime]) -> None:
        self._time_source = time_source

    def snapshot(self) -> ChronographSnapshot:
        """Produce the latest hand angles based on the time source."""
        now = self._time_source()

        seconds_float = now.second + now.microsecond / 1_000_000.0
        seconds_index = int(seconds_float) % 60
        seconds_fraction = seconds_float - seconds_index
        self._seconds_hand.move_to_index(seconds_index)
        seconds_angle = self._seconds_hand.angle_with_fraction(seconds_fraction)

        minutes_float = now.minute + seconds_float / 60.0
        minutes_index = int(minutes_float) % 60
        minutes_fraction = minutes_float - minutes_index
        self._minutes_hand.move_to_index(minutes_index)
        minutes_angle = self._minutes_hand.angle_with_fraction(minutes_fraction)

        total_minutes = (now.hour % 12) * 60 + minutes_float
        hours_index = int(total_minutes) % 720
        hours_fraction = total_minutes - hours_index
        self._hours_hand.move_to_index(hours_index)
        hours_angle = self._hours_hand.angle_with_fraction(hours_fraction)

        return ChronographSnapshot(
            seconds_angle=seconds_angle,
            minutes_angle=minutes_angle,
            hours_angle=hours_angle,
        )
