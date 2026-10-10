"""Measure actual public COCO loaders; never substitute a reference for the proposal."""

import argparse
import importlib.metadata
import json
import tempfile
import tomllib
from pathlib import Path

import numpy as np
import supervision as sv
from PIL import Image
from pycocotools import mask as coco_mask

ROOT = Path(__file__).resolve().parent
SIZE = 8


def load_mask(
    root: Path, segmentation: list | dict, proposal: bool = False
) -> np.ndarray:
    """Load a synthetic annotation through DetectionDataset.from_coco."""
    annotation = {
        "images": [{"id": 1, "file_name": "image.png", "width": SIZE, "height": SIZE}],
        "categories": [{"id": 1, "name": "object"}],
        "annotations": [
            {
                "id": 1,
                "image_id": 1,
                "category_id": 1,
                "bbox": [1, 1, 4, 4],
                "area": 16,
                "iscrowd": 0,
                "segmentation": segmentation,
            }
        ],
    }
    path = root / "annotations.json"
    path.write_text(json.dumps(annotation), encoding="utf-8")
    options = {"mask_rasterizer": "pycocotools"} if proposal else {}
    dataset = sv.DetectionDataset.from_coco(
        images_directory_path=str(root), annotations_path=str(path), **options
    )
    detection = next(iter(dataset.annotations.values()))
    assert detection.mask is not None
    assert detection.mask.shape == (1, SIZE, SIZE)
    assert detection.mask.dtype == bool
    assert detection.class_id.tolist() == [0]
    return detection.mask[0]


def compare(actual: np.ndarray, reference: np.ndarray) -> dict:
    """Count differences and foreground intersection-over-union."""
    union = int(np.count_nonzero(actual | reference))
    return {
        "svArea": int(actual.sum()),
        "cocoArea": int(reference.sum()),
        "extra": int(np.count_nonzero(actual & ~reference)),
        "missing": int(np.count_nonzero(reference & ~actual)),
        "iou": float(np.count_nonzero(actual & reference) / union) if union else 1.0,
    }


def measure(baseline: dict | None = None) -> dict:
    """Measure seven shapes at twenty-one offsets with the installed libraries."""
    cases = json.loads((ROOT / "fixtures.json").read_text(encoding="utf-8"))
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    proposal = config["tool"]["uv"]["sources"]["supervision"][0]
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
        "proposalSource": f"{proposal['git']}/tree/{proposal['rev']}" if baseline else None,
        "baselineVersions": baseline["versions"] if baseline else None,
        "cases": [],
    }
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        Image.new("RGB", (SIZE, SIZE)).save(root / "image.png")
        for case_index, fixture in enumerate(cases):
            case = {key: fixture[key] for key in ["id", "title", "note"]}
            case["samples"] = []
            for step in range(21):
                offset = round(step * 0.05, 2)
                polygons = [
                    np.round(np.asarray(p) + offset, 8) for p in fixture["polygons"]
                ]
                flat = [p.reshape(-1).tolist() for p in polygons]
                reference = coco_mask.decode(
                    coco_mask.merge(coco_mask.frPyObjects(flat, SIZE, SIZE))
                ).astype(bool)
                actual = load_mask(root, flat)
                rle = coco_mask.encode(np.asfortranarray(reference.astype(np.uint8)))
                rle["counts"] = rle["counts"].decode("ascii")
                np.testing.assert_array_equal(load_mask(root, rle), reference)
                sample = {
                    "offset": offset,
                    "polygons": [p.tolist() for p in polygons],
                    "rounded": [np.round(p).astype(int).tolist() for p in polygons],
                    "supervision": actual.astype(int).reshape(-1).tolist(),
                    "coco": reference.astype(int).reshape(-1).tolist(),
                    **compare(actual, reference),
                }
                if baseline:
                    before = baseline["cases"][case_index]["samples"][step]
                    assert before == sample, "The proposal must preserve default output"
                    proposed = load_mask(root, flat, proposal=True)
                    np.testing.assert_array_equal(proposed, reference)
                    np.testing.assert_array_equal(
                        load_mask(root, rle, proposal=True), reference
                    )
                    sample["proposed"] = proposed.astype(int).reshape(-1).tolist()
                    sample["after"] = compare(proposed, reference)
                case["samples"].append(sample)
            result["cases"].append(case)
    return result


def main() -> None:
    """Write baseline data, or verify a real installed patch against that baseline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text()) if args.baseline else None
    result = measure(baseline)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, separators=(",", ":")) + "\n")
    print(f"Verified 147 polygon/RLE cases; proposal enabled: {baseline is not None}")


if __name__ == "__main__":
    main()
