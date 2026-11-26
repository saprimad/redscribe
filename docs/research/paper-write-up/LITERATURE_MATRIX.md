# Preliminary literature matrix

37 seed references and resources, not a systematic review. All bibliographic details and full texts require verification; some entries are datasets or theses. A: dialect; B: benchmarking; C: low-resource ASR; D: code-switching; E: metrics; F: reliability; G: corpus development.

| ID | Reference/resource | Extraction priority |
|---|---|---|
| A01 | [Tan et al. (2024), Low Resource Malay Dialect ASR](https://doi.org/10.47836/pjst.32.4.06) | Kelantan/Sarawak transfer learning |
| A02 | [Hybrid Distance-Statistical-Based Phrase Alignment](https://jice.um.edu.my/index.php/MJCS/article/view/17451) | Parallel dialect alignment; verify citation |
| A03 | [Malay Dialect Conversation Speech Corpus](https://github.com/pingtt/malay_dialects) | External corpus; licence and training overlap |
| A04 | [Dialectal Malay Speech Synthesis Acoustic Model](https://journals.utm.my/jurnalteknologi/article/view/6514) | Historical dialect resources |
| A05 | [Common Voice Malay 27.0](https://mozilladatacollective.com/datasets/cmu617r0400jjo1072jneryvg) | Scripted speech; verify version |
| B01 | [Abdul Malik et al. (2026), Beyond Conventional ASR Metrics](https://doi.org/10.14569/IJACSA.2026.0171021) | Key comparator; full-text extraction below |
| B02 | [Open ASR Leaderboard](https://arxiv.org/abs/2510.06961) | Reproducible accuracy and efficiency |
| B03 | [SpeechColab Leaderboard](https://www.sciencedirect.com/science/article/pii/S0885230825000300) | Evaluation infrastructure |
| B04 | [Long-term care interview ASR study](https://pmc.ncbi.nlm.nih.gov/articles/PMC9933064/) | Research interview transcription |
| C01 | [Besacier et al. (2014)](https://doi.org/10.1016/j.specom.2013.07.008) | Under-resourced ASR survey |
| C02 | [Fatehi et al. (2025)](https://doi.org/10.1016/j.specom.2024.103151) | Low-resource evaluation |
| C03 | [Babu et al. (2022), XLS-R](https://doi.org/10.21437/Interspeech.2022-143) | Cross-lingual representations |
| C04 | [Conneau et al., FLEURS](https://doi.org/10.1109/SLT54892.2023.10023141) | Multilingual corpus |
| C05 | [Radford et al., Whisper](https://arxiv.org/abs/2212.04356) | Foundation model |
| C06 | [Shi et al. (2026), Qwen3-ASR](https://arxiv.org/abs/2601.21337) | Model architecture |
| C07 | [Zhang et al. (2025)](https://doi.org/10.21437/Interspeech.2025-1358) | Low-resource speech fluency |
| D01 | [Mustafa et al. (2022)](https://doi.org/10.3390/app12199541) | Code-switching review |
| D02 | [Agro et al. (2026)](https://doi.org/10.63317/477upr9ikf9n) | End-to-end code-switching review |
| D03 | [Biswas et al. (2022)](https://doi.org/10.1016/j.csl.2021.101262) | Domain-specific multilingual speech |
| D04 | [Nguyen & Dat (2025)](https://doi.org/10.21437/Interspeech.2025-654) | Synthetic code-switch data |
| D05 | [Nguyen & Tran (2025), AsyncSwitch](https://doi.org/10.1109/ASRU65441.2025.11434656) | Malay-English adaptation |
| D06 | [Yang et al. (2024)](https://doi.org/10.1109/ICASSPW62465.2024.10626762) | Zero-shot code-switched ASR |
| E01 | [Morris et al. (2004)](https://doi.org/10.21437/Interspeech.2004-668) | WER, MER, WIL |
| E02 | [He et al. (2011)](https://doi.org/10.1109/ICASSP.2011.5947637) | WER and downstream translation |
| E03 | [Kim et al. (2021)](https://doi.org/10.21437/Interspeech.2021-1929) | Semantic Distance |
| E04 | [Kim et al. (2022)](https://doi.org/10.21437/Interspeech.2022-11144) | User perception |
| E05 | [Rugayan et al. (2022)](https://doi.org/10.21437/Interspeech.2022-143) | Semantic metrics |
| E06 | [Rugayan & Salvi (2023)](https://doi.org/10.21437/Interspeech.2023-2175) | Task-oriented assessment |
| E07 | [Sasindran et al. (2024), SeMaScore](https://doi.org/10.21437/Interspeech.2024-2033) | Combined semantic and lexical metrics |
| E08 | [Liang et al. (2025)](https://doi.org/10.18653/v1/2025.emnlp-main.1591) | Whisper sub-token errors |
| F01 | [Fleiss (1971)](https://doi.org/10.1037/h0031619) | Inter-rater agreement |
| F02 | [Landis & Koch (1977)](https://doi.org/10.2307/2529310) | Agreement interpretation |
| G01 | [Khaw & Tan (2014), MaDiTS](https://www.isca-archive.org/slam_2014/khaw14_slam.html) | Dialect corpus preparation |
| G02 | [Khaw (2017)](https://eprints.usm.my/45395/) | Dialect models and phonetics |
| G03 | [Parallel Dialect Text Collection](https://dspace-cris.utar.edu.my/entities/publication/bf586850-b5ea-43cc-80b1-1cf10b75278c) | Parallel text |
| G04 | [Gebru et al. (2021), Datasheets for Datasets](https://doi.org/10.1145/3458723) | Dataset governance |
| G05 | [Pengaruh Dialek dalam Pertuturan Bahasa Melayu Standard](https://jurnal.dbp.my/index.php/jurnalbahasa/en/article/view/8168) | Phonological variation |

## Key comparator: Abdul Malik et al. (2026)
Full-text reading: IJACSA 17(10), 234–240. One Malay-English code-switched recording, 30 purposive windows out of 289 candidates, 826 reference words. No named regional dialect. Three models/four pipelines; three semantic raters. Qwen without prompt: WER 29.18%, CER 20.60%; Mesolitica: WER 30.39%, CER 21.71%, semantic preservation 53.3%; Qwen prompted: WER 32.20%, CER 23.20%; Faster-Whisper turbo: WER 65.86%, CER 52.69%. Semantic differences not significant (p=.134). Limitations include undocumented independent reference verification, single recording, incomplete raw/pre-QC predictions and execution manifests, no standardised speed/memory evaluation. Future work proposes multiple recordings/speakers, recording-level resampling, verified references, error taxonomy, raw-output archival and operational benchmarking. See pp. 235–239. RedScribe can investigate several of these gaps; novelty is not established by one comparator.
