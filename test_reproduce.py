"""Regression checks for measured data and known rasterization differences."""

import json

import pytest

from reproduce import ROOT, measure


@pytest.fixture(scope="module")
def baseline():
    return measure()


@pytest.mark.parametrize(
    "name,area,reference,extra,missing",
    [
        ("square", 25, 16, 9, 0),
        ("thin", 12, 5, 7, 0),
        ("triangle", 21, 10, 11, 0),
        ("slanted", 27, 17, 11, 1),
        ("tiny", 6, 0, 6, 0),
        ("parts", 18, 8, 10, 0),
        ("ties", 25, 16, 9, 0),
    ],
)
def test_known_masks(baseline, name, area, reference, extra, missing):
    sample = next(c for c in baseline["cases"] if c["id"] == name)["samples"][0]
    assert (
        sample["svArea"],
        sample["cocoArea"],
        sample["extra"],
        sample["missing"],
    ) == (area, reference, extra, missing)


def test_published_proposal_is_measured_and_exact():
    path = ROOT / "site/masks.json"
    if not path.exists():
        pytest.skip("Run proposal generation first")
    data = json.loads(path.read_text())
    assert data["proposalSource"]
    assert sum(len(c["samples"]) for c in data["cases"]) == 147
    for case in data["cases"]:
        for sample in case["samples"]:
            assert sample["proposed"] == sample["coco"]
            assert sample["after"]["extra"] == sample["after"]["missing"] == 0
            assert sample["after"]["iou"] == 1
