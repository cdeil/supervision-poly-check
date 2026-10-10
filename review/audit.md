# Polygon and mask audit

Checked 2026-10-10 against `roboflow/supervision` develop commit `0802a0e79ae097bfaad45a65f94cba9a2ae2a1c2`, release 0.30.9, and pycocotools 2.0.11. The proposed loader commit is `754ce36b6d546395ea56522b7a06466b80492acb`. Synthetic inputs only.

## Findings and scope

| Path | Finding | Evidence / recommendation |
| --- | --- | --- |
| COCO polygon ingestion | **Confirmed compatibility bug.** Rounded vertices plus inclusive fill differ from reference COCO masks. | Square: 25 versus 16 pixels; slanted polygon: 11 extra and 1 missing. Proposed opt-in reference mode fixes all 147 fixture states, retaining defaults. |
| Generic `polygon_to_mask` | Inclusive integer drawing is intentional; float inputs are truncated here, while dataset/model adapters often round first. | Document the distinction explicitly. Do not globally replace this function: zones, annotations and other formats rely on its convention. |
| COCO polygon export | **Confirmed reference round-trip loss.** Pixel-index contours are serialized as geometric COCO boundaries. | A 4×4 mask becomes a polygon spanning coordinates 1..4; reference reloading yields 3×3, area 9 instead of 16. A uniform +0.5 shift does not expand the contour's width. Prefer an explicit RLE export mode that preserves `iscrowd=0` for ordinary instances, or a carefully specified boundary conversion. Keep this separate from loading. |
| Hole export | **Confirmed on current develop.** A ring of area 2100 exports as two YOLO instance lines. | Already tracked by [#2702](https://github.com/roboflow/supervision/issues/2702), with active [#2703](https://github.com/roboflow/supervision/pull/2703). Hierarchy/topology needs format-aware handling. Do not duplicate this patch. |
| Compact-mask resize | The two published reproductions in open [#2704](https://github.com/roboflow/supervision/issues/2704) **now pass on current develop**. | Square: 3600/3600; line: 320/320; zero pixel differences. [#2697](https://github.com/roboflow/supervision/pull/2697) was merged on 2026-10-09. Active [#2705](https://github.com/roboflow/supervision/pull/2705) may still have independent changes; this probe does not prove all resizing cases correct. A draft comment records the evidence. |
| Internal `resize_masks` | **Confirmed sampling difference**, but its documentation does not promise OpenCV parity. | It uses endpoint-inclusive `linspace` indices. 4→2 samples [0,3]; OpenCV nearest samples [0,2]. A foreground column at x=2 disappears in this helper but survives in OpenCV. Specify a sampling convention and test it before changing behavior. This is separate from CompactMask resizing. |
| COCO RLE ingestion | **Confirmed missing shape validation.** The loader ignores segmentation `size` and checks only total pixel count. | `[2,8]` RLE loaded into a `[4,4]` image is silently reshaped. Validate declared size against image dimensions, retain support for legacy counts-only data, and name the annotation in errors. Separate focused validation PR. |
| Contours and mask bounds | Several nearby apparent off-by-one differences are documented conventions. | `mask_to_xyxy` has inclusive/exclusive options; `mask_to_roi` returns exclusive slice bounds. Do not change default extents as part of polygon rasterization. |

Source review covered COCO ingestion/export, YOLO/LabelMe/Pascal VOC adapters and their shared polygon approximation, `detection/utils/{converters,masks,polygons}.py`, `CompactMask` resize/RLE helpers, `PolygonZone`, and relevant backend fill/contour paths. This is a focused static review with synthetic probes, not a security or exhaustive numerical audit.

The loader patch preserves annotation alignment for missing/empty masks, checks finite coordinates before native conversion, skips parts with fewer than three vertices, retains fractional coordinates, and merges valid parts as a union. It does not alter box extents, stored annotation area, crowd metadata, generic drawing or exports. Annotation `area` may remain the supplied continuous area and need not equal a rasterized mask's pixel count.

## Current tracker check

Searched open issues and pull requests for polygon, mask, COCO, pycocotools, rasterization and rasterisation. No directly matching open Supervision reference-rasterization ticket was found. Search results can miss reports using other terminology.

- Earlier rounding fix [#2587](https://github.com/roboflow/supervision/pull/2587), merged by @Borda: fixes truncation and adapter consistency; it does not implement COCO boundary rules.
- Earlier YOLO report [#2023](https://github.com/roboflow/supervision/issues/2023) and rounding fix [#2080](https://github.com/roboflow/supervision/pull/2080): related coordinate rounding, different format/convention.
- Hole export [#2702](https://github.com/roboflow/supervision/issues/2702) / [#2703](https://github.com/roboflow/supervision/pull/2703): closely related mask conversion, already being addressed.
- Compact resize [#2704](https://github.com/roboflow/supervision/issues/2704) / [#2705](https://github.com/roboflow/supervision/pull/2705): resampling rather than polygon filling; original examples now pass after merged #2697.
- [#2689](https://github.com/roboflow/supervision/issues/2689): pycocotools metric parity, but per-image/per-class detection limits require a separate metrics change.
- PolygonZone occupancy [#2524](https://github.com/roboflow/supervision/issues/2524), [#1449](https://github.com/roboflow/supervision/issues/1449), camera motion [#2656](https://github.com/roboflow/supervision/issues/2656), per-class counting [#791](https://github.com/roboflow/supervision/issues/791), panoptic annotation [#1308](https://github.com/roboflow/supervision/issues/1308), mask mAP [#480](https://github.com/roboflow/supervision/issues/480), and geometry dispatch [#2318](https://github.com/roboflow/supervision/issues/2318) concern other features or contracts; the loader patch does not resolve them.

## COCO upstream: bug or convention?

The COCO maintainer explains the geometric-boundary convention in [cocodataset/cocoapi #659](https://github.com/cocodataset/cocoapi/issues/659#issuecomment-3037056580). A proposal to include the extra boundaries, [ppwwyyxx/cocoapi #30](https://github.com/ppwwyyxx/cocoapi/pull/30), was closed unmerged. The PyPI fork's issue tracker is disabled; its polygon routine is semantically the same as the original COCO implementation.

Thus it is fair to report a **Supervision COCO-loader compatibility bug**, while recognizing that its generic drawing rule is valid. Do not report COCO's intentional convention as a bug or ask both projects to converge on inclusive drawing. A half-pixel translation alone cannot fix changed areas and diagonal edge decisions: COCO's native `rleFrPoly` applies 5× boundary rasterization and specific quantization/tie rules.

## Reproduce the additional probes

```bash
uv run --locked --with-requirements requirements-proposal.txt \
  --with 'supervision[coco] @ git+https://github.com/cdeil/supervision@754ce36b6d546395ea56522b7a06466b80492acb' \
  python audit.py --output review/audit-results.json
```

The pinned proposal changes only COCO polygon loading, so these probes exercise the same unrelated resize/export/RLE code as the stated develop base. [Recorded results](audit-results.json) keep numerical evidence inspectable. pycocotools 2.0.11 emits a NumPy 2 `__array__(copy=...)` deprecation warning; it does not change these masks. The new upstream reference tests narrowly filter that external warning while retaining the project's error-on-deprecation policy elsewhere.

## Recommended sequence

1. Review and submit the opt-in loader PR and its visual demo.
2. Coordinate hole-export changes with existing #2703; send the current-develop reproduction results to #2704 for triage.
3. Prepare a separate exact COCO RLE export proposal, with instance/crowd metadata and contour-convention tests.
4. Add RLE declared-shape validation in a small separate PR.
5. Clarify the internal downsampling grid and test numerical parity before any compatibility change.
