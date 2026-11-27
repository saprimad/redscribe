# RedScribe — Ground Truth Preparation and Verification Protocol

**Protocol version:** 1.0  
**Revision date:** 28 November 2026  
**Scope:** Verbatim, conversation-level automatic speech recognition (ASR) benchmarking

## 1. Purpose and scientific basis

This protocol establishes a systematic, evidence-based framework for the preparation, verification and preservation of verbatim reference transcripts for automatic speech recognition (ASR) benchmarking. It is grounded in established speech recognition evaluation methodologies, the National Institute of Standards and Technology (NIST) scoring framework [1], and peer-reviewed research in computational linguistics and speech processing [2]–[7].

Reference integrity is essential because transcription corrections and scoring conventions can materially affect measured word error rate (WER) [2]. Orthographic transcription of interviews and dialectal speech requires careful human review [3]. Research on spontaneous speech and disfluency recognition further supports distinguishing speech fidelity from fluent-text transcription [4], [5]. RedScribe employs inclusive verbatim evaluation, retaining audible verbal content rather than reconstructing the speaker's intended or grammatically corrected message.

The operational requirements below define RedScribe's research protocol. They are informed by the literature rather than presented as a single universal transcription convention. The protocol applies consistently to every recording and every evaluated model.

## 2. Reference materials and scope

Maintain three distinct local artefacts:

| Artefact | Purpose |
| --- | --- |
| Original audio recording | Primary evidence of the speech within the evaluated time span |
| Original verbatim transcript | Authoritative source document for qualitative research, including speaker labels and relevant annotations |
| Benchmark scoring reference | Researcher-verified speech-only derivative used for quantitative ASR evaluation |

The original audio and source transcript shall remain unchanged. The scoring reference shall represent the same evaluated audio span, including the speech of the interviewer, participant and any other audible speakers within scope. Prepare the reference independently of the outputs of the models under evaluation to reduce reference bias.

## 3. Reference preparation rules

The benchmark targets the transcription of verbal content. Qualitative observations, non-verbal behaviour and editorial metadata are retained in the original transcript where required for qualitative interpretation but are excluded from the scoring text.

| Material | Required treatment |
| --- | --- |
| Speaker labels, including `Interviewer:`, `Penemu duga:`, `P1:` and variants | Remove the label; retain the utterance. |
| Gestures, facial expressions and observational notes | Remove the annotation, e.g. `[nods]` or `(points towards the door)`. |
| Non-speech acoustic event tags | Remove editorial descriptions such as `[coughs]`, `[laughs]`, `[silence]` and `[background noise]`. |
| Unspoken explanations, translations and glosses | Remove after verifying that the content was not uttered. Parentheses alone do not establish that content is unspoken. |
| Timestamps, page numbers, headings and administrative metadata | Remove verified non-speech material. |
| Fillers, hesitation and spoken interjections | Retain audible forms such as `erm`, `haa` and `hmm`; adjudicate ambiguous forms against the recording. |
| Repetition, false starts, incomplete words and self-correction | Retain recoverable verbal content without rewriting the utterance. |
| Dialect and colloquial language | Retain the original verified orthography; do not convert regional forms into standard Malay or another language. |
| Code-switching | Retain words in the language actually spoken. |
| Interruptions and overlapping speech | Retain recoverable speech from all speakers in the most defensible verified sequence. Record ambiguous order. |
| Unintelligible speech markers, e.g. `**` or `[inaudible]` | Re-listen, recover words where possible, and remove the marker itself from scoring text. Do not invent words. Record unresolved speech privately. |
| Word formatting and layout | Remove document-layout artefacts. Preserve verified text and apply a consistent, recorded convention for spacing and paragraph boundaries. |

Do not delete text merely because it matches a speaker name, annotation keyword or bracket pattern. Such forms may be spoken words. Do not remove personal names from the scoring reference solely for de-identification if they were spoken; protect the reference through restricted local access instead. A study requiring de-identified scoring must prespecify a matching audio/reference procedure.

### 3.1 Dialect and disfluency preservation

For conversational Malay and Kelantan dialect, preserve verified regional vocabulary, pronunciation-based orthographic forms, lexical repetitions and fillers. Use a consistent transcription convention across recordings; resolve doubtful spellings by consulting the audio and a competent language reviewer where feasible. This protocol does not authorise grammatical correction, translation, paraphrasing, summarisation or conversion to fluent intended speech. The distinction between verbatim and intended-speech evaluation is consequential for disfluency-rich recordings [4].

### 3.2 Illustrative example (synthetic)

**Original qualitative transcript**

```text
Interviewer: Haa, demo tahu gapo?
P1: Hm, tahu, tahu. (Nods)
Penemu duga: Okey, terima kasih.
```

