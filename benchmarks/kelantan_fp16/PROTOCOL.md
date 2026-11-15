# RedScribe Kelantanese Malay FP16 benchmark plan

Status: planned study protocol, not an implemented benchmark runner or a completed evaluation.

This study will compare seven locally executed ASR checkpoints against 25 existing human-verified verbatim transcripts of the corresponding Kelantanese Malay recordings. The user has confirmed that the reference transcripts have already been verified. The purpose is to identify the best-performing evaluated configuration on this dataset, using transcription accuracy as the primary criterion and processing efficiency as a secondary criterion.

## Agreed scope

- Use all 25 recording–reference pairs. Do not select only the strongest dialect recordings or remove difficult recordings after inspecting model outputs.
- All seven candidate checkpoints are listed in `models.json`: up to 175 recording–model evaluations, each of which may contain multiple shared audio chunks.
- Run locally on the same NVIDIA RTX 5070 12 GB computer, one model at a time, with a batch size of one.
- Use FP16 for every candidate: FP16 floating-point model weights and FP16 inference policy, with no BF16 or INT8/INT4 quantisation. Necessary library stability operations or accumulations may use FP32; do not describe this as literally every operation running in FP16. Record the actual dtype policy.
- Disable speaker diarisation, alignment and timestamp generation for the ASR benchmark. No word-level timestamps or speaker labels are required for WER/CER.
- Keep the verified reference independent of model outputs. Do not use these 25 recordings to fine-tune models, select prompts, or optimise hyperparameters.
- The primary comparison includes all audible dialogue represented in the reference, using the same speaker-inclusion rules for every model.

## Supplementary controlled read speech set

A separate [controlled Kelantanese read-speech plan](CONTROLLED_READ_SPEECH.md) adds fictional question-and-answer passages based on the SSIG, read by Kelantanese speakers. Its illustrative starting target is five speakers reading ten short passages each. Final collection numbers are not yet fixed. The actual spoken references require independent listening and adjudication; a printed script is not a guarantee of 100 percent transcription accuracy.

Use the same seven model candidates and FP16 protocol, but score and report the controlled recordings separately from the 25 spontaneous interviews. Plan a consented, versioned public audio/reference/configuration/scoring package for reproducibility. The original 25 interview pairs remain private under their own permissions. Do not release voices or recordings merely because the study protocol is stored in this repository.

## Candidate checkpoints and rationale

| ID | Checkpoint | Rationale | Planned benchmark runtime |
| --- | --- | --- | --- |
| whisper_large_v3 | `openai/whisper-large-v3` | General multilingual baseline and RedScribe's current model family | Transformers/PyTorch Whisper adapter |
| whisper_large_v3_turbo | `openai/whisper-large-v3-turbo` | Within-family accuracy and processing-time comparison | Transformers/PyTorch Whisper adapter |
| mesolitica_whisper_turbo_v3 | `mesolitica/Malaysian-whisper-large-v3-turbo-v3` | Malaysian-context adaptation of Whisper Turbo | Transformers/PyTorch, preserving its documented processor/task conventions |
| mesolitica_xlsr_300m_mixed | `mesolitica/wav2vec2-xls-r-300m-mixed` | Locally adapted CTC model trained on Malay and other regional speech | Transformers/PyTorch CTC adapter |
| meta_mms_1b_all | `facebook/mms-1b-all` | Multilingual CTC comparator using the Malay `zlm` adapter | Transformers/PyTorch MMS adapter |
| qwen3_asr_1_7b | `Qwen/Qwen3-ASR-1.7B` | Additional ASR family with explicit Malay support | qwen-asr Transformers backend; FP16, not its BF16 example default |
| buzzasr_malay | `BuzzASR/malay` | Malay-specific adaptation of Whisper Large-v3 | Transformers/PyTorch Whisper adapter |

The ordinary desktop app may continue to use Faster-Whisper. The planned benchmark uses the original checkpoints through the adapters above, rather than treating Hugging Face checkpoints as drop-in Faster-Whisper models. The benchmark adapters and runner still need implementation. Runtime and decoding differences must be reported alongside speed results.

MMS is included for the user's noncommercial research under its CC BY-NC 4.0 terms. The inspected Mesolitica model cards did not establish an explicit checkpoint licence; record the applicable terms before executing those candidates. Record the licence associated with the pinned revision for every model. These are setup checks, not evidence that any model has already passed validation.

