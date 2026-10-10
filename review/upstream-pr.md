## Description

COCO polygon loading uses rounded integer vertices with inclusive fill, so a square spanning `(1,1)` to `(5,5)` becomes 25 pixels instead of pycocotools' reference 16. This PR adds opt-in reference rasterization to `DetectionDataset.from_coco` through `mask_rasterizer="pycocotools"`. Existing callers retain their current masks.

See the issue and effect visually: **[interactive before/after demo](https://christophdeil.com/supervision-poly-check/)**. Select “After proposal” or the side-by-side view. [uv reproducer and measured data](https://github.com/cdeil/supervision-poly-check) pin both the released baseline and the actual proposed loader; all 147 after masks match the reference.

<img src="https://raw.githubusercontent.com/cdeil/supervision-poly-check/coco-polygon-demo/site/before-after.png" width="900" alt="At a 0.65 pixel offset, the same square gives 25 pixels before and 16 after; pixel centres and rounded vertices show the boundary difference.">

## Motivation and Context

COCO vertices describe continuous boundaries; inclusive integer drawing interprets them as pixel indices. The mismatch changes areas and diagonal edge decisions, so applying a constant subpixel shift is insufficient. [COCO's maintainer confirms this convention](https://github.com/cocodataset/cocoapi/issues/659#issuecomment-3037056580).

Related: [#2587](https://github.com/roboflow/supervision/pull/2587) fixed truncation by rounding; [#2023](https://github.com/roboflow/supervision/issues/2023) and [#2080](https://github.com/roboflow/supervision/pull/2080) cover earlier YOLO rounding. This adds reference COCO compatibility without changing their generic drawing convention.

## Changes Made

- Add a keyword-only rasterizer selector, passed through the COCO loading path; validate unsupported values even for box-only input.
- Add the optional `coco` extra and lazy pycocotools import with installation guidance.
- Preserve continuous finite vertices and merge multipart reference RLEs as a union. Empty and fewer-than-three-vertex parts remain empty.
- Preserve defaults, RLE decoding, bounding boxes and crowd metadata. Document the separate export convention and exact-RLE requirement.

## Testing

- Before implementation: 20 failures and 2 passes in the new test module, reproducing the missing selector.
- After implementation: all 22 new tests pass, including fractional/tie/sliver/diagonal/concave/multipart/canvas-edge polygons, RLE/default parity, missing dependency and invalid coordinates.
- `uv run pytest --cov=supervision`: NumPy fallback backend, 5,415 passed / 79 skipped; native OpenCV backend, 5,694 passed / 1 skipped. The fallback baseline was 5,393 passed / 79 skipped; no regression.
- `uv run pre-commit run --all-files`: all hooks passed, including Ruff, formatting, mypy, codespell and documentation checks.
- Demo generator: all 147 default masks unchanged and all 147 proposed masks pixel-identical to pycocotools; RLE paths verified in both modes.

- [x] Added/updated tests, and the full suite passes locally
- [x] Updated public API docstrings
- [x] Added an Unreleased changelog entry

## Additional Notes

The reference dependency is optional. The existing inclusive convention remains the default for compatibility; a default change would need a separate migration decision. Polygon export is unchanged and is not an exact mask round-trip across COCO tools; RLE is needed for exact preservation. Hole-export and compact-resize reports already have separate active fixes; [audit and related tracker evidence](https://github.com/cdeil/supervision-poly-check/blob/coco-polygon-demo/review/audit.md).

The new reference tests narrowly filter pycocotools 2.0.11's NumPy 2 `__array__(copy=...)` deprecation warning. The project's warning policy remains unchanged for other tests.
