# Consolidated scientific review and readiness assessment

## Decision at the feature freeze

| Decision | Satisfied criteria and evidence | Blocking evidence and next action | Conclusion |
|---|---|---|---|
| Documentation | Both modes traced separately. The [claim matrix](CLAIMS.md), [model inventory](MODELS.md), [references](REFERENCES.md), [11 figures](figures/README.md) and [numerical record](STATISTICS.md) expose the evidence behind principal claims. Public exports agree within recorded display precision. | Limited provenance and licence evidence are identified by model. A human methodological and editorial review remains necessary for manuscript use. | Suitable for technical and supervisory review with the recorded qualifications. |
| Software release | The Linux benchmark synthetic suite passed. PRs 27 and 28 were independently observed as merged into the development branch. A historical single-recording GPU run exists. | Broad regression tests report errors, GUI tests could not exercise the display, and fresh target-platform validation is outstanding. Resolve QA-01 and QA-02, then rerun and archive results for the release candidate. | Hold v2.1.0. |
| Empirical research | Reference preparation, model selection, paired comparisons and the timing boundary are documented. | Researcher must resolve [gates G1–G5](INTEGRITY.md), including authorisation, actual audio coverage and same-version repeatability, and approve the prospective analysis. | Hold the formal 25-recording comparison. |
| Publication | Public sample arithmetic is reproducible. A single recording illustrates feasibility. | The complete eligible cohort, frozen analysis, private provenance, rights review and independent expert scrutiny remain outstanding. | Evidence supports a pilot description only. A comparative performance claim across interviews is premature. |

## Regression and documentation QA

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
