## Plan: Reproduce and visualize COCO polygon rasterization

- **Date:** 2026-10-10
- **Status:** In progress
- **Summary:** Publish a reproducible comparison and develop a reviewed, opt-in COCO-reference loader patch for Supervision.

- [x] Create the public repository and configure history protection. *(agent-executable)*
- [x] Recheck open polygon/mask issues and active pull requests. *(agent-executable)*
- [x] Audit the relevant code paths and document confirmed findings. *(agent-executable)*
- [x] Implement and test the opt-in reference rasterizer in a fork branch. *(agent-executable)*
- [x] Reproduce baseline and proposal masks through the real public loader using uv. *(agent-executable)*
- [x] Add a before/after toggle and deploy the website with GitHub Pages. *(agent-executable)*
- [x] Prepare issue and pull request text with the public demo and earlier reports. *(agent-executable)*
- [x] Present the patch and proposed submissions for review. *(agent-executable)*
- [ ] Approve and submit the upstream issue and pull request. *(human-required)*

The implementation preserves existing loader defaults and generic polygon fill. The proposed `mask_rasterizer="pycocotools"` selector preserves continuous coordinates and requires the optional `supervision[coco]` extra. Related export-hole and compact-resize reports already have active fixes; this patch does not duplicate them.

The audit also reproduced a separate contour-to-COCO round-trip loss and missing RLE declared-shape validation. Current develop now passes the two original compact-resize report examples after merged #2697. Submission remains pending human review.

Review PRs: [reproducer](https://github.com/cdeil/supervision-poly-check/pull/1) and [Supervision fork](https://github.com/cdeil/supervision/pull/1). The upstream issue and PR have not been submitted; approve the drafts before posting.

After review feedback, replaced the editorial layout with a compact results page: all three masks and metrics fit in the first desktop viewport. Refreshed the PR screenshot and retained the requested overlays and +0.65 px default.
