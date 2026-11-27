# RedScribe — Consolidated Development and Validation Record

**Record date:** 28 November 2026 (Malaysia time)  
**Project:** RedScribe — Research Speech Transcription and Benchmarking System  
**Development milestone:** Benchmarking feature freeze following integration of PR #28  
**Release target:** v2.1.0 (not yet tagged or published)

## 1. Executive summary

RedScribe has progressed from a research transcription application to a dual-mode desktop system supporting conventional transcription and reproducible comparative automatic speech recognition (ASR) benchmarking. The benchmarking workflow now integrates researcher-approved verbatim references, sequential GPU model execution, edit-distance metrics, resource monitoring, checkpointing and structured scientific publication exports.

A full-length, seven-model Windows GPU validation run was completed using one authentic Kelantan Malay conversational recording (P1) and a separately prepared speech-only verbatim reference. All seven observations completed with worker exit code zero. Independent arithmetic checks and selected file-integrity checks passed. Both benchmarking pull requests have been integrated into the benchmarking timeline branch; the stable main branch and official release remain separate.

## 2. Development chronology

| Milestone | Development and decisions |
| --- | --- |
| 16–17 November | Research design, eleven-model registry, seven default models, DOCX reference workflow, WER/CER foundations and initial benchmark UI. |
| 17–18 November | Experimental pilot and batch orchestration, reference integrity controls, resource monitoring, metric and runner audits, reporting foundations. |
| 24–26 November | Architecture refactor, defect closure, full-length GPU execution, faster metric implementation using RapidFuzz, worker isolation, scientific reporting and regression validation. |
| 26 November | Earlier full seven-model P1 baseline completed; preliminary reporting and scientific figures reviewed. |
| 26–28 November | Automated experiment management, explicit approval gates, single-window integration, live benchmark monitor, UI refinement and speech-only ground truth protocol. |
| 28 November | Full P1 runtime with cleaned reference, numerical and publication integrity review, PR #28 CI success and integration. |

Earlier design and implementation documents are historical records, not a description of the current interface. See the [development timeline](../REDSCRIBE_BENCHMARK_TIMELINE.md), [implementation history](../BENCHMARK_IMPLEMENTATION_STATUS.md) and [25 November validation record](FINAL_SOFTWARE_VALIDATION_2026-11-25.md).

## 3. Implemented benchmarking workflow

### 3.1 User interface and operation

- A single main window with independent Transcription and Benchmark workspaces; active mode indicator changes when switching modes. Mode switching is guarded during processing.
- Benchmark sidebar: Scientific Benchmarking overview, Dataset, ASR models and Benchmark settings. Redundant Output location section removed.
- Eleven selectable ASR models, seven selected by default; four legacy Whisper models remain optional.
- Current visible workflow is single-recording benchmarking. Earlier pilot/batch implementation is retained for compatibility and future work; multi-recording aggregation is not represented as a completed user-facing statistical module.
- Audio and matching DOCX selection; explicit Ground Truth Review and Configuration Review; approval indicators distinguish selection from approval.
- Ground Truth Review: four required verification checks; Approve & Freeze; automatic closure after successful verification. Selecting another audio or DOCX invalidates current approval.
- Configuration Review: three explicit confirmations, recording identifier, output location selection and persistent master directory. No manual JSON loading required for new single-recording experiments.
- Live benchmark monitor: model status, WER/CER, absolute substitutions/deletions/insertions, reference and hypothesis lengths, timing, device, precision and observed resource peaks.
- Start/Stop controls, guarded configuration changes, output-folder access and preservation of standard Transcription Mode as a separate workflow.
- Consistent RedScribe branding, British English interface wording, faculty attribution and scientific report header/footer.

### 3.2 Reference preparation and integrity

- Preserve original qualitative DOCX and audio; prepare a separate speech-only full verbatim reference.
- Retain audible interviewer and participant speech, regional vocabulary, fillers, repetitions, false starts and code-switching.
- Remove verified non-spoken speaker identifiers, annotations, gestures, editorial glosses and metadata. Re-listen to uncertain speech; do not invent missing words or equate removal of an annotation with masking its audio region.
- DOCX extraction and review, explicit researcher approval, SHA-256 source and frozen-text integrity, private reference manifest and confirmed audio pairing.
- All compared models use the same approved reference per recording. A reference change requires a new approved experiment and rerunning all compared models for a consistent comparison.
- The [Ground Truth Preparation and Verification Protocol](../benchmark/GROUND_TRUTH_PROTOCOL.md) version 1.0 contains a synthetic Kelantan dialect example, preparation rules, researcher checklist and numbered literature references. Bibliographic metadata should be independently checked before journal submission.

### 3.3 Scoring and model execution

