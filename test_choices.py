"""Guard the new page's claim that the two integer-fill paths already disagree."""

from choices_data import measure_choices


def test_fractional_square_has_three_distinct_masks():
    data = measure_choices()
    square = next(case for case in data["cases"] if case["id"] == "square")
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