## Dataset preparation and reference handling

1. Copy `dataset_manifest.template.json` to `dataset_manifest.local.json`. Map all 25 anonymous IDs to their local audio and verified reference files. Never commit the completed local manifest, recordings or reference text.
2. Preserve the originals. Extract transcript content from Word/Excel reports into local UTF-8 text, excluding report metadata, automatic headings, speaker labels and formatting timestamps. Check the extraction against the already-verified transcript; this step does not replace the existing human verification or require rewriting the dialect.
3. Confirm one-to-one audio–reference correspondence, non-empty reference text and the agreed coverage of the recording. If a reference covers only part of a recording, declare that interval before the benchmark and apply it to every model; do not score unmatched audio.
4. Record duration, audio/reference SHA-256 hashes, reference version and verification provenance locally. Record unique speakers separately from recording count where known; 25 recordings must not automatically be described as 25 independent speakers.
5. Retain Kelantanese lexical forms, fillers, code-switching and other verbatim content according to the existing transcription convention. Do not standardise Kelantanese words into standard Malay or correct reference wording using ASR suggestions.
6. If dialect intensity is described, define and rate it without viewing model scores. Do not claim that every recording has equally strong dialect or that this dataset represents all Malay speakers.

## Shared audio preparation

- Prepare a reproducible 16 kHz mono PCM input once and supply the same samples to all models. Record the conversion command and software version. Preserve the original files.
- Use shared, contiguous chunks of at most 30 seconds for inference, preferring silence boundaries near the limit. Define the exact boundary-selection algorithm before running the dataset.
- Freeze chunk boundaries and hashes once. Cover the entire declared recording interval without dropping speech, and do not introduce overlapping text that would need model-dependent deduplication.
- Do not enable an additional model-specific VAD, denoiser or speech filter in the primary comparison. Document any unavoidable internal preprocessing.
- Concatenate ordered chunk hypotheses to one hypothesis per recording for scoring. Chunk count is not the statistical sample size.

## Technical validation before the scored run

Use a separate, non-study smoke-test recording to check loading, Malay settings, decoding, FP16 stability and memory use. Do not choose technical settings by finding the lowest WER on the 25 study references.

For every candidate:

- Pin a Hugging Face commit revision, runtime/package versions, processor/tokenizer revision and any required language-adapter revision.
- Set the requested language to Malay where supported, use transcription rather than translation, and document any baked-in language prompt or custom task token.
- Verify FP16 parameter dtype and actual execution device. Disable automatic precision/device fallback and avoid retaining diarisation or another ASR model in GPU memory.
- Use batch size one and no sampling. Use greedy decoding/one beam where supported; CTC uses greedy decoding without an external language model. Freeze exact per-model decoding settings, attention implementation and sufficient output-token limits before scoring.
- Qwen's FP16 path must be tested rather than assuming its BF16 example is equivalent. FlashAttention 2 may be used only if its FP16 path is supported in the chosen environment; otherwise pin a compatible attention implementation.
- Check finite outputs and complete audio coverage. A saved FP16 checkpoint or a successful load alone does not establish a successful FP16 inference run.
- Record peak GPU memory and test the shared 30-second chunk policy. If a common chunk policy needs changing for memory reasons, freeze the revised common policy before evaluating all 25 recordings.

If a model remains unsupported, numerically unstable or out of memory under the agreed FP16 protocol, mark that configuration as failed with its reason. Do not quietly run it in BF16, FP32, CPU mode or a lower-bit format and include it as an FP16 success. Any separately authorised precision comparison is a different experiment.

## Fixed scoring rules

The [WER/CER scoring preparation plan](SCORING_PLAN.md) defines the planned local JiWER evaluation tool, reference/hypothesis extraction, fixed normalisation, synthetic validation cases, result exports and the mandatory scoring freeze before the experiment. This tool remains to be implemented; desktop performance logs do not currently calculate WER/CER.

Preserve raw references and unedited raw model outputs. Apply the same deterministic normalisation to both sides for the primary metrics:

1. Unicode NFC normalisation.
2. Lowercase.
3. Replace Unicode punctuation characters with spaces; do not concatenate words when removing punctuation.
4. Collapse whitespace and strip leading/trailing whitespace.
5. Do not change dialect spellings, expand numbers, remove fillers, substitute synonyms or apply an LLM correction.