- RapidFuzz Levenshtein edit operations, with word and character substitution, deletion and insertion counts.
- Raw WER uses whitespace-delimited tokens; raw CER uses Unicode code points, including punctuation, whitespace and line breaks. Case and orthography are retained. No automatic dialect standardisation.
- Corpus-level and macro-average reporting, with explicit denominators and missing observations excluded from valid accuracy calculations rather than assigned artificial zero scores.
- Sequential model execution with worker isolation, checkpoints, resume and integrity controls, private saved predictions and model revision metadata.
- Loading and inference timings recorded separately; RTF is inference time divided by source audio duration.
- Sampled system-wide GPU/VRAM, RAM, GPU utilisation and temperature observations where available. These are not model-exclusive allocations.
- Large-v3 native unload followed by controlled process exit is an explicit workaround for the earlier wrapper-destructor failure; the upstream destructor defect is not claimed resolved.

### 3.4 Scientific output and experiment organisation

Each new experiment receives a unique local output directory. The structured output separates publication materials from sensitive research state:

- `01 - Scientific Report.pdf`: executive summary, model inventory, environment, accuracy, error counts, length ratios, efficiency, scientific figures, integrity and interpretation.
- `02 - Scientific Results.xlsx`: model summary, recording results and efficiency data.
- `03 - Supporting Material/`: scientific figures, statistical CSV data and publication checksum manifest.
- `04 - SENSITIVE DATA/`: private checkpoint, reference manifests, prediction texts, experiment configuration, worker logs and internal export integrity manifest.

Report figures include corpus accuracy, edit composition and accuracy–speed trade-off; distribution graphics require multiple scored recordings for meaningful interpretation. Publication and private export manifests have distinct scopes. Folder separation is not encryption. No participant speech, private source paths, reference hashes or raw checkpoint material is reproduced in this record.

## 4. P1 full-length runtime validation

**Purpose:** final software validation and preliminary empirical evaluation; not the completed 25-recording study.

| Parameter | Recorded value |
| --- | --- |
| Recording duration | 2,261.969 s (37 min 42 s) |
| Reference words / characters | 4,692 / 29,298 |
| Models completed / selected | 7 / 7 |
| Worker exit codes | 7 / 7 zero |
| Runtime code commit | `df8d6a33ad5006a7f344281de4b7d7e67b894716` |
| Git working tree | Clean, as recorded by checkpoint |
| Platform | Windows; Python 3.11.9 |
| GPU | NVIDIA GeForce RTX 5070 |
| Driver / CUDA build | 610.88 / 13.0 |
| Recorded system RAM | 31.8 GiB |
| PyTorch / RapidFuzz | 2.10.0+cu130 / 3.14.3 |
| Language / device / precision | Malay (ms) / CUDA / float16, as recorded for all seven models |
| Resource monitoring | Enabled |

### 4.1 Descriptive results

| Model | WER (%) | CER (%) | Inference (s) | RTF | Peak observed GPU memory (MB) |
| --- | ---: | ---: | ---: | ---: | ---: |
| BuzzASR Malay | 71.38 | 32.78 | 297.57 | 0.1316 | 7165 |
| OpenAI Whisper Large-v3 | 73.44 | 35.88 | 226.24 | 0.1000 | 7468 |
| Qwen3-ASR 1.7B | 75.90 | 37.21 | 375.66 | 0.1661 | 6804 |
| OpenAI Whisper Large-v3 Turbo | 81.59 | 40.34 | 81.64 | 0.0361 | 4487 |
| Meta MMS 1B All (Malay) | 85.78 | 45.50 | 11.94 | 0.0053 | 4645 |
| Mesolitica Wav2Vec2 XLS-R 300M Mixed | 88.70 | 71.76 | 7.02 | 0.0031 | 3248 |
| Mesolitica Malaysian Whisper Large-v3 Turbo v3 | 113.30 | 62.45 | 137.12 | 0.0606 | 4164 |

BuzzASR had the lowest observed WER and CER for P1; XLS-R had the lowest measured RTF. The Mesolitica Whisper model had 2,644 word insertions and XLS-R had 3,319 word deletions. WER above 100% is mathematically possible. These error profiles motivate further investigation of dialect, speech rate, overlap, output length and processing coverage. Edit counts alone do not establish hallucination, truncation or a causal effect of rapid speech. Earlier baseline results retain the same WER ranking but used a different reference and ASR outputs; they do not establish same-version repeatability.

### 4.2 Evidence and validation scope

