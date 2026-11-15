# Supplementary controlled Kelantanese read speech benchmark

Status: agreed addition to the study plan; scripts, recruitment, recording and release have not yet been completed.

## Purpose and relationship to the main study

Add a small, reproducible read-speech test set using fictional question-and-answer scripts based on the study's semi-structured interview guide (SSIG). Kelantanese speakers will read these scripts using their natural regional pronunciation. Once the recording and reference are verified and appropriately authorised for public sharing, other researchers can rerun the same model evaluation.

This is a supplementary test set. The primary benchmark remains the 25 existing interview recording–reference pairs in `PROTOCOL.md`. Read speech and spontaneous interviews must have separate WER/CER tables, timing denominators and interpretations. A difference between the sets cannot by itself establish a causal effect of dialect, because speaking style, content, speakers and recording conditions may also differ.

## Proposed initial scale

| Element | Planning target |
| --- | --- |
| Speakers | Five Kelantanese speakers, with variation where feasible |
| Shared scripts | Ten short question-and-answer passages, read by each speaker |
| Target duration | Approximately 15–30 seconds per recorded passage |
| Total | Illustrative target of 50 clips and approximately 12.5–25 minutes of audio |
| Role | Supplementary benchmark, not model-training or hyperparameter-tuning data |

These are starting targets, not a power calculation or a claim that 50 independent observations exist. Final speaker count, script length, clip duration and actual audio totals must be recorded and frozen before the scored evaluation. If a passage is too long for the shared input policy, split it consistently at a declared boundary before evaluation.

The seven model checkpoints and FP16 policy in `models.json` apply to both datasets. Fifty supplementary clips would imply 350 additional clip–model attempts if all seven checkpoints pass technical setup; keep those counts separate from the main study's planned 175 recording–model evaluations.

## Script preparation

- Write original, fictional questions and answers inspired by SSIG topics. Do not copy identifying interview quotations, names, personal histories or other confidential participant material into the public script.
- Include relevant Kelantanese lexical forms, ordinary connected speech and study-domain terms in a documented and balanced selection. A script is not evidence of a real person's views or experiences.
- Ask speakers to use their normal pronunciation; do not ask them to exaggerate or imitate a dialect. Describe the material as read speech, even when delivered conversationally.
- Establish a consistent written convention for dialect forms before recording. Record the intended script separately from the verified spoken reference.
- Assign stable script IDs and speaker pseudonyms. Shared passages allow comparison across speakers, but results remain clustered by both speaker and script.
- Use a separate, non-test recording for microphone checks and model setup. Do not revise final scripts or recording delivery after viewing benchmark outputs.

## Recording and reference verification

1. Record with a documented microphone/device, room, distance and input settings. Capture clean originals and record recording conditions rather than assuming identical conditions without checking.
2. Keep a log of retakes and prespecified reasons such as an interrupted recording or clearly missed line. Make any recording selection decisions before scoring, not because a model transcribes a clip poorly.
3. Have two reviewers who understand the relevant Kelantanese speech independently listen to each final clip and check the spoken words. Resolve differences and record the adjudicated reference version.
4. The final reference follows what was actually spoken. A reader may omit, add, repeat or change words; the printed script alone is not an automatically correct reference.
5. Preserve dialect wording under the agreed orthographic convention. Do not rewrite it into standard Malay or use model hypotheses to decide the reference.
6. Record verification provenance and freeze audio/reference hashes before evaluation. Describe the result as a human-verified/adjudicated reference, not an assertion of guaranteed 100 percent correctness.

## Evaluation and reporting

Use the same shared preprocessing, chunk policy, FP16/batch-one settings, pinned model revisions and deterministic scoring rules as the main protocol. Keep raw outputs and normalised scoring strings for audit. Disable diarisation and timestamp generation for this test as well.

Report per-clip errors, per-speaker and per-script summaries, corpus WER/CER, model coverage, time/RTF and peak VRAM for this supplementary set. All models must receive the same final clips and references. Failures remain visible and must not become zero-error rows.

For uncertainty estimates, account for repeated clips from the same speakers and shared passages. Do not treat the illustrative 50 clips as 50 independent speakers. With a small number of speakers, be explicit about the limited precision and generalisability of speaker-level conclusions.

Do not pool supplementary read-speech counts into the primary 25-interview WER/CER. If a combined summary is ever added, label its composition and weighting, and retain the two separate primary and supplementary tables.

## Planned public reproducibility package

Obtain the required institutional/ethics clearance or amendment for new recording and public release where applicable, and obtain explicit speaker consent for public voice/audio sharing. Existing consent to a private interview does not automatically cover release of a separate recording. Voice can remain identifying despite removal of names; do not promise anonymity of released voices.

After the applicable approvals, participant consent and file checks are complete, prepare a versioned release containing:

- Final audio clips and the verified spoken references.
- The intended scripts, clearly distinguished from what was actually spoken.
- Anonymous clip, script and speaker IDs, durations, sampling rates and audio/reference SHA-256 hashes.
- Only metadata approved for sharing; remove identifying file names, recording tags and unnecessary personal details.
- Model checkpoint revisions, actual FP16/runtime/decoding settings, normalisation version and scoring code.
- A README explaining collection, reference verification, known limitations and how to reproduce the results.
- Applicable consent-compatible reuse terms/licences and a persistent version identifier or DOI when released.

Do not publish recruitment/contact details, signed consent forms, private identity mappings, the 25 original interview recordings or private interview transcripts in this package. Keep the two datasets' release decisions separate. This plan authorises preparation of the protocol only; no audio release has been completed or requested at this stage.

## Checklist

- [ ] Draft fictional SSIG-based scripts and the dialect-writing convention.
- [ ] Confirm the final collection scale and a recording/retake protocol.
- [ ] Confirm applicable institutional/ethics requirements and public-sharing consent.
- [ ] Recruit speakers and record the controlled passages.
- [ ] Independently verify the final audio with two reviewers and adjudicate differences.
- [ ] Freeze the final clip/reference manifest and hashes before scoring.
- [ ] Run the same seven FP16 configurations where technically eligible.
- [ ] Produce supplementary results separately from the 25-interview results.
- [ ] Check release permissions and identifying content before publishing a versioned reproduction package.

## Background

Common Voice distinguishes scripted/read speech from spontaneous speech datasets. This motivates reporting the two speaking styles separately; it does not validate this study's proposed sample size or establish Kelantan-specific performance.

- https://commonvoice.mozilla.org/
- https://github.com/common-voice/cv-dataset/
