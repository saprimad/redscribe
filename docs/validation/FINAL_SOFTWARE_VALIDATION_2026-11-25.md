# Software validation record — 25 November 2026

Scope: PR #27, refactor/benchmark-architecture. Validated code commit: `1556b8fe0770cbb5fc2a1cb9939b00943b3b4f20`. This record is for expert review, not authorisation to commence the formal experiment or merge.

## Verified CI evidence

| Platform | Tests passed | Failed | Duration |
| --- | ---: | ---: | ---: |
| Windows, Python 3.11 | 84 | 0 | 51.903 s |
| Ubuntu, Python 3.11 | 84 | 0 | 30.319 s |

84 distinct suite tests executed on each platform (168 executions). [Regression run](https://github.com/saprimad/redscribe/actions/runs/45542332260); [Windows job](https://github.com/saprimad/redscribe/actions/runs/45542332260/job/138963581178); [Ubuntu job](https://github.com/saprimad/redscribe/actions/runs/45542332260/job/138963581569).

[Dependency validation run](https://github.com/saprimad/redscribe/actions/runs/45542332203) completed successfully on Windows and Ubuntu. Scope: declared dependency installation, CPU PyTorch, pip check, runtime imports and resolved version listing. This does not establish CUDA compatibility or reproducibility across future unpinned dependency resolutions.

## Defect closure and scope

- Batch export failure recovery: checkpoint manifest precedes secondary exports; regression suite covers reporting failure and cancellation. Corrective commit addc5d2f3d83971359b9f84c85d79a5251ea775a.
- Raw prediction integrity: synthetic exact-byte UTF-8 persistence, SHA-256, non-overwrite and independent rescoring/tamper checks.
- Ground truth integrity: synthetic DOCX extraction, repeated table content, approval and hash mutation checks. Actual participant document layout remains subject to local review.
- Scientific figures: synthetic common-cohort corpus WER/CER, boxplot medians, RTF scatter and masked heatmap values; existing export tests cover PNG/SVG and workbook creation. Initial run [45541905516](https://github.com/saprimad/redscribe/actions/runs/45541905516) failed one test on each OS because the test selected an incorrect Matplotlib line index. Commit 1556b8f uses named median artists without changing expected values or scoring; subsequent run passed.
- Dependency workflow trigger corrected in commit 6b46855e8cc1d114461badd889e161cfe23732d0.

## Remaining gates

Synthetic tests and CPU dependency checks passed within the stated scope. No real ASR inference, physical GPU, CUDA/FP16, GUI interaction, full-length audio performance or participant dataset validation is established by these CI runs. Before formal benchmarking: expert review of architecture and protocol; local clean-environment GUI smoke test; non-sensitive audio/reference smoke test on RTX 5070 with device/precision verification, exports and independent rescoring; verify each intended model and local reference layout; record actual results and freeze the approved version. Existing methodological HOLD decisions remain unchanged.

No participant data is required for CI. Keep PR #27 draft and unmerged. This record does not certify all possible defects absent.
