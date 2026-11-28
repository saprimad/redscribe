# Draft release package for v2.1.0

**Disposition: hold.** This candidate adds structured comparative benchmarking to the desktop transcription workflow. The proposed release notes describe reference approval, model-major scheduling, checkpoint recovery, raw WER/CER and PDF/workbook reporting. The [readiness assessment](RELEASE_READINESS.md) distinguishes the documented single-recording pilot, synthetic regression and outstanding workstation acceptance. Release evidence must identify the exact candidate SHA.

## Proposed Zenodo deposit metadata

| Field | Proposed value or decision |
|---|---|
| Resource type and version | Software, 2.1.0 (proposed) |
| Title | RedScribe: Research Speech Transcription and Benchmarking System |
| Description | Desktop software for producing editable research transcripts and evaluating ASR pipelines against researcher-approved references. Structured benchmarking reports orthographic error, elapsed time and available resource measurements. |
| Keywords | automatic speech recognition, research transcription, benchmarking, word error rate, character error rate, Malay |
| Creators | Begin with the ordered creators and ORCIDs in [CITATION.cff](../../CITATION.cff). Obtain owner confirmation of spelling, order, affiliations and contribution to this version before submitting. |
| Prior identifier | Repository citation for v2.0.0 is 10.5281/zenodo.22941754. The live record could not be independently retrieved in this review. Verify its version lineage in the depositor account. |
| New identifier, date and repository | Leave DOI and publication date pending. Attach the approved immutable commit and release URL when available. |
| Software rights | PolyForm Noncommercial License 1.0.0, SPDX identifier PolyForm-Noncommercial-1.0.0. Include the full [licence](../../LICENSE) and applicable notices with the distribution. |

Zenodo treats a new version as a linked record with separate files, metadata and identifier. If using GitHub integration, Zenodo prioritises a root .zenodo.json over CITATION.cff when both exist. Decide the deposit route after checking the prior record and authorisation. [Zenodo versioning](https://help.zenodo.org/docs/deposit/manage-versions/) · [Software metadata](https://help.zenodo.org/docs/github/describe-software/) · [SPDX licence text](https://spdx.org/licenses/PolyForm-Noncommercial-1.0.0.html)

## Compatibility and upgrade

| Environment | Evidence and scope |
|---|---|
| Windows and Ubuntu, Python 3.11 | Synthetic and dependency jobs run on hosted systems. Inspect the exact candidate workflow results. CPU dependency imports do not exercise the CUDA adapters. |
| Windows NVIDIA workstation | Structured benchmarking requests CUDA FP16. Perform the [workstation acceptance procedure](../validation/WINDOWS_GPU_ACCEPTANCE.md) before release. |
| macOS | The desktop Faster-Whisper route supports CPU INT8. The strict CUDA benchmark requires NVIDIA hardware. Current candidate macOS runtime evidence is outstanding. |

Keep the existing installation, virtual environment, outputs and approved references. Check out the accepted revision into a separate directory and create a fresh Python 3.11 environment. Follow the platform-specific [installation instructions](../../README.md), install requirements-benchmark.txt for benchmarking and the selected optional adapter requirements where applicable. Run pip check and open both modes. Use synthetic speech and a disposable reference to exercise export, approval and resume. If a legacy manifest lacks source integrity evidence, reapprove against the original DOCX. Preserve earlier experiments separately. Resume only with the matching experiment identity. Return to the earlier checkout and environment if verification fails.

## Release checklist

1. Record the final SHA, successful candidate CI URLs and signed-off physical acceptance evidence. Resolve release-blocking issues in the readiness assessment.
2. Inspect the exact distribution contents, including nested archives, samples, author metadata and screenshots. Exclude private paths, raw interviews, credentials, manifests and unapproved study materials. Review consent and rights for each public example.
3. Keep model weights outside the archive. Dependencies, model publishers and converted checkpoints have distinct terms. Two Mesolitica licences and conflicting large-v3 declarations remain open for redistribution. See the [model inventory](MODELS.md).
4. Verify installer guidance, links, citations and licences on the candidate. Record filenames, file sizes and SHA-256 digests of the approved archive and evidence.
5. Obtain maintainer approval for the version, attribution, integration, tag and deposit. Assign the publication date and version-specific DOI only following the authorised release procedure. Check the final citation against the published record.

## Terminology for release notes

Use *Transcription Mode* for editable automated drafts; *Benchmarking Mode* for comparisons against an approved scoring reference. An approved reference is a frozen scoring artefact. *Raw WER/CER* denotes the implemented edit-based measures under their stated tokenisation. *RTF* measures inference interval divided by audio duration. *Historical runtime evidence* identifies a past run. *Synthetic regression* identifies fixture execution. Reserve *release acceptance* for a documented decision on a named candidate. The [citation register](REFERENCES.md) gives claim-specific qualifications.
