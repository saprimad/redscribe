# Ground-truth reference preparation and review protocol (experimental)

**Updated:** 28 November 2026. Applies to the experimental benchmarking workflow, including `feature/benchmark-experiment-manager` (PR #28). This is **not** an IEEE-mandated universal standard, a certified NIST-conformant pipeline, or a completed scientific validation. The implementation follows principles described in authoritative scoring documentation and published speech-recognition evaluation studies.

## Rationale and research references

1. **NIST SCTK/SCLITE** documents reference/hypothesis alignment and scoring, including `TRN` and time-labelled `STM` formats. RedScribe currently uses a researcher-approved plain-text source, **not yet exported or independently validated as NIST STM/TRN**: https://github.com/usnistgov/SCTK/blob/master/doc/sclite.htm and https://github.com/usnistgov/SCTK/blob/master/doc/infmts.htm
2. **Faria et al., Interspeech 2022** demonstrate that transcription-reference corrections and normalisation policy can materially alter reported WER. This motivates separately retaining original source, approved scoring text, and explicit rules: https://www.isca-archive.org/interspeech_2022/faria22_interspeech.pdf
3. **Gorisch & Schmidt, LREC-COLING 2024**, *Evaluating Workflows for Creating Orthographic Transcripts for Oral Corpora by Transcribing from Scratch or Correcting ASR-Output*, examine human transcription/correction workflows relevant to conversational and dialect data: https://aclanthology.org/2024.lrec-main.582/
4. **LDC Hub-4 annotation specification** illustrates why segment identity and temporal boundaries matter for labelled multi-speaker transcripts. This does not imply the current implementation is Hub-4 compliant: https://catalog.ldc.upenn.edu/docs/LDC2001S91/h4annot.pdf

These sources motivate quality control and reproducibility; **they do not prescribe one mandatory scoring normalisation for Malay/Kelantan dialect data**. That design decision remains HOLD.

## Current controls

1. Import an existing DOCX; preserve the original file without editing it. Reject Word temporary lock files and empty readable bodies.
2. Extract paragraphs and table cells in document-body order. Preserve verbatim words and surface speaker labels, headings, fillers and punctuation for manual review.
3. Capture SHA-256 of the DOCX when preview is opened; flag detectable Word features requiring manual inspection (tracked insertions/deletions, comments, text boxes, Word fields and non-empty header/footer content). These flags are **warnings**, not an exhaustive parser or automatic cleanup.
4. The researcher edits a separate scoring copy and confirms (a) source audio reviewed, (b) scoring text covers exactly the relevant audio clip, (c) speaker labels/headings/metadata reviewed, (d) fillers, overlap, interruptions and non-speech notes reviewed. **No words are silently deleted or normalised.**
5. On approval, reject when the source DOCX SHA-256 differs from the preview snapshot. The approval stores a separate UTF-8 text file plus JSON manifest (source location/hash, text hash, checklist, policy, timestamp) in a private folder.
6. At scoring time, re-check both scoring-text and original DOCX hashes. Legacy manifests without original-source location must be re-approved.
7. Manual pairing remains required for each audio-reference pair; the SHA-256 evidence does **not** prove that the reference actually corresponds to the selected audio. The researcher's signed-off review and later alignment verification remain necessary.

## Mandatory pre-benchmark reference preparation (verbatim speech only)

The original qualitative interview transcript and the ASR scoring reference serve different purposes. Qualitative transcripts may contain speaker identifiers, observational notes, gestures, editorial explanations and other annotations useful for research interpretation. These are not necessarily words spoken in the recording. WER and CER evaluate transcription of speech, not the reproduction of qualitative annotations or recognition of non-verbal behaviour.

Prepare a separate local DOCX scoring copy **before** running any model. Preserve the original qualitative transcript unchanged. Apply the same written preparation rules to every recording and every model, without using model predictions to decide which reference words to retain.

| Material | Required action |
| --- | --- |
| Speaker identifiers (e.g. `Interviewer:`, `Penemu duga:`, `P1:`, including formatting variants) | Remove labels only; retain all actual spoken words from the interviewer, participant and any other audible speakers within the evaluated audio span. |
| Non-verbal observations (e.g. `[nods]`, `(points to the door)`, gestures, facial expressions) | Remove the editorial annotation from the scoring copy, even when it describes an audible event. Non-verbal event detection is outside this word/character scoring task. |
| Unspoken editorial glosses, translations, explanatory text, timestamps, headings, page numbers | Remove only verified non-spoken metadata; retain any words that were actually spoken. Do not delete all parenthesised text blindly. |
| Laughter, coughing, silence and other non-speech sounds | Remove descriptive tags such as `[laughs]` or `[coughs]`. Retain genuine spoken interjections and lexical fillers; adjudicate ambiguous written forms such as "haha" against the audio under a consistent policy. |
| Unintelligible or missing speech markers (e.g. `**`, `[inaudible]`) | These markers are not reference words. Re-listen first and transcribe recoverable speech; never invent missing words. If unresolved, document the occurrence privately and disclose the incomplete coverage. Removing a marker does not exclude the corresponding audio from scoring. |
| Dialect, code-switching, fillers, repeated words, false starts and interruptions | Preserve audible verbal content in original order; do not translate, standardise dialect, paraphrase, summarise or remove repetitions. |
| Overlapping speech | Retain recoverable speech from all speakers and verify ordering against the audio. Document ambiguity; conversation-level WER/CER is not a speaker-attribution metric. |
| Layout and whitespace | Review extraction for artificial line breaks, tabs and extra spaces. Adopt a fixed documented formatting convention before experiments; raw CER is sensitive to these characters. Do not silently change the metric or introduce one-sided lexical normalisation. |

### Researcher checklist before Approve & Freeze

- [ ] Confirm the audio and DOCX represent the same recording and entire evaluated time span.
- [ ] Compare the scoring copy against the original transcript and listen to the audio to resolve doubtful annotations, words and omissions.
- [ ] Remove speaker labels and non-spoken annotations while retaining all audible speech in scope.
- [ ] Review any uncertain or overlapping speech; record unresolved regions, preparation decisions and reviewer/date in a private audit log.
- [ ] Inspect the extracted scoring text, especially whitespace, punctuation, casing and residual annotation markers.
- [ ] Approve and freeze one reference for use by all models evaluating that recording. Retain the source and frozen hashes with the experiment.

### Effect on reported metrics and comparability

Reference preparation can change the reference word and character denominators and the optimal substitution, deletion and insertion alignment. WER and CER may increase, decrease or remain unchanged; improvement is not guaranteed. The existing RapidFuzz implementation computes WER on whitespace-delimited tokens and CER on raw Unicode code points (including punctuation, spaces and line breaks). Removing non-spoken metadata is reference preparation, not a new scoring algorithm.

Any optional scoring normalisation (such as case folding, punctuation stripping or general text normalisation) remains a separate methodological decision and must be prespecified and applied consistently to both reference and hypothesis. Verify that hypotheses contain speech text rather than exported labels or annotations; do not selectively correct model errors. The current raw scorer does not support time-region masking or exclusion of unintelligible audio; do not claim that removing an annotation excludes a region from evaluation. If unresolved audio materially compromises the reference, defer that recording or explicitly design and validate an identical audio/reference exclusion procedure for all models before scoring.

If a frozen reference changes, create a new approved reference and a new experiment; rerun all compared models under the same settings and report the new reference hash. Do not mix results based on different reference versions in the main comparison. Earlier runs may be retained as preliminary validation, not pooled as equivalent observations. Keep all real audio, participant transcripts, annotation logs and private manifests outside GitHub. This checklist is a research preparation requirement, not an automatic annotation-removal feature or a claim of independent validation.

## Explicit non-goals and outstanding constraints

- **Do not automatically strip labels or annotations in the scorer.** Manually remove verified non-spoken metadata during reference preparation as described above. Preserve audible words; any optional scoring normalisation must be agreed before scoring, recorded and applied consistently to both hypothesis and reference.
- A raw character-error rate counts Unicode code points **including spaces, punctuation and line breaks**. Consequently, Word paragraph boundaries can affect CER; *raw scoring is exploratory*. A prespecified matching scoring policy is needed before comparison.
- Conversation-level WER does not measure speaker attribution. Timestamped and manually adjudicated speaker ground truth is needed to claim DER/JER or diarisation accuracy.
- Complex DOCX constructs (nested/merged tables, revisions, fields, footnotes, comments, images and drawn text boxes) still require visual comparison with the original DOCX.
- Human verification is an **attestation**, not independent proof of perfect transcription. Document reviewer identity/protocol externally when preparing the final study design.
- A reference approved through programmatic compatibility calls with no checklist is recorded as `scoring_scope=unspecified`; it must not be treated as publication-ready.
- A full 45–60-minute DOCX may **not** correspond to a 180-second pilot clip. Clip-to-reference coverage must be verified; do not calculate WER against a mismatched complete interview transcript.
- Results from private participant audio/transcripts and reference manifests must not be uploaded to public GitHub.

## Verification steps on the researcher's machine

```powershell
git fetch origin
git switch redscribe-benchmark-timeline
git pull --ff-only
python -m unittest discover -s tests -p "test_benchmark*.py"
python redscribe_gpu.py
```

Perform human review on a **de-identified** representative DOCX, including a file with tables and one with speaker labels, then deliberately alter the DOCX between preview and approval to confirm the application blocks the freeze. Re-open the GUI and verify the four checklist confirmations, raw text, saved hashes, and private output path.

**Validation status: tests are authored but have not been executed on the user’s Windows/GPU environment as part of this remote review.**
