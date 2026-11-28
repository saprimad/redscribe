# Consolidated scientific review and readiness assessment

## Current corrective validation

The [central validation evidence summary](VALIDATION_EVIDENCE.md) links seven verified jobs at final PR head 61a9acb, identifies the earlier tested revision and records the evidential scope of the merge.

The full Linux suite on an isolated checkout of 5da7f53 ran 228 tests with zero failures, errors or skips. All nine real Tk cases ran, including the added switch from transcription to benchmarking and back. The test launcher fails on an empty discovery or any skip. The ten completion tests and eleven token UI tests also passed independently. Additional targeted modules passed for operation exclusion (1), session lifecycle (2), reference handling (10), fast scoring (3), resume (1), publication (1), ground-truth integrity (3), export integrity (1) and matrix checkpoint persistence (1). These are subsets of discovery. Cancellation, model cleanup and completion are covered by the same suite. The 175-cell stress fixture uses injected sessions and synthetic inputs.

An exploratory run during a changing checkout rejected a resume identity. The benchmark records Git revision and worktree state in the checkpoint identity. The clean detached rerun passed with the guard intact. All six published synthetic WER/CER examples retained the expected word and character edit distances. Rechecking the two archived sample hashes ties this review to the numerical record already on file. The workflow checks paths, numbered claims and citations, model labels, vector sources, captions and sample digests. Bibliographic interpretation and empirical validity still depend on the documented evidence.

| Decision | Current disposition |
|---|---|
| A. Documentation | Suitable for supervisory review. The previous numerical, licensing and citation qualifications continue to apply. |
| B. Software | QA-01, QA-02 and the automated display portion of QA-03 pass on Linux and Windows. The target machine must complete the [Windows GPU acceptance procedure](../validation/WINDOWS_GPU_ACCEPTANCE.md). Withhold main integration and release until physical acceptance is recorded. |
| C. Empirical research | The authorised custodian must resolve G1–G5, including permission, effective model identities, coverage and repeatability, before the official experiment. The 25 recordings are unnecessary for fixture closure. |
| D. Publication | Evidence supports describing the P1 pilot. Comparative publication requires the authorised full study, completed analysis and independent review. |