**Speech-only scoring reference**

```text
Haa, demo tahu gapo?
Hm, tahu, tahu.
Okey, terima kasih.
```

The example is invented for documentation; it does not reproduce participant data.

### 3.3 Unresolved speech and overlapping speech

Re-listen to uncertain regions and record unresolved instances, approximate time locations where feasible, reasons and reviewer decisions in a private audit log. The current raw scoring method does not mask time regions. Deleting an unintelligibility marker therefore does not remove the corresponding audio from evaluation; model words in that region may still affect the edit distance. If unresolved speech materially compromises reference coverage, withhold approval until it is resolved or a prespecified, consistently applied audio/reference exclusion procedure has been designed and validated. Document any deferred recordings and the reason for their exclusion.

Conversation-level WER/CER assesses the sequence of recognised text. It does not measure speaker attribution or diarisation accuracy. Overlap and uncertain ordering shall be acknowledged as potential influences on sequence-based error rates.

## 4. Researcher verification and approval

Complete the following procedure before starting model execution:

1. Create a separate scoring DOCX from the original transcript and apply Section 3.
2. Match the scoring DOCX to its source recording and verify the beginning, end and full evaluated span.
3. Listen to the audio while reviewing the text; resolve omissions, questionable wording, annotation boundaries and overlapping speech. Where feasible, obtain an additional qualified review and adjudicate disagreements. Do not claim independent double review unless performed.
4. Review extracted text in RedScribe's Ground Truth Review window. Inspect inconsistent speaker labels, metadata, residual annotations, punctuation, spacing and document-layout artefacts.
5. Record reference preparation decisions, reviewer identity, review date, unresolved regions and source/derivative versions in a private audit log.
6. Confirm all four verification checks in the application: audio verification, coverage verification, speaker-label review and non-speech review.
7. Select **Approve & Freeze**. Use the same frozen reference for every model evaluating the recording.
8. Confirm the experiment configuration, then start benchmarking.

Human approval records the researcher's verification; it is not a guarantee of error-free transcription. Review the full audio rather than relying solely on document structure or a file hash.

### Pre-run checklist

- [ ] Audio and reference correspond to the same recording and time span.
- [ ] Both interviewer and participant speech are retained.
- [ ] Speaker labels and non-spoken annotations are removed.
- [ ] Dialect, code-switching, fillers and repetitions are preserved.
- [ ] Uncertain speech and overlap have been reviewed and documented.
- [ ] Extracted text has been inspected for omissions and formatting artefacts.
- [ ] Reference preparation and reviewer details are recorded privately.
- [ ] One reference has been approved and frozen for all models.

## 5. Scoring methodology

RedScribe uses minimum-edit alignment to quantify differences between the frozen reference and ASR hypothesis, consistent with the general edit-distance approach in ASR research [1], [6]. WER and CER provide complementary word-level and character-level measures; the value of CER for multilingual evaluation has also been examined in recent research [7].

```math
WER = \frac{S_w+D_w+I_w}{N_w}\times100\%
```

```math
CER = \frac{S_c+D_c+I_c}{N_c}\times100\%
```

Here, S, D and I denote substitutions, deletions and insertions; N is the reference length in the corresponding unit. A score of zero indicates an exact match under the specified scoring policy. Insertions can result in scores exceeding 100%. An empty reference has an undefined error rate.

The current implementation uses RapidFuzz's `Levenshtein.editops` [8] with unit-cost operations:

| Property | Current raw scoring implementation |
| --- | --- |
| WER unit | Whitespace-delimited tokens using Python `str.split()` |
| CER unit | Unicode code points, including punctuation, spaces and line breaks |
| Case, punctuation and spelling | Retained; differences can contribute to error |
| Scoring normalisation | No automatic lexical or Unicode normalisation in the raw scorer |
| Scoring reference | One researcher-approved immutable-by-convention text artefact per recording |

See [scoring implementation](../../redscribe/benchmark/benchmark_fast_metrics.py). Report the raw scoring policy explicitly. These values are formatting-sensitive and should not be equated directly with scores obtained under normalised WER/CER or NIST SCLITE-specific alignment conventions. RedScribe uses its own RapidFuzz implementation rather than executing SCLITE.

Reference cleaning removes verified non-spoken material, not model recognition errors. Any future normalised scoring analysis requires a separately prespecified policy applied consistently to references and hypotheses. This protocol retains the existing raw scoring policy and does not resolve the separate normalisation research decision.

## 6. Integrity, traceability and quality control

The application extracts readable DOCX body content, including paragraphs and table cells, and retains the source file unchanged. Review extraction warnings and visually inspect complex DOCX content, including tracked changes, comments, text boxes, headers, footers, fields, footnotes, merged or nested tables. Extraction warnings are not an exhaustive inspection of all Word structures.

