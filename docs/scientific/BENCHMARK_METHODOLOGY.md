# Benchmark methodology — accuracy, aggregation and operational efficiency

**Applicable route:** structured model-major experiments using `rapidfuzz-levenshtein-editops-v1`. The legacy pilot/batch scorer is described separately below.

## 1. Measurement definition

Let R be the approved reference sequence and H the hypothesis sequence. Levenshtein edit distance is the minimum number of unit-cost substitutions (S), deletions (D) and insertions (I) converting R into H. N is the reference length; M is the hypothesis length. A specific minimum-cost alignment supplies the three counts.

$$
E=S+D+I,\qquad e=\frac{E}{N},\quad N>0
$$

$$
\mathrm{WER}_{\%}=100\frac{S_w+D_w+I_w}{N_w},\qquad
\mathrm{CER}_{\%}=100\frac{S_c+D_c+I_c}{N_c}.
$$

Matched units C=N-S-D and hypothesis length M=C+S+I=N-D+I. These identities provide consistency checks. E can exceed N, so WER and CER can exceed 100%; do not cap them or equate 100%-WER with semantic accuracy.

The implemented raw word sequence is Python `str.split()` (whitespace tokens). The character sequence is the Python string as Unicode code points, not grapheme clusters, bytes or linguistic phonemes. Case, punctuation, diacritics and whitespace within CER are retained; WER ignores whitespace variation between tokens but retains punctuation within tokens. No automatic lexical or Unicode normalisation is applied by the raw scorer. Adapter-side stripping and joining of segment/chunk output occur before scoring and must be documented as part of the hypothesis construction.

## 2. Worked synthetic examples

| Reference | Hypothesis | WER | CER |
| --- | --- | ---: | ---: |
| a b c | a x c | 1/3 = 33.33% | 1/5 = 20% |
| a b | a | 1/2 = 50% | 2/3 = 66.67% |
| a | a b c | 2/1 = 200% | 4/1 = 400% |
| a b | empty | 2/2 = 100% | 3/3 = 100% |
| a b | a  b | 0/2 = 0% | 1/3 = 33.33% |
| empty | a | Undefined | Undefined |

Empty references have undefined rates (None), even if edit counts are defined; the reference approval workflow rejects blank scoring text. Failed runs are different from a valid empty hypothesis: failed or unavailable observations are not assigned scores.

## 3. Engine and alignment

[Fast metric source](../../redscribe/benchmark/benchmark_fast_metrics.py) calls `rapidfuzz.distance.Levenshtein.editops`, counts replace/delete/insert tags, and uses the shared ErrorCounts class. The recorded P1 version is 3.14.3. RapidFuzz library documentation describes the operation API [1]. Do not claim a specific tie-break rule unless verified for the pinned implementation. Multiple optimal alignments can give the same E but different S/D/I allocations; granular error classification requires attention to alignment conventions [2].

The older [benchmark_metrics.py](../../redscribe/benchmark/benchmark_metrics.py) implements a row-wise dynamic-programming scorer, with substitution > deletion > insertion preference when candidate distances tie, O(NM) time and O(M) working memory. The legacy pilot and rescore modules call this scorer. Neither the presence of JiWER in requirements nor a NIST citation means RedScribe runs JiWER or SCLITE in its current model-major scoring route. NIST SCTK is a reference implementation for comparison [3]; an independent validation must align tokenisation, preprocessing, costs and denominator policies. Total edit distance equality does not guarantee identical S/D/I.

## 4. Aggregation and missingness

For valid recording observations j=1,...,n of a model:

$$
e_{\mathrm{corpus}}=\frac{\sum_j E_j}{\sum_j N_j},\qquad
e_{\mathrm{macro}}=\frac{1}{n}\sum_j\frac{E_j}{N_j}.
$$

Corpus rate weights by reference length; macro rate weights each valid recording equally. For N=(10,90) and E=(5,9), corpus rate is 14%, macro rate is 30%. Do not average rounded percentages or pool different reference versions.

[Reporting source](../../redscribe/benchmark/benchmark_reporting.py) distinguishes all_attempted and common_completed cohorts. The common cohort requires valid word and character scores for all compared models. Use this same cohort for principal cross-model accuracy comparison; explicitly report missing outcomes, reasons, and per-model denominators. All-attempted results describe the available data for a model, not necessarily a comparable set. Completion and valid scoring are distinct from cleanup success and scientific eligibility.

