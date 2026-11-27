# RedScribe — User Guide and Demonstration

**Research Speech Transcription and Benchmarking System**

**Documentation snapshot:** 28 November 2026 | Windows benchmarking workflow | Runtime commit `df8d6a3`

This guide documents the single-recording scientific benchmarking workflow demonstrated during the seven-model validation run. For the reference preparation method and validation evidence, see the [Ground Truth Protocol](../benchmark/GROUND_TRUTH_PROTOCOL.md) and [Consolidated Development and Validation Record](../validation/CONSOLIDATED_DEVELOPMENT_RECORD_2026-11-28.md).

## 1. Ground Truth Review

Select an audio recording and its corresponding speech-only verbatim DOCX. Review the separate scoring text against the recording. Preserve spoken dialect, fillers and repetitions; remove only verified non-spoken annotations and labels. Complete the four verification checks and the approval acknowledgement, then select **Approve & freeze reference**. The original document remains unchanged.

## 2. Configuration Review

Select the ASR models, language and resource monitoring. Verify the recording ID, audio, reference, requested device/precision and output location. Complete the three configuration confirmation checks and select **Confirm configuration**.

## 3. Benchmark initialisation

Select **Start benchmark**. RedScribe validates the experiment directory, verifies the approved dataset, collects runtime provenance and initialises the checkpoint. Model statuses appear in the live monitor.

## 4. Live benchmark monitoring

Models are evaluated sequentially. The monitor displays WER, CER, edit counts, reference and output lengths, loading and inference times, RTF, device, precision and sampled resource peaks. Configuration is locked during the run.

## 5. Completion and scientific reporting

Inspect the completion status and scientific outputs. A completed worker does not alone establish full audio coverage or model superiority. Review the results before commencing another experiment.

## 6. Structured output

Select **Open output folder** to inspect the experiment directory.

| Output | Purpose |
| --- | --- |
| `01 - Scientific Report.pdf` | Recognition accuracy, edit counts, efficiency, scientific figures and interpretation. |
| `02 - Scientific Results.xlsx` | Model summary, recording results and efficiency data. |
| `03 - Supporting Material/` | Scientific figures, statistical CSV data and publication checksum manifest. |
| `04 - SENSITIVE DATA/` | Restricted checkpoints, predictions, reference metadata and diagnostic logs. |

## 7. Illustrated documentation and sample outputs

The accompanying documentation package is prepared separately for author review. It includes six runtime screenshots, with confidential transcript content and workstation paths obscured, and the original PDF and Excel publication exports from the validation run. The binary assets have not yet been committed to the repository.

Release screenshots and numerical sample outputs only after confirming research permissions. Actual run data remain pseudonymous rather than anonymous. Keep the original screenshots, source recordings, reference transcripts, logs and checkpoints in protected local storage. A synthetic demonstration is an alternative if research permissions do not permit public distribution.

The original scientific outputs are examples of report functionality, not evidence of a completed multi-recording comparative study.