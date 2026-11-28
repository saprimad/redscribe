# Validation evidence by revision

PR #29 corrected desktop test fixtures and added display-enabled regression tests. The table records GitHub job conclusions and the test counts read from the job logs for the final PR head, 61a9acb. The two benchmark jobs exercise a subset of the full suite. The additional Ubuntu GUI run repeats tests also included in full discovery.

| Evidence | Windows | Ubuntu | Scope |
|---|---|---|---|
| Full discovery | [228 passed, zero skips](https://github.com/saprimad/redscribe/actions/runs/46078472907/job/140771660835) | [228 passed, zero skips](https://github.com/saprimad/redscribe/actions/runs/46078472907/job/140771661075) | Each log reports zero errors and failures. Ubuntu separately ran all nine Tk tests under a virtual display. |
| Synthetic benchmark | [107 passed](https://github.com/saprimad/redscribe/actions/runs/46078472892/job/140771660979) | [107 passed](https://github.com/saprimad/redscribe/actions/runs/46078472892/job/140771660735) | Compilation and benchmark unit tests without model downloads. |
| Dependency checks | [Passed](https://github.com/saprimad/redscribe/actions/runs/46078472898/job/140771660769) | [Passed](https://github.com/saprimad/redscribe/actions/runs/46078472898/job/140771661171) | CPU PyTorch, declared base and benchmark dependencies, consistency check and imports. |
| Documentation checks | — | [Passed](https://github.com/saprimad/redscribe/actions/runs/46078472907/job/140771661094) | The repository validator ran against the PR checkout. |

The earlier test commit 5da7f53 also passed on both platforms. Its full-suite logs report 228 tests on each OS, its Ubuntu GUI step reports nine and its benchmark subset reports 107 per OS. Its three runs are linked in the [readiness assessment](RELEASE_READINESS.md). The merge commit was 24cafc0. Git comparison between 5da7f53 and that merge lists documentation changes only. The [post-merge push workflow](https://github.com/saprimad/redscribe/actions/runs/46078817753) passed at 24cafc03effd13d88f61b2167216cf358d90ce18. Windows and Ubuntu each ran 228 tests without errors, failures or skips. Scientific documentation checks also passed.

## Scientific interpretation

The synthetic tests exercise scheduling, export generation, raw-score calculation, resume and failure paths using controlled inputs. The [claim matrix](CLAIMS.md) provides symbols and evidence categories. The reviewed [numerical record](STATISTICS.md) recalculates rates from the published counts. Fresh alignment of the private hypothesis against the approved private reference requires the original material. Repeating exported arithmetic cannot establish end-of-file coverage, timing validity or transcript fidelity. In particular, neither 228 tests nor 175 synthetic model-recording cells is a sample size for inference about ASR performance.

The [target workstation procedure](../validation/WINDOWS_GPU_ACCEPTANCE.md) specifies native software acceptance. Research governance, reference eligibility and paired empirical analysis have their own [integrity gates](INTEGRITY.md). Record the exact tested revision, artefact identities and outcome before updating the corresponding readiness decision.
