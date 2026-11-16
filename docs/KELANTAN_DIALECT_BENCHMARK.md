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


## Critical reading: proposed additional rule families (v0.3; 2026-11-16)

**Evidence policy:** This is a source-grounded *candidate taxonomy for analysis*, not a validated deterministic Standard Malay → Kelantan converter. Distinguish (a) explicitly documented linguistic phenomena, (b) proposed ASR error tags, and (c) unverified spelling correspondences. Do not silently add new example word mappings.

### Sources inspected directly
1. Jiang Wu (2023), *Malayic varieties of Kelantan and Terengganu*, Chapter 2 (Kelantan phonology), especially pp. 49–53, 74, and Chapter 5 (morphology). https://www.lotpublications.nl/Documents/651_fulltext.pdf
2. Nur Eliana Muhamad & Nur Farahkhanna Mohd Rusli (2024), article abstract and listed seven phonological processes; **full article examples still require extraction and checking**. https://spaj.ukm.my/jpbm/index.php/jpbm/article/view/387/0
3. Khaw & Tan (2014), ISCA abstract: corpus translation/G2P, not ASR accuracy. https://www.isca-archive.org/slam_2014/khaw14_slam.html

### New candidate analysis rules (do NOT run as global text substitutions)
| ID | Feature / proposed error tag | Direct support | Implementation / verification requirement |
| --- | --- | --- | --- |
| R13 | Phonemic nasal vowel vs contextual vowel nasalisation | Wu (2023), §2.2.2.1, pp. 49–50 | Separate tags; annotate from audio, not from casual '-ae' spellings |
| R14 | /e/ vs /ɛ/ and /o/ vs /ɔ/ contrasts | Wu (2023), Tables 2.7–2.8, pp. 51–53 | Preserve distinctions in phonetic reference; normal orthography may obscure them |
| R15 | Oral vs phonemic nasal vowel minimal-pair contrasts | Wu (2023), Table 2.8, p. 53 | Create phonetic contrast tests; do not equate every deleted final nasal with phonemic nasal vowel |
| R16 | Final glottal stop /ʔ/ as distinct coda | Wu (2023), §2.3; Muhamad & Mohd Rusli (2024) abstract for /p,t,k/ → [ʔ] | Tag coda substitution and deletion, audio-check each example |
| R17 | Word-final /s/ → [h] | Muhamad & Mohd Rusli (2024), abstract | Audit existing R05/R11/R12 instead of creating duplicate blanket suffix rules |
| R18 | Rhotic deletion | Muhamad & Mohd Rusli (2024), abstract | Audit existing R04; record environment and exceptions |
| R19 | Final nasal deletion | Muhamad & Mohd Rusli (2024), abstract | Audit R01–R03; do not assume all nasals behave identically |
| R20 | Syllable template (C)(C)V(C) | Wu (2023), §2.3, p. 53 | Syllable-level error annotation, not a text replacement |
| R21 | Complex onsets / consonant clusters | Wu (2023), §§2.5–2.6 | Tag ASR vowel insertion or consonant loss in clusters |
| R22 | Vowel sequences versus diphthongs | Wu (2023), §§2.7 and 2.9; no phonemic diphthongs in KM analysis | Tag vowel segmentation; do not treat informal 'ae' spelling as IPA diphthong |
| R23 | Initial gemination | Wu (2023), §5.3.2 | Potential morphophonological error category; inspect examples and recording before implementing |
| R24 | Prefixation and morphophonological alternations | Wu (2023), §5.3.1 | Track affix/word-form errors separately from lexical substitutions |
| R25 | Function words, pronouns, negators and discourse particles | Wu (2023), Chapter 6; lexical studies cited by Muhamad & Mohd Rusli (2024) | Build context-tagged lexicon; avoid one-to-one replacement without semantic review |
| R26 | District/idiolect-sensitive variants | Wu (2023), comparative fieldwork and linguistic variation | Stratify by speaker and locality; never force a single spelling across districts |

### Critical corrections to v0.1
- **Important:** Wu (2023, p. 50) represents 'to eat' as /makɛ/ with phonetic [mãkɛ]. This shows that nasalisation can be *contextual*; the informal spelling `makae` is **not** a reliable IPA representation of a phonemic nasal vowel. Keep R01 as an orthographic candidate only.
- Wu (2023) reports **eight oral and four phonemic nasal vowels** in his Kelantan analysis; this does not mean every nasalised vowel is phonemic.
- Existing R02/R03/R06–R12 need direct audio validation. A few spellings may be regional, lexical or inaccurate; no automatic suffix substitutions should be deployed.
- A 2024 school-based study with eight respondents supports a *process taxonomy*, not a universal conversion engine for all Kelantan speakers.
- Rules R13–R26 are **analysis tags / candidate feature families**, not 14 verified new pronunciation transformations.

### Recommended validation table
`rule_id | phenomenon | standard_form | dialect_practical | IPA_reference | audio_id | district | speaker_id | source_page | evidence_level | verified_by | verification_status | exception_notes`

Evidence levels: `published_explicit`, `published_inferred`, `speaker_confirmed`, `hypothesis_only`. Status: `pending`, `accepted`, `rejected`, `district_specific`.

### Implementation decision
**Documentation only**. Do not modify live RedScribe ASR outputs or the scoring pipeline until reference orthography, annotator agreement, and exceptions are defined. Raw verbatim WER/CER remain primary; normalised scores remain secondary.
