"""Check distinct fill paths, existing export losses, and import-only regressions."""

import pytest

from choices_data import measure_choices


@pytest.fixture(scope="module")
def measured():
    return measure_choices()


def test_fractional_square_has_three_distinct_masks(measured):
    square = next(case for case in measured["cases"] if case["id"] == "square")
    sample = next(sample for sample in square["samples"] if sample["offset"] == 0.65)
    assert [sum(sample[key]) for key in ["coco", "supervision", "opencvTruncated"]] == [
        16,
        25,
        25,
    ]
    assert (
        sum(
            before != truncated
            for before, truncated in zip(
                sample["supervision"], sample["opencvTruncated"], strict=True
            )
        )
        == 18
    )


@pytest.mark.parametrize(
    "name,expected",
    [
        ("rectangle", [16, 16, 9, 16]),
        ("pixel", [1, 0, 0, 1]),
        ("hole", [32, 36, 25, 32]),
    ],
)
def test_export_losses_and_lossless_rle(measured, name, expected):
    case = next(case for case in measured["roundTrips"] if case["id"] == name)
    assert [
        sum(case[key]) for key in ["source", "supervision", "coco", "rle"]
    ] == expected
    assert case["source"] == case["rle"] == case["rleSupervision"]
    assert case["iscrowd"] == 0
    if name == "pixel":
        assert case["segmentation"] == []
        assert any(
            "returned no polygons" in warning for warning in case["exportWarnings"]
        )
