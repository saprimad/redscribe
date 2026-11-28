# Supervisor briefing and publication plan

## Decision sought

Endorse the design for a prospective comparison of seven automatic speech recognition pipelines on 25 conversational Kelantan Malay interviews, subject to written confirmation of permitted secondary use, workstation acceptance and approval of the analysis protocol. Separately decide whether the intended scholarly contribution is the reusable research software, the empirical speech evaluation, or two papers with distinct questions and cross-disclosure.

## What the evidence supports

RedScribe provides a desktop transcription workflow with editable research outputs and a separate benchmarking workflow that pairs model predictions with approved references. On the historical P1 recording all seven selected models produced scored observations. Independently reopening the public PDF and workbook confirmed their WER, CER, output-length and real-time-factor arithmetic. WER ranged from 71.38% to 113.30% on this recording. Insertions can drive WER above 100%. One interview cannot establish model superiority across Kelantan speakers, and export agreement cannot verify every input sample reached inference. The test evidence includes synthetic workflows and cross-platform regression. Physical GPU acceptance remains a separate decision. [Numerical evidence](STATISTICS.md) · [Validation history](RELEASE_READINESS.md) · [Target workstation procedure](../validation/WINDOWS_GPU_ACCEPTANCE.md)

## Decisions before official recruitment-data reuse

| Decision owner | Decision and evidence required |
|---|---|
| Researcher and relevant ethics authority | Establish whether approval and consent cover secondary ASR evaluation and which summaries may be published. Keep speech, transcripts, identifiable paths and restricted manifests in authorised storage. |
| Workstation operator | Record target-platform acceptance, effective model revisions, decoding configuration, full-audio coverage and repeatability. Document unresolved failures before including observations. |
| Researcher, supervisors and statistician | Freeze primary recording-level WER contrasts, reference version, retry rules and complete-cohort criteria before the full run. Treat recordings as paired blocks. Disclose pilot reuse and shared-speaker dependence. |
| Authors | Agree contributions, responsibility for verification, disclosure of AI assistance, archive policy and the scope of each manuscript before submission. |

The planned 175 model–recording observations represent up to 25 paired blocks. Report common-cohort and available-case results, absolute edit counts, reference denominators, corpus and recording-level rates, uncertainty and coverage exceptions. The existing protocol explains how to handle skew, ties, incomplete blocks and 21 candidate pairwise comparisons. [Analysis protocol](STATISTICS.md) · [Research integrity gates](INTEGRITY.md)

## Publication routes

| Route and working title | Contribution, evidence and submission decision |
|---|---|
| Software paper — *RedScribe for local research transcription and reproducible ASR benchmarking* | Describe the research need, architecture, human reference approval, recovery, provenance and verifiable exports. Provide an installable environment, a reusable synthetic example, tests and comparison with existing tools. **JOSS is ineligible under the present licence.** Its submission rules require an OSI-approved licence. The repository specifies PolyForm Noncommercial 1.0.0. If the rights holder elects to retain the licence, exclude JOSS from the submission shortlist. The development-history, research-use, packaging and AI-disclosure requirements also need assessment before any future submission. [Repository licence](../../LICENSE) · [JOSS submission requirements](https://joss.readthedocs.io/en/latest/submitting.html) · [JOSS review checklist](https://joss.readthedocs.io/en/latest/review_checklist.html) |
| Empirical paper — *Recognition error and computational efficiency across seven ASR pipelines for conversational Kelantan Malay* | Computer Speech & Language publishes original experimental research on spoken language processing, including recognition. Consider it once the complete authorised study supports an original speech-research question. Explain the dialect and interview setting, reference production, matched comparisons, timing scope, sampling limits and interpretation of deletion/insertion patterns. Evaluate novelty against recent work and seek an independent speech-methods review. The archived P1 report can illustrate feasibility. [Publisher scope](https://shop.elsevier.com/journals/computer-speech-and-language/0885-2308) · [ISCA journal description](https://www.isca-speech.org/Publications) |

For a software manuscript, assemble a fresh-install walkthrough and synthetic outputs that a reviewer can regenerate. For the empirical manuscript, freeze the protocol, record authorisations, execute the complete study and have a second analyst independently reproduce the principal results within the permitted environment. Publication material should state which artefacts can be shared, the grounds for restricted access and the available verification route. Recheck the chosen venue’s instructions immediately before submission.
