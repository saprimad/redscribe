# Feature freeze and release readiness audit — 2026-11-24

Status: not ready for full experiment. Researcher approved feature freeze; only integration, correctness and validation changes.

Evidence: dataset commit ca117aa, CI run 45391153563, 50 tests passed. Synthetic CPU CI is not GPU or GUI end-to-end evidence.

Open release gates:
1. Connect approved dataset manifest to GUI and batch runner; validate immediately before execution and on resume.
2. Connect offline rescoring to actual pilot artifacts and multi-recording runs; verify real schema and report preservation.
3. Retain 180-second pilot guard; design explicit full-recording execution with performance and cancellation tests. Raw CER dynamic programming is quadratic in transcript lengths.
4. Windows launch, actual CUDA FP16 verification and all selected backend smoke tests; verify ordinary transcription fallback unchanged.
5. Full recording pilot and resource/timing validation; verify output reports, checkpoint and resume.
6. Confirm model revision availability and document backend-specific decoding. Missing provenance is not proof of reproducibility.
7. Review documentation and obtain researcher approval before merge. No private data in repository.
