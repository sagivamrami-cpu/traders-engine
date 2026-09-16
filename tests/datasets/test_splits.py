from datetime import UTC, datetime

from trading_system.datasets.splits import ChronologicalSplitBoundaries, assign_chronological_split


def boundaries():
    return ChronologicalSplitBoundaries(
        train_end=datetime(2026, 8, 28, 13, 32, tzinfo=UTC),
        validation_end=datetime(2026, 8, 28, 13, 34, tzinfo=UTC),
    )


def test_split_assignment_uses_time_boundaries():
    assert assign_chronological_split(datetime(2026, 8, 28, 13, 31, tzinfo=UTC), boundaries()) == "TRAIN"
    assert assign_chronological_split(datetime(2026, 8, 28, 13, 33, tzinfo=UTC), boundaries()) == "VALIDATION"
    assert assign_chronological_split(datetime(2026, 8, 28, 13, 35, tzinfo=UTC), boundaries()) == "TEST"


def test_split_assignment_is_independent_of_row_order():
    times = [
        datetime(2026, 8, 28, 13, 35, tzinfo=UTC),
        datetime(2026, 8, 28, 13, 31, tzinfo=UTC),
        datetime(2026, 8, 28, 13, 33, tzinfo=UTC),
    ]

    assert [assign_chronological_split(time, boundaries()) for time in times] == ["TEST", "TRAIN", "VALIDATION"]
