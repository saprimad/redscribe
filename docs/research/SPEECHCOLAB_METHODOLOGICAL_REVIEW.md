# SpeechColab methodological review

## Source inspected
- https://github.com/SpeechColab/Leaderboard/blob/master/ops/benchmark
- Inspected file blob: d099db9a5d852924b32b508ad7d7d413e1df3aad.
- Related research: https://arxiv.org/abs/2403.08196 (bibliographic and indexing details require independent verification).

## Direct observations
The host runner accepts one model and one dataset via CLI, or one model and multiple test sets via YAML. It validates model metadata and the SBI executable, builds a model-specific Docker image and invokes utils/benchmark.sh inside the container. This establishes model-oriented orchestration, not proof of a single GPU weight-loading event. No SpeechColab runtime experiment was performed.

## Proposed RedScribe adaptation
Use one local model session across the explicitly approved recording list, one recording at a time. Record loading and warm-up separately from inference; verify CUDA/FP16 where supported. Preserve raw predictions and raw verbatim WER/CER including fillers. Use model-by-recording checkpoints, verified offline rescoring, and separate resource measurements. Record session restarts and do not conflate resumed sessions with uninterrupted loading. Keep normal transcription unchanged. No cloud processing or private data upload.

## Implementation gates
1. Separate adapter lifecycle from per-recording inference.
2. Validate model-major execution and failure isolation using synthetic adapters.
3. Integrate model-level resume and dataset integrity checks.
4. Validate long-form scoring performance and GUI integration.
5. Run Windows/Linux regression and actual RTX GPU pilot before release.

This is a design reference, not a claim that SpeechColab uses the identical loading policy or long-form protocol. No scoring normalisation changes approved.
