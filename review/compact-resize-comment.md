# Draft comment for Supervision #2704

I reran the square and thin-line reproductions on current develop `0802a0e` with native OpenCV 5.0.0.93. Both now match dense `INTER_NEAREST` exactly:

| Reproduction | Compact area | Dense area | Differing pixels |
| --- | ---: | ---: | ---: |
| 20×20 square, 640→1920 | 3600 | 3600 | 0 |
| 1×80 line, 100→200 | 320 | 320 | 0 |

The original report used `69cb843`; [#2697](https://github.com/roboflow/supervision/pull/2697) was merged on October 9. These two examples appear covered by that change. This does not establish exhaustive parity or rule out independent improvements in #2705.

[Pinned runnable probes and results](https://github.com/cdeil/supervision-poly-check/blob/coco-polygon-demo/review/audit.md) are available for comparison. Could the remaining #2705 scope be checked against the current develop implementation before duplicating the fix?
