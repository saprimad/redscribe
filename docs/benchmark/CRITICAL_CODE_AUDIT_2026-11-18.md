# RedScribe Benchmarking Mode — Critical Code Audit (18 November 2026)

**Scope:** Static source review of the `redscribe-benchmark-timeline` branch, targeting a defensible ASR model-comparison study. The production `main` branch was not modified. This review was conducted remotely: **no RTX 5070, Windows Tkinter smoke test or full test suite was executed**. Severity reflects possible research impact, not a claim that the issue has already occurred in a real run.

## Summary

**Disposition: NOT READY for publication-grade experiments yet.** The existing pilot is useful for integration testing and short private audio with approved references. It is not yet a validated fair comparison of eleven ASR models. The five researcher-designated methodological HOLD items remain HOLD.

### Findings and changes made in this audit

| ID | Severity | Finding | Action/status |
|---|---|---|---|
| F01 | HIGH | Worker thread interacted with Tkinter state and called `window.after` directly; closing UI mid-run could interrupt writing | **FIXED in branch:** Tk variables snapshotted on UI thread; `queue.Queue` forwards status and completion; close button/WM close protected while worker is running |
| F02 | HIGH | Approved manifest originally stored the source DOCX SHA-256 but verification only checked the frozen scoring text, allowing later edits to the original DOCX to go unnoticed | **FIXED in branch:** manifest stores original local source path and hash, and verifies both source DOCX and scoring TXT. Old manifests missing source path require a fresh approval. Synthetic regression tests added |
| F03 | MEDIUM | GPU monitor export/summary failures could mark the ASR model as failed despite successful transcription | **FIXED in branch:** optional resource-report errors generate warnings and do not discard valid transcript or accuracy score; regression test added |
| F04 | MEDIUM | Source UI and runner comments claimed no actual execution/diarisation although the pilot runs ASR and optional pyannote | **FIXED in branch:** comments now reflect implementation |

### Outstanding publication blockers

| ID | Severity | Issue | Required evidence/action |
|---|---|---|---|
| P01 | **CRITICAL** | Raw reference and hypothesis may not have equivalent formatting: extracted DOCX paragraph breaks vs space-joined ASR segments; speaker labels, annotations and headings can remain if manually overlooked. Raw CER counts newline and spaces; WER uses whitespace tokens. These may systematically penalise ASR regardless of model quality | Audit actual DOCX structure, define and freeze the approved scoring protocol; demonstrate equivalence of comparison inputs. **Normalisation and DOCX layout remain HOLD** |
| P02 | **CRITICAL** | Comparability of all 11 ASR models is unproven: Faster-Whisper and Transformers/CTC/Qwen use different generation settings, 30-second chunks in optional adapters, language constraints, and FP16-CUDA vs possible CPU-INT8 fallback | Define a fair-comparison policy, record per-model decoding/configuration and actual device, run compatibility tests on Windows RTX 5070. **Model compatibility remains HOLD** |
| P03 | **HIGH** | Load vs inference time is not consistently separated. Optional `LocalASR` adapters load weights during generator iteration, while standard Whisper load time is measured separately. Inference RTF is not directly comparable across backends | Instrument standardised start/end timestamps around load, preprocess, inference and teardown. Make unavailable measurements NULL, not inferred |
| P04 | **HIGH** | Model checkpoint revisions, inference parameters, library versions and environment specifications are not captured consistently. Input hashes exist but do not by themselves guarantee reproducibility | Export environment and model-version manifest, ASR parameter registry, seed/config and equipment; independently reproduce a frozen test run |
| P05 | **HIGH** | WER/CER scorer is an internal dynamic-programming implementation without a verified benchmark against a trusted external scorer. Ties can alter S/D/I breakdown even if total edit distance agrees. Corpus and macro aggregates exist in helpers but are not fully integrated into publication tables | Cross-check with `jiwer` and independent NIST SCLITE test vectors, document tokenisation and exact denominator rules; verify micro/macro aggregation |
| P06 | **HIGH** | No verified handling of mismatched audio duration and reference span. The current pilot allows up to 180 seconds per audio but cannot certify whether a DOCX represents that exact time window | Check researcher-approved alignment of every audio clip and scoring reference before publication results. **Overlap/interruptions policy remains HOLD** |
| P07 | **HIGH** | No runtime execution test for pyannote Community-1 OSD on current Windows stack. Overlap is inferred from non-exclusive speaker-turn intersections, not a dedicated manually verified OSD classifier | Validate access, CUDA compatibility and diarisation output schema; test known synthetic and hand-labelled overlap excerpts; label estimate correctly |
| P08 | **MEDIUM** | GPU monitoring is from `nvidia-smi` device 0 (system-wide), not process-level model utilisation, and `psutil` RAM is system-wide. nvidia-smi polling at 0.5 seconds may miss short peaks; background processes confound measurements | Identify GPU/driver, add controlled-idle baseline and process-specific indicators where feasible; report sampling interval and limitations |
| P09 | **MEDIUM** | A checkpoint is saved after each model/audio, but automated resume/retry does not exist; cancellation is cooperative, and a stopped or partially processed batch needs careful handling | Implement run identity, checkpoint verification and safe recovery after all five methodological decisions permit it |
| P10 | **MEDIUM** | The DOCX parser extracts body paragraphs and table content but has not been validated with merged cells, tracked changes, field codes, text boxes, headers/footers or speaker annotations | Test de-identified representative Word layouts; retain editable researcher approval. **DOCX format remains HOLD** |
| P11 | **LOW** | Documentation contains historical implementation sections that are superseded by later commits; reading only the first page of implementation status can misrepresent current capabilities | Keep an explicit latest-status section and retain dated historical decisions for auditability |

