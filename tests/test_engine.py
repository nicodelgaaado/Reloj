from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta

import pytest

from reloj.engine import ChronographEngine


def _time_iterator(instants: list[datetime]) -> Iterator[datetime]:
    for instant in instants:
        yield instant


def test_snapshot_angles_match_expected_values() -> None:
    reference_time = datetime(2024, 1, 1, 3, 15, 30, 500_000)

    iterator = _time_iterator([reference_time])
    engine = ChronographEngine(time_source=lambda: next(iterator))

    snapshot = engine.snapshot()

    assert snapshot.seconds_angle == pytest.approx(183.0, abs=1e-6)
    assert snapshot.minutes_angle == pytest.approx(93.05, rel=1e-4)
    assert snapshot.hours_angle == pytest.approx(97.754166, rel=1e-4)


def test_snapshot_uses_linked_list_progression() -> None:
    base_time = datetime(2024, 1, 1, 10, 0, 0)
    instants = [
        base_time,
        base_time + timedelta(seconds=1),
        base_time + timedelta(seconds=60),
        base_time + timedelta(hours=1, minutes=5, seconds=45),
    ]

    iterator = _time_iterator(instants)
    engine = ChronographEngine(time_source=lambda: next(iterator))

    first = engine.snapshot()
    second = engine.snapshot()
    third = engine.snapshot()
    fourth = engine.snapshot()

    assert second.seconds_angle > first.seconds_angle
    assert third.minutes_angle > first.minutes_angle
    assert fourth.hours_angle > third.hours_angle
