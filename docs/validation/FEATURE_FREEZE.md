# Feature freeze — stability and reliability

Researcher decision, 24 November 2026: no new features. Changes limited to defect fixes, data integrity, reliability, existing workflow integration, tests and documentation. Benchmark branch only; no main merge.

## Verified baseline
Commit b100670dc612e599fce3c5b71614e4246a6eaeef, Actions run 45412419438: Windows 74/74 (24.223 s), Ubuntu 74/74 (24.256 s). Synthetic tests; not actual GPU or GUI runtime validation.

## Release gates
- Audit matrix audit and report schemas against actual code; add missing regression coverage, including prediction tampering and plot cohort consistency.
- Verify stop/resume, invalid checkpoint, export failures, concurrent writer protection and GUI event lifecycle.
- Verify full-length workflow on Windows with actual CUDA FP16 models and non-study pilot audio; inspect reports and resource measurements.
- Confirm ordinary transcription unaffected, dependency installation reproducible, README and validation log accurate.
- No private study audio or transcripts in GitHub or CI. No merge until researcher approves.
