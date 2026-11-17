# Ground-truth reference preparation and review protocol (experimental)

**Updated:** 18 November 2026. Applies only to `redscribe-benchmark-timeline`. This is **not** an IEEE-mandated universal standard, a certified NIST-conformant pipeline, or a completed scientific validation. The implementation follows principles described in authoritative scoring documentation and published speech-recognition evaluation studies.

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

## Explicit non-goals and outstanding constraints

- **Do not auto-strip speaker labels, abbreviations, fillers, dialect, punctuation or non-speech events.** Any transformation must be agreed before scoring, recorded and applied consistently to both hypothesis and reference.
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
