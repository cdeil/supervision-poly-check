"""Measure the three fill paths and a contour round trip for the decision page."""

import importlib.metadata
import json
import tempfile
from pathlib import Path

import cv2
import numpy as np
import supervision as sv
from PIL import Image
from pycocotools import mask as coco_mask

from reproduce import ROOT, SIZE, load_mask


def reference_mask(polygons: list) -> np.ndarray:
    """Rasterize COCO polygons through the reference implementation."""
    flat = [np.asarray(p).reshape(-1).tolist() for p in polygons]
    return coco_mask.decode(
        coco_mask.merge(coco_mask.frPyObjects(flat, SIZE, SIZE))
    ).astype(bool)


def bitmap(mask: np.ndarray) -> list[int]:
    """Serialize the eight-by-eight mask in row order."""
    return mask.astype(int).reshape(-1).tolist()


def measure_choices() -> dict:
    """Use the released loader and OpenCV, without importing Ultralytics."""
    assert importlib.metadata.version("supervision") == "0.30.9", (
        "Generate with uv run --locked --extra before python choices_data.py"
    )
    fixtures = json.loads((ROOT / "fixtures.json").read_text())
    published = json.loads((ROOT / "site/masks.json").read_text())
    result = {
        "canvas": [SIZE, SIZE],
        "versions": {
            name: importlib.metadata.version(name)
            for name in [
                "supervision",
                "pycocotools",
                "opencv-python-headless",
                "numpy",
            ]
        },
        "truncationScope": (
            "Independent OpenCV integer-fill experiment. Matches the documented "
            "truncate-then-fill steps of Ultralytics polygon2mask for one polygon "
            "at full resolution. Does not run Ultralytics, resampling, or training."
        ),
        "cases": [],
    }
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        Image.new("RGB", (SIZE, SIZE)).save(root / "image.png")
        for fixture in fixtures:
            if fixture["id"] not in {"square", "thin", "slanted"}:
                continue
            case = {"id": fixture["id"], "title": fixture["title"], "samples": []}
            original = next(c for c in published["cases"] if c["id"] == case["id"])
            for step in range(21):
                offset = round(step * 0.05, 2)
                polygons = [
                    np.round(np.asarray(p) + offset, 8) for p in fixture["polygons"]
                ]
                flat = [p.reshape(-1).tolist() for p in polygons]
                supervision = load_mask(root, flat)
                coco = reference_mask(polygons)
                truncated = np.zeros((SIZE, SIZE), dtype=np.uint8)
                # Independent use of OpenCV's public fillPoly API, not copied code.
                cv2.fillPoly(truncated, [p.astype(np.int32) for p in polygons], color=1)
                assert bitmap(supervision) == original["samples"][step]["supervision"]
                assert bitmap(coco) == original["samples"][step]["coco"]
                case["samples"].append(
                    {
                        "offset": offset,
                        "polygon": polygons[0].tolist(),
                        "rounded": np.round(polygons[0]).astype(int).tolist(),
                        "truncated": polygons[0].astype(int).tolist(),
                        "coco": bitmap(coco),
                        "supervision": bitmap(supervision),
                        "opencvTruncated": bitmap(truncated),
                    }
                )
            result["cases"].append(case)

        source = np.zeros((SIZE, SIZE), dtype=bool)
        source[2:6, 2:6] = True
        contours = [p.tolist() for p in sv.mask_to_polygons(source)]
        flat = [np.asarray(p).reshape(-1).tolist() for p in contours]
        current = load_mask(root, flat)
        reference = reference_mask(contours)
        assert (int(source.sum()), int(current.sum()), int(reference.sum())) == (
            16,
            16,
            9,
        )
        result["roundTrip"] = {
            "source": bitmap(source),
            "contours": contours,
            "supervision": bitmap(current),
            "coco": bitmap(reference),
        }
    return result


if __name__ == "__main__":
    output = ROOT / "site/choices.json"
    output.write_text(json.dumps(measure_choices(), separators=(",", ":")) + "\n")
    print("Verified 63 three-way comparisons and the 16 → 16 / 9 contour example")
