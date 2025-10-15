"""Chronograph engine that wraps timekeeping with doubly circular linked lists."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
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

    MODE_CLOCK = "clock"
    MODE_STOPWATCH = "stopwatch"

    def __init__(self, time_source: Callable[[], datetime] | None = None) -> None:
        self._time_source = time_source or datetime.now
        self._seconds_hand = HandRing(positions=60, degrees_per_step=6.0)
        self._minutes_hand = HandRing(positions=60, degrees_per_step=6.0)
        self._hours_hand = HandRing(positions=720, degrees_per_step=0.5)  # 12h * 60 minutes
        self._mode: str = self.MODE_CLOCK
        self._stopwatch_running = False
        self._stopwatch_accumulated = timedelta()
        self._stopwatch_start_time: datetime | None = None

    @property
    def mode(self) -> str:
        return self._mode

    def set_time_source(self, time_source: Callable[[], datetime]) -> None:
        self._time_source = time_source

    def current_time(self) -> datetime:
        """Return the current time from the time source."""
        return self._time_source()

    def set_mode(self, mode: str) -> None:
        if mode not in {self.MODE_CLOCK, self.MODE_STOPWATCH}:
            raise ValueError("mode must be 'clock' or 'stopwatch'.")
        if self._mode == mode:
            return
        if mode == self.MODE_CLOCK:
            self._stopwatch_running = False
            self._stopwatch_start_time = None
        self._mode = mode

    def start_stopwatch(self) -> None:
        if self._mode != self.MODE_STOPWATCH:
            self.set_mode(self.MODE_STOPWATCH)
        if not self._stopwatch_running:
            self._stopwatch_running = True
            self._stopwatch_start_time = self.current_time()

    def stop_stopwatch(self) -> None:
        if not self._stopwatch_running:
            return
        now = self.current_time()
        if self._stopwatch_start_time is not None:
            self._stopwatch_accumulated += now - self._stopwatch_start_time
        self._stopwatch_running = False
        self._stopwatch_start_time = None

    def reset_stopwatch(self) -> None:
        self._stopwatch_accumulated = timedelta()
        if self._stopwatch_running:
            self._stopwatch_start_time = self.current_time()
        else:
            self._stopwatch_start_time = None

    def is_stopwatch_running(self) -> bool:
        return self._stopwatch_running

    def stopwatch_elapsed(self) -> timedelta:
        elapsed = self._stopwatch_accumulated
        if self._stopwatch_running and self._stopwatch_start_time is not None:
            elapsed += self.current_time() - self._stopwatch_start_time
        return elapsed

    def snapshot(self) -> ChronographSnapshot:
        """Produce the latest hand angles based on the time source."""
        if self._mode == self.MODE_STOPWATCH:
            elapsed = self.stopwatch_elapsed()
            seconds_total = elapsed.total_seconds()
            seconds_float = seconds_total % 60.0
            seconds_index = int(seconds_float)
            seconds_fraction = seconds_float - seconds_index
            self._seconds_hand.move_to_index(seconds_index)
            seconds_angle = self._seconds_hand.angle_with_fraction(seconds_fraction)

            minutes_total = seconds_total / 60.0
            minutes_float = minutes_total % 60.0
            minutes_index = int(minutes_float)
            minutes_fraction = minutes_float - minutes_index
            self._minutes_hand.move_to_index(minutes_index)
            minutes_angle = self._minutes_hand.angle_with_fraction(minutes_fraction)

            total_minutes = minutes_total % 720.0  # keep within 12 hours
            hours_index = int(total_minutes)
            hours_fraction = total_minutes - hours_index
            self._hours_hand.move_to_index(hours_index)
            hours_angle = self._hours_hand.angle_with_fraction(hours_fraction)
        else:
            now = self.current_time()

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
