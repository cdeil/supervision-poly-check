"""Small, synthetic probes for adjacent mask and polygon behavior."""

import argparse
import json
import tempfile
from pathlib import Path

import cv2
import numpy as np
import supervision as sv
from PIL import Image
from supervision.dataset.formats.coco import coco_annotations_to_masks
from supervision.detection.utils.masks import resize_masks


def probe() -> dict:
    """Record current behavior without assuming every convention is a bug."""
    result = {}
    for name, shape, region, new_shape in [
        ("square", (640, 640), (slice(100, 120), slice(100, 120)), (1920, 1920)),
        ("line", (100, 100), (slice(10, 11), slice(10, 90)), (200, 200)),
    ]:
        mask = np.zeros(shape, bool)
        mask[region] = True
        rows, cols = np.nonzero(mask)
        bbox = np.array([[cols.min(), rows.min(), cols.max(), rows.max()]], float)
        compact = sv.CompactMask.from_dense(mask[None], bbox, shape)
        actual = compact.resize(new_shape).to_dense()[0]
        expected = cv2.resize(
            mask.astype(np.uint8), new_shape[::-1], interpolation=cv2.INTER_NEAREST
        ).astype(bool)
        result[f"compact_resize_{name}"] = {
            "actual_area": int(actual.sum()),
            "reference_area": int(expected.sum()),
            "different_pixels": int(np.count_nonzero(actual ^ expected)),
        }

    mask = np.zeros((1, 4, 4), bool)
    mask[0, :, 2] = True
    actual = resize_masks(mask, max_dimension=2)[0]
    expected = cv2.resize(
        mask[0].astype(np.uint8), (2, 2), interpolation=cv2.INTER_NEAREST
    ).astype(bool)
    result["resize_masks_sampling"] = {
        "actual": actual.astype(int).tolist(),
        "opencv_nearest": expected.astype(int).tolist(),
    }

    # Equal pixel counts with incompatible geometry currently pass silently.
    encoded_mask = np.zeros((2, 8), bool)
    encoded_mask[:, 1:3] = True
    rle = {"size": [2, 8], "counts": sv.mask_to_rle(encoded_mask)}
    decoded = coco_annotations_to_masks([{"id": 1, "segmentation": rle}], (4, 4))[0]
    result["rle_size_mismatch"] = {
        "encoded_size": rle["size"],
        "loaded_size": list(decoded.shape),
        "accepted": True,
        "mask": decoded.astype(int).tolist(),
    }

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        image = str(root / "image.png")
        Image.new("RGB", (150, 100)).save(image)
        mask = np.zeros((100, 150), bool)
        mask[10:60, 10:60] = True
        mask[25:45, 25:45] = False
        detection = sv.Detections(
            xyxy=np.array([[10, 10, 59, 59]], float),
            mask=mask[None],
            class_id=np.array([0]),
        )
        dataset = sv.DetectionDataset(
            classes=["ring"], images=[image], annotations={image: detection}
        )
        dataset.as_yolo(
            str(root / "images"), str(root / "labels"), str(root / "data.yaml")
        )
        result["hole_export"] = {
            "original_instances": 1,
            "original_area": int(mask.sum()),
            "exported_label_lines": len(
                (root / "labels/image.txt").read_text().splitlines()
            ),
        }

    mask = np.zeros((8, 8), bool)
    mask[1:5, 1:5] = True
    polygons = [p.reshape(-1).tolist() for p in sv.mask_to_polygons(mask)]
    from pycocotools import mask as coco_mask

    restored = coco_mask.decode(coco_mask.merge(coco_mask.frPyObjects(polygons, 8, 8)))
    result["contour_coco_roundtrip"] = {
        "original_area": int(mask.sum()),
        "reference_reloaded_area": int(restored.sum()),
        "polygon": polygons,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = probe()
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
