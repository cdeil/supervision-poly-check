"""Measure polygon fill paths and polygon/RLE export round trips."""

import importlib.metadata
import json
import tempfile
import warnings
from pathlib import Path

import cv2
import numpy as np
import supervision as sv
from PIL import Image
from pycocotools import mask as coco_mask
from supervision.dataset.formats.coco import (
    coco_annotations_to_masks,
    detections_to_coco_annotations,
)

from reproduce import ROOT, SIZE, load_mask


def reference_mask(polygons: list) -> np.ndarray:
    """Rasterize COCO polygons through the reference implementation."""
    if not polygons:
        return np.zeros((SIZE, SIZE), dtype=bool)
    flat = [np.asarray(p).reshape(-1).tolist() for p in polygons]
    return coco_mask.decode(
        coco_mask.merge(coco_mask.frPyObjects(flat, SIZE, SIZE))
    ).astype(bool)


def bitmap(mask: np.ndarray) -> list[int]:
    """Serialize the eight-by-eight mask in row order."""
    return mask.astype(int).reshape(-1).tolist()


def measure_round_trips(root: Path) -> list[dict]:
    """Export ordinary instances without simplification, then decode each path."""
    cases = []
    for name, title in [
        ("rectangle", "4 × 4 rectangle"),
        ("pixel", "Single pixel"),
        ("hole", "Instance with a hole"),
    ]:
        source = np.zeros((SIZE, SIZE), dtype=bool)
        if name == "rectangle":
            source[2:6, 2:6] = True
        elif name == "pixel":
            source[3, 3] = True
        else:
            source[1:7, 1:7] = True
            source[3:5, 3:5] = False
        ys, xs = np.where(source)
        detections = sv.Detections(
            xyxy=np.array(
                [[xs.min(), ys.min(), xs.max() + 1, ys.max() + 1]], dtype=float
            ),
            mask=source[None],
            class_id=np.array([0]),
            data={"iscrowd": np.array([0])},
        )
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always", UserWarning)
            annotations, _ = detections_to_coco_annotations(
                detections, image_id=1, annotation_id=1, approximation_percentage=0
            )
        segmentation = [[int(v) for v in p] for p in annotations[0]["segmentation"]]
        assert annotations[0]["iscrowd"] == 0
        current = coco_annotations_to_masks(annotations, (SIZE, SIZE))[0]
        if segmentation:
            np.testing.assert_array_equal(current, load_mask(root, segmentation))
        reference = reference_mask([np.asarray(p).reshape(-1, 2) for p in segmentation])
        # Candidate lossless encoding, not an implementation of a new SV exporter.
        rle = coco_mask.encode(np.asfortranarray(source.astype(np.uint8)))
        rle["counts"] = rle["counts"].decode("ascii")
        rle_reference = coco_mask.decode(rle).astype(bool)
        rle_current = load_mask(root, rle)
        np.testing.assert_array_equal(rle_reference, source)
        np.testing.assert_array_equal(rle_current, source)
        # Hand-authored boundary fixtures, not a general mask-to-polygon exporter.
        edge_polygons = {
            "rectangle": [[[2, 2], [6, 2], [6, 6], [2, 6]]],
            "pixel": [[[3, 3], [4, 3], [4, 4], [3, 4]]],
        }.get(name)
        edge_reference = reference_mask(edge_polygons) if edge_polygons else None
        if edge_reference is not None:
            np.testing.assert_array_equal(edge_reference, source)
        cases.append(
            {
                "id": name,
                "title": title,
                "source": bitmap(source),
                "segmentation": segmentation,
                "emptySegmentation": not segmentation,
                "iscrowd": 0,
                "supervision": bitmap(current),
                "coco": bitmap(reference),
                "rle": bitmap(rle_reference),
                "rleSupervision": bitmap(rle_current),
                "pixelEdgePolygons": edge_polygons,
                "pixelEdgeCoco": (
                    bitmap(edge_reference) if edge_reference is not None else None
                ),
                "exportWarnings": [str(warning.message) for warning in captured],
            }
        )
    return cases


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

        result["roundTrips"] = measure_round_trips(root)
    return result


if __name__ == "__main__":
    output = ROOT / "site/choices.json"
    output.write_text(json.dumps(measure_choices(), separators=(",", ":")) + "\n")
    print("Verified 63 fill comparisons and 3 polygon/RLE export round trips")
