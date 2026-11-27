# Documentation audit and gap analysis — 28 November 2026

**Scope:** targeted static review of the integrated benchmarking branch; not a complete repository inventory, independent runtime audit or external peer review. Feature freeze applies. Historical records remain intact.

## Reviewed evidence

- Root README, CITATION.cff, requirements, documentation indexes, benchmark architecture, reference protocol, consolidated validation record and sample output navigation.
- Desktop entry point, model registry, local ASR adapters, diarisation options, performance logger.
- Benchmark configuration, UI and matrix UI, reference extraction and approval, experiment manager, structured publication route, legacy pilot/batch, legacy and fast metrics, resource sampler, reporting and publication modules.
- PR #27/#28 integration and prior CI evidence as recorded in the consolidated record. Rechecking the exact PR head and test logs remains separate from current-branch testing.

## Findings

| ID | Severity | Finding / source | Correction or gate |
|---|---|---|---|
| D01 | Major | Root README describes seven-model run as pending, calls PR #27 draft and directs cloning an earlier branch. | Update current overview; retain dated evidence. |
| D02 | Major | Benchmark index and architecture retain November 18–25 statements that GPU/CI are unverified. | Add latest milestone and label earlier descriptions historical. |
| D03 | Major | Legacy pilot uses benchmark_metrics.py (dynamic programming); structured path uses benchmark_fast_metrics.py (RapidFuzz). | Distinguish routes and alignment conventions; never transfer tie-breaking guarantees. |
| D04 | Major | Single-recording visible workflow differs from retained batch/pilot implementation. | Document interface scope separately from underlying modules. |
| D05 | Major | Current code partitions LocalASR audio into intervals of at most 30 seconds; this is static design evidence, not proof of actual processed coverage for all models. | Retain runtime coverage gate, including sample counts and end-of-file verification. |
| D06 | Major | Recorded model revisions do not establish pinned downloaded artefacts; backend decoding and timing differ. | Verify effective weights, parameters and GPU timing before formal study. |
| D07 | Major | Resource sampler is system-wide; nominal interval 0.5 s plus collection latency; unavailable values can be null. | Avoid calling observed peaks model-exclusive or true maxima. |
| D08 | Major | Existing P1 summary reports private hash/log checks that this pass cannot independently reproduce without private files. | Attribute historical checks; do not certify them anew. |
| D09 | Major | Sample reports retain pseudonymous P1 and real results. Public sharing permission not established by redaction. | Researcher/ethics review required; no new private data publication. |
| D10 | Major | Ground truth protocol has eight references with incomplete independent metadata/claim verification. | Citation register marks verified and outstanding sources separately. |
| D11 | Major | No timestamped reference diarisation; speaker labels alone cannot establish DER/JER. | Explicit limitation in Part I/II. |
| D12 | Major | No same-version repeatability evidence or completed 25-recording analysis. | Prespecify paired analysis and repeatability protocol. |
| D13 | Minor | CITATION.cff describes v2.0.0 and prior DOI; authorship spelling and release metadata need owner verification. | Preserve archival citation; defer changes to approved release. |
| D14 | Minor | Existing workflow figures may reflect earlier batch/pilot UI and optional speech analysis. | Label historical; create current route diagrams from source. |
| D15 | Major | Legacy pilot rescoring uses a different edit-count algorithm from model-major scoring. | Do not interpret legacy offline rescoring as independent verification of identical S/D/I for current route. |
| D16 | Minor | Scientific publication code creates distribution figures even with one common recording. | Explain that one-recording distribution is not informative; no engine change in this task. |

## Audit boundaries

No full checkout, complete tree enumeration, execution of repository tests or local GPU access was established in this pass. Public source files and existing records support the targeted findings, not a release certificate. Model card licence/revision verification, full code-path inspection, original private evidence and independent human review remain gates. No claim of IEEE/JOSS compliance.

## Follow-up on the checked-out development branch

The earlier audit boundaries above describe the original review. The follow-up used the complete tree at d2ab724, reopened both public sample files, verified byte digests, and executed benchmark and full regression discovery. D01–D04 are addressed in current navigation and diagrams. D08 and D09 remain restricted-evidence and governance gates. For D10 see the citation-by-citation register. D16 concerns generated chart assets; PDF inclusion and export generation have distinct conditions. See the [integrated review](RELEASE_READINESS.md), [numerical verification](STATISTICS.md), [citation register](REFERENCES.md) and [current figures](figures/README.md). Historical validation documents remain dated evidence.