## 5. Timing

The scheduler records loading wall-clock time for a model session, optional warm-up time and recording-level inference wall-clock time using perf_counter. The recorded inference interval includes progress callback, parent-side reference checks, optional monitor setup/teardown, worker request/response, per-recording audio decoding and prediction construction, in addition to model inference; it ends before checkpoint scoring/export. It is not isolated GPU kernel execution time and excludes the initial model loading interval. Loading includes session creation, process start and applicable model preparation/download overhead. Session loading is counted once per observed session in the efficiency summary. The reported loading+inference sum is not full experiment elapsed time; it excludes warm-up, scoring, cleanup, reporting and other work.

$$
\mathrm{RTF}_j=\frac{t_{\mathrm{inference},j}}{t_{\mathrm{audio},j}},
\qquad
\mathrm{RTF}_{\mathrm{aggregate}}=\frac{\sum_j t_{\mathrm{inference},j}}{\sum_j t_{\mathrm{audio},j}}.
$$

For 60 s of source audio and 12 s recorded inference, RTF=0.2. RTF is dimensionless. An RTF below 1 means the measured interval is shorter than source duration, not that audio coverage or accuracy was established. Mean and median RTF are computed over valid timed recordings and differ from aggregate RTF. The efficiency export uses valid positive audio/inference times; it can include a different cohort from the common accuracy cohort. The accuracy–speed plot uses common-completed recordings with valid timing for each plotted model.

Use a fixed cache state, explicit warm-up policy, background-load controls and consistent timing boundary in the official study. Verify asynchronous execution boundaries and record any overhead; the current scheduler measures an end-to-end inference request, not GPU-only timing.

## 6. Resource monitoring

The optional [ResourceMonitor](../../redscribe/benchmark/benchmark_resources.py) samples nvidia-smi GPU index 0 system-wide utilisation, memory and temperature, plus psutil CPU and RAM if available. The 0.5 s wait is nominal; actual cadence includes collection time, subprocess latency and scheduling. Sampled maxima are lower-resolution observed peaks, not true continuous maxima or per-model allocations. NVIDIA memory units should be reconciled with the displayed MB labels (nvidia-smi commonly reports MiB); RAM is explicitly divided by 1024 squared in code. Sample count includes polling attempts even if every measurement in an attempt is missing. A non-zero count alone cannot establish GPU telemetry availability. Record the count together with the availability of each reported peak. The matrix path retains summary peaks/sample counts; do not assume per-sample CSV traces are produced by that route simply because the sampler implements save_csv.

## 7. Dataset descriptives and interpretation

The active runner measures decoded duration and counts reference units. A reference word-count divided by full recording duration in minutes is a recording-level word-density measure, not articulation rate or individual speaking rate. For P1: 4692/(2261.969/60) = approximately 124.46 reference words/minute of recording. Audio metadata, VAD, overlap, signal quality and speaker-specific speech activity require additional validated measurement or an explicitly separate analysis; historical pilot speech-analysis functions do not establish that these fields were collected in P1.

CER supplements WER, especially where word segmentation conventions differ; evidence from other languages is not direct validation for Kelantan Malay [4]. Raw WER/CER are orthographic edit measures, not semantic fidelity. Do not attribute a deletion to speech rate or an insertion to hallucination without inspecting aligned audio and hypothesis evidence.

## References

[1] RapidFuzz, “Levenshtein distance,” API documentation. https://rapidfuzz.github.io/RapidFuzz/Usage/distance/Levenshtein.html

[2] K. Kuhn, V. Kersken, and G. Zimmermann, “Beyond Levenshtein: Leveraging Multiple Algorithms for Robust Word Error Rate Computations and Granular Error Classifications,” *Proc. Interspeech*, pp. 4543–4547, 2024. https://doi.org/10.21437/Interspeech.2024-32

[3] National Institute of Standards and Technology, “SCLITE scoring documentation,” SCTK. https://github.com/usnistgov/SCTK/blob/master/doc/sclite.htm

[4] T. D. K, J. James, D. P. Gopinath, and M. A. K, “Advocating Character Error Rate for Multilingual ASR Evaluation,” *Findings of ACL: NAACL 2025*, pp. 4941–4950, 2025. https://doi.org/10.18653/v1/2025.findings-naacl.277