At reference approval, RedScribe checks the source DOCX SHA-256 against the preview snapshot and stores the approved UTF-8 text and a JSON manifest in a private local directory. The manifest records the source location/hash, scoring text hash, verification responses, preparation metadata and approval timestamp. Both source and approved-text integrity are verified during benchmarking. A changed source or missing integrity evidence requires renewed verification. Legacy manifests without source provenance must be re-approved.

For each recording, retain a private preparation log with recording ID, source and derivative filenames, preparation version, removal categories, unresolved speech, review decisions, reviewer/date, frozen reference identifier and hashes. Record model identifiers, software commit/version, scoring library version and evaluation settings in the experiment documentation.

A file hash establishes integrity, not transcription accuracy or correct audio pairing. Audio-span verification remains mandatory, including whenever a shorter excerpt is used.

## 7. Reproducibility and change control

Reference preparation may change the denominator and optimal alignment of WER/CER; a lower score is not guaranteed [2]. Freeze references before official model comparisons and do not revise them in response to a model's score. If a genuine transcription defect is discovered after freezing, document the independent evidence, create a new approved reference and rerun all compared models with the same settings. Retain earlier results as separately identified preliminary or superseded runs. Do not pool incompatible reference versions in the principal comparison.

Verify hypotheses contain the model's speech output rather than export-only speaker labels or editorial metadata. Do not selectively correct model predictions. Where preprocessing is necessary, prespecify and apply the same rule to all models.

Maintain source and frozen references, audio, annotation logs and private manifests in access-controlled local storage. Public repository documentation and test fixtures shall contain synthetic or appropriately authorised non-confidential material only.

## 8. Method verification

Software checks should include synthetic examples with known substitution, deletion and insertion totals; empty references; Unicode and whitespace sensitivity; source/reference modification detection; and reference-approval gating. Verify DOCX extraction against visually inspected representative documents and confirm the four manual verification controls and private output path on the research workstation.

Independent metric comparison should use matching tokenisation, preprocessing and alignment assumptions. Full runtime validation, reviewer verification and experimental outcomes are recorded separately in the [validation records](../validation/README.md).

## References

[1] National Institute of Standards and Technology (NIST), “Speech Recognition Scoring Toolkit (SCTK): SCLITE scoring documentation.” [Online]. Available: https://github.com/usnistgov/SCTK/blob/master/doc/sclite.htm. Input formats: https://github.com/usnistgov/SCTK/blob/master/doc/infmts.htm

[2] A. Faria, A. Janin, S. Adkoli, and K. Riedhammer, “Toward zero oracle word error rate on the Switchboard benchmark,” in *Proc. Interspeech*, 2022. [Online]. Available: https://www.isca-archive.org/interspeech_2022/faria22_interspeech.html

[3] J. Gorisch and T. Schmidt, “Evaluating workflows for creating orthographic transcripts for oral corpora by transcribing from scratch or correcting ASR-output,” in *Proc. LREC-COLING*, 2024, pp. 6564–6574. [Online]. Available: https://aclanthology.org/2024.lrec-main.582/

[4] A. Romana, M. Niu, M. Perez, and E. M. Provost, “FluencyBank Timestamped: An updated data set for disfluency detection and automatic intended speech recognition,” *Journal of Speech, Language, and Hearing Research*, 2024, doi: [10.1044/2024_JSLHR-24-00070](https://doi.org/10.1044/2024_JSLHR-24-00070). 

[5] R. Amann, Z. Li, B. Bruno, and J. Niehues, “Augmenting automatic speech recognition models with disfluency detection,” in *2024 IEEE Spoken Language Technology Workshop (SLT)*, 2024, doi: [10.1109/SLT61566.2024.10832349](https://doi.org/10.1109/SLT61566.2024.10832349).

[6] K. Kuhn, V. Kersken, and G. Zimmermann, “Beyond Levenshtein: Leveraging multiple algorithms for robust word error rate computations and granular error classifications,” in *Proc. Interspeech*, 2024, doi: [10.21437/Interspeech.2024-32](https://doi.org/10.21437/Interspeech.2024-32).

[7] T. D. K, J. James, D. P. Gopinath, and M. A. K, “Advocating character error rate for multilingual ASR evaluation,” in *Findings of the Association for Computational Linguistics: NAACL 2025*, 2025. [Online]. Available: https://aclanthology.org/2025.findings-naacl.277/

[8] RapidFuzz, “Levenshtein distance: API documentation.” [Online]. Available: https://rapidfuzz.github.io/RapidFuzz/Usage/distance/Levenshtein.html
