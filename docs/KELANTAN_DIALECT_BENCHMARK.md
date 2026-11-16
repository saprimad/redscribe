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


## Literature review and existing resources (v0.2; added 2026-11-16)

### Scope and evidence status
This section is a **narrative literature review and source-discovery log**, not a systematic review. Bibliographic details and quantitative claims should be checked against the full papers before publication. The candidate rules above are **not** all independently supported by the studies below.

### Linguistic foundations
- **Wu (2023)**, *Malayic Varieties of Kelantan and Terengganu: Description and Linguistic History*, LOT Dissertation Series 651. Comparative phonology and linguistic history provide a basis for distinguishing Kelantan forms from Terengganu and for defining transcription conventions. https://www.lotpublications.nl/Documents/651_fulltext.pdf
- **Muhamad & Mohd Rusli (2024)**, *Pengaruh Dialek Kelantan dalam Pembelajaran Bahasa Melayu di Sekolah Menengah*, *Jurnal Pendidikan Bahasa Melayu*. Discusses dialect-related phonological changes, including final-vowel changes, rhotic deletion, nasal deletion, final /s/ changes and glottalisation. **Check the original paper for the exact classification, phonetic notation and examples before citing specific rules.** https://spaj.ukm.my/jpbm/index.php/jpbm/article/view/387/0
- A reported study of **Pasir Mas** speech discusses final-consonant deletion; the exact paper citation remains **to be verified** and should not yet be used as a reference.

### Speech resources and ASR research
- **Khaw & Tan (2014)**, *Preparation of MaDiTS Corpus for Malay Dialect Translation and Speech Synthesis System*. Describes dialect translation and pronunciation-resource preparation; **not** evidence of ASR recognition accuracy. https://www.isca-archive.org/slam_2014/khaw14_slam.html
- **Tan et al. (2024)**, *Low Resource Malay Dialect Automatic Speech Recognition Modeling Using Transfer Learning from a Standard Malay Model*, *Pertanika Journal of Science & Technology*, 32(4), 1545–1563. Relevant prior work on Kelantan/Sarawak dialect ASR using transfer learning. **Extract and verify actual corpus sizes, model configurations and reported error metrics from the paper before comparing results.** https://doi.org/10.47836/pjst.32.4.06
- **Potential external corpus:** https://github.com/pingtt/malay_dialects . Inspect repository contents, licence, speaker overlap and ground-truth quality before any download or benchmark use. Do not assume permission or that all referenced audio is downloadable.

### Proposed literature matrix (to populate from full texts)
| Source | Research focus | Relevance to RedScribe | Verification still required |
| --- | --- | --- | --- |
| Wu (2023) | Comparative linguistic description | Phonology and district-sensitive annotation | Precise rules, IPA and page numbers |
| Muhamad & Mohd Rusli (2024) | Kelantan dialect and Malay learning | Candidate phonological error categories | Sample, rule taxonomy and examples |
| Khaw & Tan (2014) | MaDiTS corpus, translation and speech synthesis | Orthographic and pronunciation mappings | Dataset availability and reuse rights |
| Tan et al. (2024) | Low-resource dialect ASR transfer learning | Baseline and external comparison | Corpus size, split, WER/CER and licence |
| pingtt/malay_dialects | Potential external data repository | Possible independent benchmark set | Files, licence, provenance and leakage |

### Evaluation implications
1. **Primary:** unchanged dialect-verbatim reference and raw ASR hypotheses; calculate WER and CER under a published, frozen scoring convention.
2. **Secondary:** separately normalise reference and hypotheses with a reviewed lexicon; label normalised WER/CER as a different task.
3. **Phonological analysis:** examine errors for word-final nasals, rhotics, fricatives, stops, glottalisation and vowels, with human verification of each category.
4. **Fair comparison:** identical audio, splits and scoring across Whisper, Mesolitica, MMS, Qwen3-ASR and other supported RedScribe adapters; record checkpoint/version and decoding parameters.
5. **Reporting:** include speaker/district variation, code-switching, reference orthography, confidence intervals where appropriate and error examples with participant privacy safeguards.
6. **External data:** check licence and ensure no training/test overlap before treating third-party audio as independent evaluation.

### Research gap (provisional)
The identified literature motivates a controlled, reproducible comparison of the **specific** RedScribe ASR configurations on Kelantan dialect-verbatim speech. This is a proposed evaluation gap, **not** a claim that no prior multilingual ASR comparison exists.

### Publication checklist
- [ ] Read the full text of each cited study and confirm authors, year, title, venue, pages and DOI.
- [ ] Extract original phonetic transcriptions rather than treating informal '-ae' spellings as IPA.
- [ ] Verify every candidate rule with recorded examples and native-speaker review.
- [ ] Confirm external corpus access, licence, consent and model training overlap.
- [ ] Populate model-by-model WER/CER literature matrix with traceable tables/pages.
- [ ] Freeze annotation and normalisation rules before benchmark evaluation.
