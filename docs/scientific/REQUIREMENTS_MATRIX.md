# Software requirements and verification matrix

Revision inspected and exercised: `24cafc03effd13d88f61b2167216cf358d90ce18`. Requirements below describe operational invariants. The 12 linked test modules ran locally on Linux using Python unittest. All 54 tests passed, with zero skips, errors or failures. These module totals reflect every case in the named module. Multiple behaviours can share one test. This run exercised synthetic fixtures and mocked services.

| ID | Requirement and observable acceptance criterion | Verification evidence and number of tests passing | Validation still required for research use |
|---|---|---|---|
| R01 | All 11 model choices map to the supported runtimes and distinct stable output folders. Failed preflight prevents entry into transcription. | [Model choices and preflight](../../tests/test_model_options.py) · 14 | Test each selected native runtime on the intended workstation. |
| R02 | Extra adapters retain valid chunk ranges, reject invalid configuration and apply architecture-specific decoding controls. | [Adapter contracts](../../tests/test_asr_backends.py) · 14 | Measure consumed samples and tail coverage using the effective weights and real recordings. |
| R03 | Approval binds the reviewed text to source bytes and detects subsequent changes. | [Reference approval and tampering](../../tests/test_benchmark_reference.py) · 10 | Independently listen to the full reference span and adjudicate disputed content. |
| R04 | Dataset approval rejects duplicate inputs and detects changes to approved pairs. | [Pair approval](../../tests/test_benchmark_dataset.py) · 1 | Researcher verifies the actual audio–reference correspondence. |
| R05 | The scheduler orders work by model, contains failure within that session and closes sessions on cooperative stop. | [Model-major scheduling](../../tests/test_benchmark_model_major.py) · 3 | Exercise native worker termination and resume on target hardware. |
| R06 | A failed matrix replace preserves previous on-disk and in-memory state. | [Injected write failure](../../tests/test_benchmark_checkpoint_write_failure.py) · 1 | Evaluate interruption and storage behaviour on the actual experiment volume. |
| R07 | The strict benchmark configuration rejects unsupported device and precision. | [Configuration checks](../../tests/test_benchmark_configuration.py) · 1 | Capture effective device and precision for each empirical session. |
| R08 | Matrix restart reuses only a completed cell accepted by its verification callback. | [Checkpoint restart](../../tests/test_benchmark_matrix_checkpoint.py) · 1 | Check saved prediction hashes and reference hashes during a controlled interrupted native run. |
| R09 | Runtime provenance has the implemented schema. | [Runtime provenance](../../tests/test_benchmark_provenance.py) · 1 | Confirm effective model revisions, runtime artefacts and hardware at experiment start. |
| R10 | The output lock rejects a conflicting writer and releases after an exception. | [Lock behaviour](../../tests/test_benchmark_output_lock.py) · 2 | Confirm the operating filesystem supports the required semantics. |
| R11 | Counts respect reference/hypothesis lengths and reject impossible combinations. | [Count identities](../../tests/test_benchmark_extended_counts.py) · 3 | Independently reproduce scores from approved references and saved hypotheses. |
| R12 | Raw scoring and aggregation respect literal characters, whitespace tokenisation and unequal recording lengths. | [Metric validation](../../tests/test_benchmark_metric_validation.py) · 3 | This suite exercises the legacy metric implementation. Verify the structured RapidFuzz scorer separately before interpreting alignment components. |

Reproduce the local checks from repository root using `python -m unittest discover -s tests -p test_model_options.py`, substituting each linked basename in turn. See the [technical interfaces](TECHNICAL_REFERENCE.md) and [claim-to-evidence matrix](CLAIMS.md) for corresponding code symbols. For scientific readiness, recording-level reference agreement, target-hardware execution, measurement repeatability, consent and human review have separate acceptance criteria in the [readiness assessment](RELEASE_READINESS.md).

## Cross-mode acceptance

The following tests passed within the 228-case regression suite. The acceptance column identifies the remaining native observation or review. [Platform evidence](VALIDATION_EVIDENCE.md)

| Requirement | Implementation | Regression evidence | Acceptance |
|---|---|---|---|
| Mode switching restores the transcription workspace and excludes concurrent ASR workers | [Desktop](../../redscribe_gpu.py), [guard](../../redscribe/ui/operation_guard.py) | [Tk layout](../../tests/test_desktop_layout.py), [exclusion](../../tests/test_benchmark_operation_guard.py) | Exercise both modes while idle and busy on Windows. |
| Cancellation and error recovery restore controls after cleanup | [Desktop worker](../../redscribe_gpu.py) | [Completion and export failure](../../tests/test_run_completion.py) | Cancel a native run and successfully start the next. |
| Optional diarisation reports progress and preserves speaker labels in Word and Excel | [Desktop](../../redscribe_gpu.py) | [Diarisation status](../../tests/test_diarization_status.py), [speaker exports](../../tests/test_speaker_exports.py) | Open both outputs and check against authorised speech. Time-aligned labels are needed to measure diarisation error. |
| Structured scoring preserves raw word and character distances | [RapidFuzz scorer](../../redscribe/benchmark/benchmark_fast_metrics.py) | [Fast scorer](../../tests/test_benchmark_fast_metrics.py) | Check private prediction and reference identities before rescoring. |
| Efficiency outputs distinguish elapsed request time from load time and report sampled system peaks | [Resource sampler](../../redscribe/benchmark/benchmark_resources.py), [reporting](../../redscribe/benchmark/benchmark_reporting.py) | [Reporting](../../tests/test_benchmark_reporting.py) | Verify the sensor, device, sampling cadence, time boundaries and RTF denominator on native hardware. |
| PDF and Excel derive from eligible observations and declared artefacts retain their digests | [Structured exports](../../redscribe/benchmark/benchmark_structured_output.py) | [Publication](../../tests/test_benchmark_publication.py), [export integrity](../../tests/test_benchmark_export_integrity.py) | Reopen native exports, compare counts and verify each manifest. |