| Check | Result / scope |
| --- | --- |
| Seven worker logs | All contain INFERENCE PASS; six normal cleanups and one controlled Large-v3 exit after native unload |
| WER and CER | 14/14 recalculated from recorded integer edit counts and denominators |
| RTF | 7/7 recalculated from recorded inference and source duration |
| Model revisions | Seven revision identifiers recorded; exact loaded artefact and full decoding parameters still require verification |
| Configuration | Recorded audio/reference hashes, model selection, language and monitoring consistent between configuration and matrix; researcher confirmation recorded |
| Private matrix integrity | SHA-256 matches private manifest |
| Scoring DOCX integrity | SHA-256 matches recorded source DOCX hash |
| Published PDF and XLSX | 2/2 SHA-256 hashes match structured publication manifest |
| Remaining publication files | 16 supporting files listed in manifest; not independently checked in this consolidated audit |
| Audio and frozen scoring text | Actual bytes not independently rehashed here; source duration alone does not prove full processing |
| Audio coverage and timing | Actual per-chunk coverage and GPU-synchronised timing not independently established |
| Same-version repeatability | Pending controlled repeat run |

The arithmetic and four file-hash checks were repeated against the supplied local files when preparing this record. The private evidence is retained by the researcher outside GitHub. No claims of independently verified perfect transcription or general model superiority follow from this single-recording run.

## 5. GitHub integration and CI

| Item | Verified status |
| --- | --- |
| [PR #27](https://github.com/saprimad/redscribe/pull/27) | Merged into `redscribe-benchmark-timeline`; merge commit `595be61cbfd1b12c9c80da6df90ba9c749a0fa0b` |
| [PR #28](https://github.com/saprimad/redscribe/pull/28) | Merged into `redscribe-benchmark-timeline`; merge commit `46beecdf6cbb98047bb69fbe4fc70acd65d662ef` |
| PR #28 tested head | `97e95753d704eea3d31bdd807d970fb21e1df4d5` |
| [Benchmark runner synthetic tests](https://github.com/saprimad/redscribe/actions/runs/46032274274) | Success |
| [Benchmark dependency validation](https://github.com/saprimad/redscribe/actions/runs/46032274341) | Success |
| Difference from P1 runtime commit to PR #28 head | Ground truth protocol documentation only |
| Main integration and release | Pending |

CI success refers to the specified PR head and workflows, not an assertion that every future commit or GPU environment is validated. Standard merge preserves development history.

## 6. Feature freeze and remaining release gates

No additional features or redesign are planned for the current benchmarking release unless a defect or required validation correction is identified.

- [ ] Complete static and, where necessary, runtime audio-coverage audit for all seven model adapters; distinguish low recognition accuracy from incomplete input processing.
- [ ] Verify effective model revisions, complete decoding settings and timing methodology; assess same-version repeatability with the same audio and frozen reference.
- [ ] Verify remaining supporting-file integrity and final regression/CI status on the intended release candidate.
- [ ] Consolidate README, user guide, architecture, benchmark methodology, validation evidence, changelog and citation metadata. Preserve historical records and distinguish current behaviour from earlier proposals.
- [ ] Prespecify the statistical analysis protocol before the official comparative study; do not retrospectively choose tests based on the completed study outcomes.
- [ ] Review the integration candidate and merge to main only with author approval.
- [ ] Assign and tag v2.1.0, publish GitHub release and archive the corresponding version in Zenodo.

## 7. Planned Kelantan Malay ASR research

The proposed comparative study evaluates seven models across 25 authentic conversational interview recordings (175 planned model–recording observations). The recording is the paired analysis block; these are not 175 independent observations. The same interviewer across recordings may introduce additional dependence.

Planned research outcomes: recognition accuracy (WER primary; CER secondary), computational efficiency (inference, RTF and sampled resource peaks), and error profiles (substitution, deletion and insertion). Candidate analyses include corpus and macro estimates, Friedman omnibus tests, Wilcoxon paired comparisons with Holm correction, Kendall's W, paired effect sizes and recording-level bootstrap confidence intervals. Exploratory analyses of dialect forms, fillers, speech rate and overlap require suitable measurements and independent verification. The statistical plan, missing-data approach, multiplicity strategy and power considerations remain to be finalised; no inferential results are claimed.

Before official experiments, confirm ethics and consent coverage for secondary ASR use of interview audio, prepare and independently review speech-only references under the same protocol, and freeze the software/settings. Retain P1 development and validation evidence separately from the official cohort unless its eligibility under the final prespecified protocol is established. Potential manuscripts include a software-focused paper and a distinct empirical ASR evaluation. Journal scope, novelty and bibliographic details require literature review; no publication outcome is implied.

## 8. Current operating instructions

On the Windows workstation, close RedScribe before switching versions:

```powershell
git fetch origin
git switch --detach origin/redscribe-benchmark-timeline
git log -1 --oneline
python -X faulthandler -u redscribe_gpu.py
```

For exact reproduction of the validated P1 software code, use the runtime commit in Section 4 rather than a moving branch. Keep experiment folders, original audio, DOCX references, manifests and outputs locally protected.

**Milestone conclusion:** The benchmarking feature branch has been integrated and the full-length P1 runtime and selected integrity gates have passed. The next phase is scientific documentation and completion of outstanding release validation, not new feature development.
