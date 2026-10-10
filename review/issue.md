# Proposed issue title

COCO polygon loading disagrees with pycocotools reference rasterization

# Proposed issue body

### Search before asking

- [x] I searched the open issues and pull requests for polygon/mask rasterization and COCO reference parity.

### Bug

`DetectionDataset.from_coco` rounds continuous polygon vertices, then fills the integer boundary inclusively. That produces different masks from pycocotools for the same COCO annotation. A square from `(1,1)` to `(5,5)` gives 25 foreground pixels instead of the reference's 16 (IoU 0.64). Fractional, thin and diagonal polygons also differ; some slanted polygons have both extra and missing pixels.

See the issue and the proposed effect visually: **[interactive before/after demo](https://christophdeil.com/supervision-poly-check/)**. It starts at the +0.65 px square with pixel centres and rounded vertices visible. Choose “After proposal” or “Before / after side by side”. All displayed masks come from the actual libraries and proposed public loader, not a browser approximation. [Reproducible uv project and audit](https://github.com/cdeil/supervision-poly-check).

This is a COCO-loading compatibility bug caused by using another drawing convention. A generic inclusive integer rasterizer is valid, but COCO uses geometric boundaries. It is more than a subpixel shift: the filled area changes. [The COCO maintainer confirmed this convention](https://github.com/cocodataset/cocoapi/issues/659#issuecomment-3037056580), so I am not proposing a change in COCO itself.

@Borda, you reviewed/merged the earlier rounding change in [#2587](https://github.com/roboflow/supervision/pull/2587). This follows that work: rounding fixes truncation, but still differs from COCO rasterization. The earlier polygon report [#2023](https://github.com/roboflow/supervision/issues/2023) and its [#2080](https://github.com/roboflow/supervision/pull/2080) fix provide related context.

### Proposed behavior

Add an explicit `mask_rasterizer="pycocotools"` option, preserving fractional vertices and unioning all parts using `frPyObjects → merge → decode`. Provide it via the optional `supervision[coco]` extra. Preserve the current default and generic polygon drawing behavior; RLE decoding stays identical.

### Environment

- Baseline: Supervision 0.30.9; same polygon path confirmed on develop `0802a0e`.
- Reference: pycocotools 2.0.11, OpenCV 5.0.0.93.
- Reproducer: Python 3.14, macOS arm64; GitHub Actions repeats it on Linux.

### Minimal reproducible example

```python
import json
import tempfile
from pathlib import Path

import supervision as sv
from PIL import Image
from pycocotools import mask as coco_mask

polygon = [[1, 1, 5, 1, 5, 5, 1, 5]]
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    Image.new("RGB", (8, 8)).save(root / "image.png")
    annotation = {
        "images": [{"id": 1, "file_name": "image.png", "width": 8, "height": 8}],
        "categories": [{"id": 1, "name": "object"}],
        "annotations": [{"id": 1, "image_id": 1, "category_id": 1,
                         "bbox": [1, 1, 4, 4], "area": 16, "iscrowd": 0,
                         "segmentation": polygon}],
    }
    path = root / "annotations.json"
    path.write_text(json.dumps(annotation))
    ds = sv.DetectionDataset.from_coco(str(root), str(path))
    actual = next(iter(ds.annotations.values())).mask[0]
    reference = coco_mask.decode(coco_mask.merge(coco_mask.frPyObjects(polygon, 8, 8)))
    print(int(actual.sum()), int(reference.sum()))  # 25 16
```

### Related work

Hole export [#2702](https://github.com/roboflow/supervision/issues/2702) / [#2703](https://github.com/roboflow/supervision/pull/2703), and compact resize [#2704](https://github.com/roboflow/supervision/issues/2704) / [#2705](https://github.com/roboflow/supervision/pull/2705), concern separate conversion/resampling paths. This proposal does not close those reports. The audit also identifies a separate contour-to-COCO export round-trip problem; exact mask export should use RLE.

### Willing to submit a PR

- [x] Yes; an implementation with reference and compatibility regression tests is prepared for review.