WER uses whitespace-separated words after these transformations. CER uses the resulting characters after removal of whitespace; preserve letters, digits and diacritics. These conventions must be versioned and reported because other CER definitions may retain spaces.

- Primary: corpus WER, `sum(S + D + I) / sum(reference_words)`, reported as a percentage.
- Secondary: corpus CER, aggregated using total reference characters under the declared rule.
- Also retain per-recording WER/CER and the alignment counts for substitutions, deletions and insertions.
- Use a pinned scoring-library version and retain the normalised strings and alignments for audit.
- An empty hypothesis from a successful inference remains scoreable as deletions. A crashed run has a missing result, not zero error. An empty reference is a data-preparation error and is not silently removed.

## Timing and resource measurement

Pre-download model files. Record cold model-loading time separately from transcription.

Warm up each model with a non-study sample, then time its full 25-recording pass in a predefined model order. Synchronise CUDA at timing boundaries. Record per-recording inference time, total model-pass time and peak allocated/reserved GPU memory. Include each model's required feature extraction and decoding in inference timing; exclude reference scoring and Word/Excel report export. Common audio conversion/chunk creation is a separate preprocessing measurement.

RTF is total timed inference seconds divided by the corresponding evaluated audio seconds. Report corpus RTF from those totals rather than an unweighted mean of recording RTFs. If timings are repeated, repeat the entire timed protocol under the same configuration and retain each repeat.

## Results and interpretation

Store results privately under `output/benchmark_kelantan_fp16/` with the frozen manifests and run configuration. The future runner should resume only missing or failed recording–model jobs, and only when input hashes, model revisions and configuration hashes match. Never overwrite or mix results from different configurations.

Each result needs at least: recording ID, model ID/revision, configuration hash, device, requested/actual precision, audio duration, status/failure reason, raw hypothesis path/hash, reference hash, word/character alignment counts, WER, CER, timed inference seconds, RTF and peak GPU memory. Store errors without tokens or identifying participant paths.

The paper should report:

- Dataset duration, recording and unique-speaker counts where available, reference verification, dialect characteristics and recording conditions.
- One model-level table with model/revision, runtime, FP16 policy, completed recordings out of 25, corpus WER/CER, inference time/RTF and peak VRAM.
- Paired recording-level results and dialect/code-switching error examples reviewed against audio.
- Uncertainty in paired WER differences, for example recording-level bootstrap intervals. If recordings share speakers, use a justified cluster unit and do not assume that all 25 files are independent people.
- The lowest corpus WER as the prespecified primary ranking criterion among configurations with all 25 completed recordings. CER and speed provide additional interpretation. Small differences without supporting uncertainty should not be presented as definitive superiority.
- A candidate with incomplete coverage must not be ranked against complete candidates using a different set of recordings without a clearly labelled matched-subset analysis.
- Conclusions limited to the evaluated Kelantanese Malay dataset and configurations. Do not claim universal superiority for all Malay speech.

## Implementation milestones

- [ ] Complete the private 25-pair mapping, extraction checks, hashes and reference conventions.
- [ ] Pin model revisions, applicable licences, packages, decoding and attention settings.
- [ ] Implement FP16 model adapters and verify each on the non-study smoke-test audio.
- [ ] Implement common chunk preparation, resumable execution, raw-output capture and resource logging.
- [ ] Implement and validate the local JiWER scorer and recording/model summary export using [the pre-experiment scoring gate](SCORING_PLAN.md#pre-experiment-gate).
- [ ] Freeze the protocol/configuration before the 25-pair scored run.
- [ ] Attempt the seven model passes; report all failures and coverage.
- [ ] Review alignments, dialect errors, uncertainty and publication tables.
- [ ] Prepare and verify the supplementary controlled read-speech set under its separate collection and release checklist.

## Primary documentation

- https://huggingface.co/openai/whisper-large-v3
- https://huggingface.co/openai/whisper-large-v3-turbo
- https://huggingface.co/mesolitica/Malaysian-whisper-large-v3-turbo-v3
- https://huggingface.co/mesolitica/wav2vec2-xls-r-300m-mixed
- https://huggingface.co/facebook/mms-1b-all
- https://creativecommons.org/licenses/by-nc/4.0/
- https://huggingface.co/Qwen/Qwen3-ASR-1.7B
- https://huggingface.co/BuzzASR/malay

Follow the documentation for the exact revisions selected at setup; these links alone are not evidence that the benchmark was executed.
