# Kelantan Malay dialect benchmark — phonological rules (draft v0.1)

Status: **Provisional; requires validation by Kelantan speakers and comparison with audio.** Recorded 2026-11-16. This document is a benchmark design note, not an implemented transcription feature.

## Aim
Evaluate ASR recognition of Kelantan Malay speech, retaining original verbatim and comparing it against a human-verified reference transcript. Assess dialect-to-standard Malay normalisation **separately**.

## Candidate mappings for speaker review
| ID | Proposed pattern (informal spelling) | Standard Malay | Kelantan-style rendering |
| --- | --- | --- | --- |
| R01 | final -an → nasal vowel often written -ae | makan; ikan; jalan | makae; ikae; jalae |
| R02 | final -am → nasal vowel (spelling to verify) | malam; dalam | malae; dalae |
| R03 | final -ang → nasal vowel (spelling to verify) | orang; barang | ore; bare |
| R04 | final -ar → -o | besar; lapar | beso; lapo |
| R05 | final -as → -eh | panas; keras | paneh; kereh |
| R06 | final -at → glottalised ending in some words | berat | bera' |
| R07 | final -a → -o in some words | mana; lima | mano; limo |
| R08 | final -ah → -oh in some words | rumah; salah | rumoh; saloh |
| R09 | final -ut → -u' in some words | takut; rambut | taku'; rambu' |
| R10 | final -it → -i' in some words | sakit; bukit | saki'; buki' |
| R11 | final -us → -uh in some words | halus; kurus | haluh; kuruh |
| R12 | final -is → -ih in some words | manis; habis | manih; habih |

These are **candidate correspondences, not universal substitution rules**. E.g. 'tempat → tempa\'' was discussed but must be checked before adoption. Written -ae is an informal approximation, not an IPA transcription of nasal vowels. Some rows may be inaccurate or district-specific.

## Lexical correspondences (context dependent)
- saya → kawe
- awak → demo / mung
- tidak → dok / tok (context dependent)
- pergi → gi
- kenapa → bakpo
- bagaimana → guano
- apa → gapo

These are lexical alternatives, not automatic phonological replacements. Do not assume the same meaning in every utterance.

## Benchmark protocol (planned)
1. Collect consented audio and a speaker-verified **verbatim dialect reference**, retaining an untouched original.
2. Document speaker district, recording conditions, language switching and annotation convention where ethically permissible.
3. Run the same audio through each selected RedScribe ASR model, recording model/checkpoint, device, settings and runtime.
4. Compute **raw verbatim WER and CER** against the original dialect reference. Keep all original model outputs.
5. Optionally compute a **second**, explicitly labelled normalised WER/CER using a frozen, documented mapping and independently verified standardised reference; never replace the primary scores.
6. Report per-speaker/per-district results where sample sizes permit; review substitution/deletion/insertion errors and dialect-specific terms.
7. Freeze annotation conventions and rule version before final comparisons; record exceptions and disagreements.

## Planned data structure
`audio_id | speaker_id | district | reference_verbatim | asr_model | hypothesis_raw | wer_raw | cer_raw | reference_normalised | hypothesis_normalised | wer_normalised | cer_normalised | rule_version | reviewer_notes`

## Next steps
- Verify every proposed mapping with native speakers and recordings.
- Decide whether reference transcription uses a consistent practical orthography or IPA (do not mix them within a scoring set).
- Build an exceptions lexicon and unit tests before any optional normalisation code.
- Benchmark raw transcripts first; report normalisation as a distinct experiment.
