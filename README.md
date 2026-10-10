# Supervision polygon check

[Open the interactive before/after demo](https://christophdeil.com/supervision-poly-check/).
GitHub Pages also serves it through [cdeil.github.io](https://cdeil.github.io/supervision-poly-check/), which redirects to the account's existing custom domain.

The same COCO polygon produces different masks in Supervision and pycocotools. A square from `(1, 1)` to `(5, 5)` has 25 pixels with Supervision's inclusive integer fill and 16 with COCO's reference rasterization. This is a COCO-loading compatibility bug caused by different conventions, not just a subpixel translation. The generic inclusive drawing function has a valid, documented convention.

The proposed change adds an opt-in `mask_rasterizer="pycocotools"` to `DetectionDataset.from_coco`, with an optional `supervision[coco]` dependency. Existing defaults stay unchanged. The demo shows actual outputs from the proposed loader; all 147 after masks match the reference exactly. It starts on the square at +0.65 px with pixel centres and rounded Supervision vertices visible. Use **After proposal** or **Before / after side by side** to inspect the change.

![Before and after, with geometric boundaries and pixel centres](site/before-after.png)

## Reproduce with uv

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```bash
git clone https://github.com/cdeil/supervision-poly-check.git
cd supervision-poly-check
uv sync --locked
uv run --locked pytest -q
uv run --locked python reproduce.py --output results/baseline.json
uv run --locked --with-requirements requirements-proposal.txt \
  --with 'supervision[coco] @ git+https://github.com/cdeil/supervision@754ce36b6d546395ea56522b7a06466b80492acb' \
  python reproduce.py --baseline results/baseline.json --output site/masks.json
uv run --locked python -m http.server 8000 --directory site
```

Open `http://localhost:8000`. Python 3.14 is selected by `.python-version`; uv installs it if necessary. `uv.lock` pins the baseline (Supervision 0.30.9, pycocotools 2.0.11, OpenCV 5.0.0.93). The proposal is pinned to an immutable fork commit; `requirements-proposal.txt`, exported from the same lock with Supervision excluded, pins its other packages. The browser loads measured arrays from `site/masks.json`, rather than approximating rasterization in JavaScript.

Seven synthetic shapes × twenty-one offsets produce 147 measurements. Every baseline reference is checked against Supervision's RLE path. In proposal mode, the generator verifies that defaults remain pixel-identical, and that polygon and RLE reference-mode masks match pycocotools. No external datasets or credentials are needed.

GitHub Actions regenerates and compares the published data on Linux before deploying. Site source, fixtures, a small screenshot and measured outputs are committed so the evidence is inspectable. To put environments outside the checkout, set `UV_PROJECT_ENVIRONMENT` to a scratch directory before the commands above.

## Audit and proposed submissions

- [Polygon and mask audit, current tracker findings and reproducible probes](review/audit.md)
- [Proposed Supervision issue](review/issue.md)
- [Proposed upstream pull request text](review/upstream-pr.md)
- [Comment draft for the existing compact-resize report](review/compact-resize-comment.md)
- [Execution plan](docs/plans/plan-coco-polygons.md)

The issue and upstream PR text are drafts for review. The fork contains the implementation; these files do not imply an upstream submission.

For exact mask preservation when exporting COCO, RLE is needed: existing contour-to-polygon export is a separate issue and is not changed by this loader proposal.