## Research design safeguards

- **Do not publish any pilot score until P01–P05 are addressed.** The existing code is an experimental pipeline, not yet empirical evidence of model superiority.
- Keep *Human-verified DOCX → Preview → Approval → Freeze → Verified audio pairing*.
- Retain original and scoring text separately; never silently strip dialect forms or fillers.
- Optional Silero VAD and pyannote-derived overlap are descriptive only and must never modify the recorded WER/CER silently.
- Current code cannot provide DER/JER without a timestamped speaker ground truth. Do not claim DER/JER.
- Never commit study participants' audio, DOCX transcripts, frozen scoring text or local manifests to GitHub. The existing `.gitignore` ignores `output/`, `*.docx`, and common audio formats; this is a safeguard, not a substitute for checking every commit.
- Previous experimental reference manifests without `source_path` now require renewed approval to ensure source integrity.

## Code files reviewed

`benchmark_ui.py`, `benchmark_reference_ui.py`, `benchmark_ground_truth.py`, `benchmark_reference.py`, `benchmark_config.py`, `benchmark_pilot.py`, `benchmark_batch.py`, `benchmark_batch_ui.py`, `benchmark_metrics.py`, `benchmark_resources.py`, `benchmark_speech.py`, `model_options.py`, `asr_backends.py`, selected `redscribe_gpu.py` integration and synthetic test sources, requirements and `.gitignore`.

## Next controlled test

1. On Windows, run `python -m unittest discover -s tests -p "test_benchmark*.py"` and record **actual test results**, not just source-review status.
2. Open Tkinter UI and inspect Single and Batch modes, approval/re-approval, stop button, output files and exact pairing.
3. Run one de-identified 20–30-second audio with a matching researcher-verified reference and one ASR model.
4. Compare WER/CER with independent manually calculated examples; then test 2-audio batch and optional monitoring.
5. Only then test individual optional ASR models and VAD/OSD; record every runtime failure as evidence for resolving P02/P07.

This review is a **static audit**, not a CI or GPU test-pass certificate.
