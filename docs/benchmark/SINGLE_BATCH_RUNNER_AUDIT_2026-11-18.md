# Single / Batch Benchmark Runner — Code Audit and Reliability Changes

**Audit date:** 18 November 2026  
**Branch:** `redscribe-benchmark-timeline` (experimental; `main` unchanged)  
**Target:** Reliability and transparent reporting for a future defensible IEEE ASR-comparison study.

## Scope and testing honesty

Inspected the source for `benchmark_pilot.py`, `benchmark_batch.py`, `benchmark_ui.py`, `benchmark_batch_ui.py`, `benchmark_reference.py`, `benchmark_config.py`, `benchmark_resources.py`, `model_options.py`, `asr_backends.py` and the existing synthetic tests. Examined single-model continuation, source preflight, human-paired references, cancellation, batch failures, per-model reporting, resource monitoring, cleanup and CSV/JSON persistence.

**Tests added** in `tests/test_benchmark_runner_integrity.py` include: failed recording still represented in batch CSV; cancellation before a batch; audio changed after preflight; cancellation during a single run; remaining models marked `not_run`; a model failure followed by successful next model; monitor startup/shutdown faults; cleanup fault; expected hash mismatch; child cancellation preserving pending recordings.

**Runtime limitation:** Code and tests were committed. GitHub Actions synthetic test workflow `.github/workflows/benchmark-tests.yml` was created to compile the benchmark modules and run `python -m unittest discover -s tests -p "test_benchmark*.py" -v` without ASR weights. Its run conclusion could not be inspected through the available connector. **Do not report CI as PASS or claim RTX 5070/Windows GUI testing.** Full GPU inference, live app and all eleven models remain untested here.

## Findings and corrective actions

| ID | Severity | Finding before audit | Corrective action |
|---|---|---|---|
| R01 | HIGH | `batch_results.csv` silently omitted recordings that failed before any model produced a result | **Fixed:** output always contains a row per failed, cancelled or pending recording; columns include `recording_status` and `recording_error` |
| R02 | HIGH | Audio was hashed during batch preflight but not compared again at execution | **Fixed:** audio hash rechecked immediately before each recording; `run_single_pilot` validates `expected_audio_sha256` too |
| R03 | HIGH | `results.csv` and `batch_results.csv` were overwritten directly, risking truncation if interrupted mid-write | **Fixed:** temporary CSV is written and replaced atomically, as already done for JSON manifests |
| R04 | HIGH | On cancellation, unattempted ASR models could be absent from the output CSV | **Fixed:** selected models still not attempted are labelled `not_run` with null WER/CER; active cancelled model remains `cancelled` |
| R05 | MEDIUM | `model.close()` errors could override a completed model transcription | **Fixed:** model teardown and CUDA cache cleanup are best-effort with warnings, never replacing a correct score with a cleanup failure |
| R06 | MEDIUM | Resource monitor start/stop or report problems could incorrectly mark ASR inference as failed | **Fixed:** independently catch monitoring setup, teardown and export errors; preserve actual ASR result while flagging monitoring warning |
| R07 | MEDIUM | A recording failure's cause was visible in JSON but missing in aggregate CSV | **Fixed:** include the recording-level error in the batch CSV |
| R08 | MEDIUM | Existing automated tests did not cover failed-first-recording continuation, mid-run cancellation, and skipped-model status | **Added:** synthetic/mock regression tests covering these cases |
| R09 | MEDIUM | No repeatable automated benchmark-only check in repository | **Added:** dedicated GitHub Actions workflow on experimental branch; CI outcome still unverified |

## Current status semantics

- **Model `completed`:** ASR generated hypothesis, scoring and transcript output saved; no claim about correctness of the model's recognised words.
- **Model `failed`:** model could not complete; WER/CER remain empty, not zero.
- **Model `cancelled`:** a cooperative cancellation interrupted the model operation.
- **Model `not_run`:** this selected model was not reached before the single run stopped.
- **Recording `failed`:** error prevented or interrupted that recording's run (see `recording_error`); later recordings may still proceed.
- **Recording `pending`:** recording was not reached, including after batch cancellation.
- **Batch `completed_with_errors`:** batch ended and at least one audio did not complete; do not interpret as a complete comparison.
- **Batch `cancelled`:** cancellation stopped remaining recordings.
- **Batch `completed`:** every recording finished with each selected model marked completed; says nothing about scientific validity.

**CSV compatibility notice:** `batch_results.csv` now adds recording-level status/error columns and placeholder rows, and changes `batch_manifest.json` schema version to 2. Downstream analysis must filter `model_key` nonempty and model `status=completed` for accuracy/RTF comparisons, while reporting failed/pending counts separately. Do not average missing or failed WER/CER as zero. The `results.csv` field names remain the same, with additional `not_run` rows after cancellation.

## Outstanding research and reliability limitations

1. **Resume is not implemented.** Atomic checkpoints permit auditing/intermediate recovery, but automatically resuming a batch safely requires separate design and tests.
2. **GPU/Windows not validated.** Synthetic tests do not prove Qwen, Mesolitica, MMS, BuzzASR or Whisper model weights will run on RTX 5070, Windows CUDA, or pyannote.
3. **Runtime timing is not fair across backends yet.** Lazy-loaded optional models include loading in `transcription_seconds`; Faster-Whisper separates model load. The RTF cannot be treated as comparable across all backends until instrumentation is standardised.
4. **Scientific ground-truth alignment is not automatic.** Approval checklist and hashes cannot prove that the DOCX corresponds to precisely the audio clip being benchmarked.
5. **Monitoring is observational.** GPU 0 system-wide utilisation and 0.5-second sampling cannot guarantee per-process peak VRAM accuracy.
6. **Nonexclusive diarisation overlap** is not independently validated overlap-event ground truth; VAD/OSD do not change raw WER/CER.
7. **A power loss or forced process termination** can leave a batch with `running` status in the latest JSON checkpoint; no automatic crash-resume or terminal-state reconciliation exists.
8. **CSV/JSON writes are separately atomic, not one combined transaction.** Interrupted execution can leave different checkpoint generations; inspect run timestamps/statuses in recovery.
9. **No verified publication-grade scoring policy** for BM/English/Kelantan; five previously deferred methodology decisions stay HOLD.
10. **Pilot input limit remains 180 seconds per audio**, not full interviews. The review does not change this.

## Controlled verification on desktop

```powershell
git fetch origin
git switch redscribe-benchmark-timeline
git pull --ff-only
python -m pip install python-docx
python -m unittest discover -s tests -p "test_benchmark*.py" -v
python redscribe_gpu.py
```

Run a synthetic/non-sensitive audio + approved matching DOCX first; choose a single model with VAD/OSD disabled. Test 2–3 recordings and two models, simulated invalid reference/changed audio, one deliberately unavailable model, cancellation mid-run and reopening both CSV/JSON outputs. Capture exact console output, Git SHA, OS, driver, Python and CUDA versions. Do not publish preliminary WER, CER or RTF.

**Bottom line:** Reliability and failure transparency improved through focused code changes. The experimental runner is not yet verified for IEEE publication-quality 11-model benchmarking.