On candidate 5da7f53 the [cross-platform full regression and documentation jobs](https://github.com/saprimad/redscribe/actions/runs/46078097846) passed. Windows and Ubuntu each executed 228 tests with zero failures, errors and skips, including nine Tk tests. Ubuntu also executed the isolated nine-test GUI job step. The [benchmark regression](https://github.com/saprimad/redscribe/actions/runs/46078098039) passed 107 tests per OS. The [clean dependency workflow](https://github.com/saprimad/redscribe/actions/runs/46078097796) exercises the declared base and benchmark libraries with CPU PyTorch. Optional adapter CUDA imports and native inference require the workstation.

## Historical decision at the documentation freeze (02a7f83)

| Decision | Satisfied criteria and evidence | Blocking evidence and next action | Conclusion |
|---|---|---|---|
| Documentation | Both modes traced separately. The [claim matrix](CLAIMS.md), [model inventory](MODELS.md), [references](REFERENCES.md), [11 figures](figures/README.md) and [numerical record](STATISTICS.md) expose the evidence behind principal claims. Public exports agree within recorded display precision. | Limited provenance and licence evidence are identified by model. A human methodological and editorial review remains necessary for manuscript use. | Suitable for technical and supervisory review with the recorded qualifications. |
| Software release | The Linux benchmark synthetic suite passed. PRs 27 and 28 were independently observed as merged into the development branch. A historical single-recording GPU run exists. | Broad regression tests report errors, GUI tests could not exercise the display, and fresh target-platform validation is outstanding. Resolve QA-01 and QA-02, then rerun and archive results for the release candidate. | Hold v2.1.0. |
| Empirical research | Reference preparation, model selection, paired comparisons and the timing boundary are documented. | Researcher must resolve [gates G1–G5](INTEGRITY.md), including authorisation, actual audio coverage and same-version repeatability, and approve the prospective analysis. | Hold the formal 25-recording comparison. |
| Publication | Public sample arithmetic is reproducible. A single recording illustrates feasibility. | The complete eligible cohort, frozen analysis, private provenance, rights review and independent expert scrutiny remain outstanding. | Evidence supports a pilot description only. A comparative performance claim across interviews is premature. |

## Historical regression and documentation QA (02a7f83)

Local platform was Linux, Python 3.12.14. A disposable environment supplied the repository-pinned RapidFuzz 3.14.3 and JiWER 4.0.0. An initial broad run without them produced dependency errors and was superseded. The second run of the workflow's benchmark discovery command passed **107 tests**. Full discovery ran **227 tests**, reported **14 errors** and skipped **8** Tk display tests. Errors include subtest outcomes. These are local observations. The synthetic workflow uses Python 3.11 and filters documentation-only pushes. No fresh Windows or CUDA result is asserted.

| ID | Severity and evidence | Implication, reproduction and disposition |
|---|---|---|
| QA-01 | Major regression-test defect. In tests/test_run_completion.py the fixture constructs the desktop app via __new__. Ten cases encounter a missing mode_button used by control restoration in redscribe_gpu.py. The real constructor creates the button. | Run python -m unittest discover -s tests -p test_run_completion.py. Extend the fixture to cover actual UI state and rerun with a Tk smoke test. Current evidence prevents certifying completion/error recovery; a live desktop crash has not been reproduced. Open under the software freeze. |
| QA-02 | Major regression-test defect. Four subcases of test_worker_receives_resolved_saved_token_only_with_diarisation in tests/test_token_ui.py construct an app without the active_mode read by start in redscribe_gpu.py. | Run python -m unittest discover -s tests -p test_token_ui.py. Correct the fixture and recheck token handoff with a synthetic identity. Blocks certification of the tested behaviour. No credential exposure was observed. |
| QA-03 | Runtime evidence unavailable. Eight desktop layout tests explicitly skip for lack of a Tk display. | Run the full suite in a display-enabled environment and perform the normal transcription and benchmark launch checks on the target workstation. |

## Six simulated review perspectives

| Review | Finding and correction | Revalidation and remaining limitation |
|---|---|---|
| A, methodology | Four findings cover hypothesis persistence, estimated timestamps, telemetry and attribution. | [A01–A04 and implementation checks](CLAIMS.md). |
| B, architecture | The reachable UI route differs from the impression given by an older module header. | [Source locations, 11 figure captions and review](figures/README.md). Static call paths do not measure actual audio coverage. |
| C, statistics | Treating seven model runs on one interview as independent would give invalid inference. | [Paired protocol and independent arithmetic](STATISTICS.md). Empirical inference awaits the full cohort. |
| D, integrity | Public sample digests establish byte agreement. Research permissions, runtime identity and corpus-level generalisation remain open. | [Integrity findings and verification procedures](INTEGRITY.md). |
| E, editorial | Current-facing navigation contained a stale development branch and status. | [Corrections, sample rendering and citation metadata](EDITORIAL.md). |
| F, adversarial | Major. A green benchmark-only suite could mask errors in transcription tests. Major. Matching exported metrics could be misread as independent rescoring. Minor. Half-unit rounding differs for two resource readings. | Broad discovery exposed QA-01 and QA-02. Reopened the numerical record to distinguish exported-count arithmetic from unavailable private text alignment. Documented the rounding tolerance. Reviewers must request authorised coverage and repeatability evidence before accepting cross-model claims. |

The six reviews are simulated. The pilot's orthographic error rates describe particular pipelines, a particular reference and one interview. They cannot establish accuracy for Kelantan Malay speakers generally. No new critical software failure was independently demonstrated. Existing major gates above remain open. The [master index](README.md) identifies every evidence document. The [task register](TASK_REGISTER.md) maps the assignment to deliverables.
