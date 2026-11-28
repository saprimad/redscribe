# Windows GPU acceptance run for v2.1.0 preparation

Candidate test and application tree: 5da7f53c72e3c834228d0214e048ddc814009882. This immutable revision includes the corrected test infrastructure. If production code, dependencies or scoring change, repeat acceptance on the successor. Use a dedicated, private validation folder outside the checkout. Use an authorised non-study clip for smoke tests and one authorised full-length recording with an approved verbatim reference for technical validation. Never reuse an official experiment directory. Keep credentials, local paths, audio, logs and hashes in restricted storage.

## 1. Check out and identify the candidate

Run PowerShell in the existing validated Python 3.11 CUDA environment. These commands create a separate checkout. Keep existing experiments and environments intact.

```powershell
$rev = '5da7f53c72e3c834228d0214e048ddc814009882'
$dst = Join-Path $env:USERPROFILE 'Documents\RedScribe-QA-5da7f53'
git clone https://github.com/saprimad/redscribe.git $dst
if ($LASTEXITCODE) { throw 'Clone failed' }
Set-Location $dst
git switch --detach $rev
if ($LASTEXITCODE -or (git rev-parse HEAD) -ne $rev) { throw 'Wrong revision' }
if (git status --porcelain) { throw 'Use a clean checkout' }
$py = (Get-Command python -ErrorAction Stop).Source
& $py -c "import sys; print(sys.executable,sys.version); assert sys.version_info[:2]==(3,11)"
if ($LASTEXITCODE) { throw 'Select the validated Python 3.11 environment' }
& $py -m pip check
if ($LASTEXITCODE) { throw 'Resolve dependency conflicts before testing' }
& $py -m pip freeze
ffmpeg -version
if ($LASTEXITCODE) { throw 'FFmpeg unavailable' }
Get-CimInstance Win32_Processor | Select-Object Name,NumberOfLogicalProcessors
Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize,FreePhysicalMemory
nvidia-smi --query-gpu=index,uuid,name,driver_version,memory.total,memory.free --format=csv
if ($LASTEXITCODE) { throw 'NVIDIA driver inventory unavailable' }
& $py -c "import torch,torchaudio,ctranslate2,faster_whisper,pyannote.audio,transformers,qwen_asr,soundfile,docx,openpyxl,rapidfuzz,jiwer,psutil; print(torch.__version__,torch.version.cuda,torch.cuda.device_count()); assert torch.cuda.is_available(); print(torch.cuda.get_device_name(0),torch.cuda.mem_get_info(0)); assert 'float16' in ctranslate2.get_supported_compute_types('cuda',0); x=torch.ones((32,32),device='cuda',dtype=torch.float16); y=x@x; torch.cuda.synchronize(); assert y[0,0].item()==32"
if ($LASTEXITCODE) { throw 'CUDA, FP16 or an adapter dependency failed preflight' }
$env:PYTHONUTF8 = '1'
& $py scripts/validate_regression.py
if ($LASTEXITCODE) { throw 'Regression validation failed or tests skipped' }
& $py -X faulthandler -u redscribe_gpu.py
```

Expected workstation inventory is Intel Core i5-14400F, RTX 5070 with nominal 12 GB VRAM and 64 GB installed RAM. Record actual device index, free and total memory, driver, CUDA build, compute type, Python and dependency versions at launch. The numerical FP16 probe exercises PyTorch. Each of the seven adapters still needs a native run.

## 2. Exercise the two normal entry points

1. Transcription Mode: select the non-sensitive clip, choose Large-v3, set the intended language and record the diarisation setting. Start, observe live updates, and verify the Word transcript, Excel workbook and performance log open. Exercise stop on a second clip, wait for cleanup, then start another run. If testing diarisation, confirm speaker attribution and diarisation status rather than accepting fallback silently.
2. Switch to Benchmark Mode in the same window, then return. Confirm the previous transcription view is restored. Re-enter Benchmark Mode. Review and freeze the clip's reference, confirm recording pairing and run one model with strict CUDA FP16. Accept a completed scored observation, positive duration, readable PDF/XLSX and clean worker exit. Check the UI prevents switching while busy.

## 3. Validate all seven models on one full recording

- In a fresh experiment directory select the seven default models. Verify the approved reference digest, source digest, recording duration and language, CUDA FP16 policy, warm-up/cache policy, device mapping and monitoring choice. Record UTC times and local package versions. Keep an independent record of the input hashes using Get-FileHash -Algorithm SHA256.
- For each model retain resolved repository, snapshot SHA and actual weight/config identities from the loaded files. Record adapter identifier, language/adapter, resampling, chunk size, attention mask where applicable, beams, token ceiling, VAD, dtype and effective device from the actual session. Record inherited backend defaults with library version. A registry label or requested configuration alone leaves the item open.
- Verify full audio coverage for each backend on a separate diagnostic replay where necessary. Compare decoded duration and sample count at the expected sample rate. For chunked models collect actual submitted start/end sample positions, post-processor frame length, padding/truncation, empty chunks and end-of-file. Require complete interval union and explain any overlaps. For streaming/Faster-Whisper verify decoder input duration, actual consumed frames including the tail, generator exhaustion and VAD policy. Inspect consented beginning, middle, boundaries and tail. Speech timestamps need not reach trailing silence. If the backend cannot expose these measurements, record coverage as unverified and retain the diagnostic requirement.
- Enable resource monitoring and inspect actual non-null GPU/RAM readings, sample counts, device index and units. Compare with an independent nvidia-smi trace. Record available memory at start, background load and cache state. Separate loading, warm-up and inference wall time. Use a separate device-synchronised timing trial for hardware efficiency claims.
- Repeat in a second fresh experiment directory with identical inputs, model revisions and configuration. Compare per-model prediction hashes, reference counts, S/D/I, WER and CER. Record any differences and investigate non-determinism. Report timing variation separately. A resumed run cannot establish repeatability.
- In a separate restart trial stop after at least one model completes. Resume using the same frozen experiment identity. Verify the previously completed prediction SHA-256 and recomputed score fields, remaining successful cells, absence of duplicate results and clean finalisation. A changed input, model or reference must start a new identity.
- Open the PDF and XLSX. Expect seven eligible model rows per applicable cohort, seven recording results and efficiency rows for completed models. Match S/D/I, reference lengths, WER/CER, RTF, units, per-model status and any missing measurements. Recompute rates and RTF from unrounded cells. Verify publication manifest digests with Get-FileHash; confirm every declared artefact exists. Retain original manifests and reports privately.
- Record PASS, FAIL or UNVERIFIED per model per criterion. On a crash or mismatch preserve the exit code, versions, traceback, progress point, restricted logs and unchanged checkpoint. Reproduce on a synthetic clip, then isolate the affected model or stage. Do not edit a prediction or reference to repair the score. Release sign-off needs both modes, seven native sessions, verified coverage and repeatability, resume and export evidence. Report any unobservable gate explicitly.

This technical exercise uses one authorised full-length recording. The official 25-recording comparison has separate authorisation, freezing and statistical requirements. See [integrity gates](../scientific/INTEGRITY.md).

## 4. Restricted evidence record

Make a private copy of this section for each acceptance run. Record the operator, UTC start/end, candidate SHA, clean-tree result, input and reference version, selected model keys, cold/warm cache conditions, warm-up policy, and monitoring choice. Record only private evidence locators for logs, digests and source material. A public summary may give the candidate, criterion, status and reason after disclosure review. The table starts unverified; it records no new Windows observations.

| Criterion | Available evidence | Additional evidence needed for acceptance |
|---|---|---|
| A. Native execution and cleanup | Private matrix fields `status`, `device`, `precision`, `worker_exit_code`, `cleanup_status`, `shutdown_strategy` and linked worker log | Confirm one applicable row for each of the seven models with completed scoring, CUDA, FP16, exit 0 and successful cleanup. Keep the actual exit strategy. |
| B. Resolved model and decoding | `model_provenance` contains the model key and exposed revision. Local adapters additionally record checkpoint, language and chunking label. Faster-Whisper records beam size, task, VAD and conditioning. | Resolve the exact cached artefacts opened for each native session, including tokenizer, processor and config. Record effective backend defaults and file hashes privately. An absent revision or a bare registry label leaves identity unverified. |
| C. End-to-end coverage | Duration is measured in a separate decode. The local backend slices a 16 kHz waveform. Faster-Whisper consumes a segment iterator. Both return a string. The matrix stores no per-model sample ledger. | Retain a separately labelled diagnostic replay tracing submitted and processed samples or frames, tail handling, token limits and any exclusions. Reconcile the trace with the same frozen input. A coarse segment end time alone cannot establish full consumption. |
| D. Efficiency | `session_loading_seconds`, `session_warmup_seconds` where applicable, `inference_seconds`, `audio_seconds`, `rtf`, sampled resource peaks and sample count | Check independent arithmetic and device mapping. Archive the external trace with sampling interval, units and timing boundaries. A GPU synchronisation in the parent process does not time kernels in a separate model worker. Hardware-only timing needs a measurement in the executing worker or an appropriately scoped external profiler. |
| E. Fresh-run repeatability | Separate private checkpoints A and B each contain `prediction_sha256`, edit counts, denominators and rates | Compare on identical model/recording pairs with matching frozen identity fields and effective revisions. Keep both raw outputs on a mismatch and classify text, score and timing variation separately. |
| F. Interrupted-run recovery | Saved prediction hash and verified recalculation of score fields determine cell reuse. Cleanup fields describe a separate event. | Keep pre-stop and resumed checkpoint snapshots. Confirm retained session IDs and prediction hashes for reused cells, newly executed pending cells, final cardinality and integrity verification. |
| G. Publication integrity | The structured publication manifest lists public file digests. The internal manifest covers working exports. Neither provides a signature. | Verify each manifest against its own directory. Check consent and the scope of the intended disclosure separately. Keep the internal manifest, unfiltered working folder and raw traces private. |

For each model record A–G as PASS, FAIL or UNVERIFIED, with one evidence locator and an observation or failure reason for each decision. Record the two-mode UI checks separately. Keep an operator decision, UTC date and unresolved gates with the private record. This acceptance procedure remains pending until completed on the target workstation.

Source mappings: [native controller and resume verification](../../redscribe/benchmark/benchmark_model_major_batch.py), [local adapter](../../redscribe/benchmark/benchmark_local_session.py), [Faster-Whisper adapter](../../redscribe/benchmark/benchmark_whisper_session.py), [resource sampler](../../redscribe/benchmark/benchmark_resources.py) and [structured publication](../../redscribe/benchmark/benchmark_structured_output.py).

### Operator sign-off copy

| Model | A | B | C | D | E | F | G | Restricted evidence reference |
|---|---|---|---|---|---|---|---|---|
| Whisper Large-v3 | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | Pending |
| Whisper Large-v3 Turbo | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | Pending |
| Mesolitica Whisper v3 | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | Pending |
| Mesolitica XLS-R 300M | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | Pending |
| Meta MMS Malay | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | Pending |
| Qwen3-ASR 1.7B | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | Pending |
| BuzzASR Malay | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | Pending |

Operator: ______  Candidate SHA: ______  Date (UTC): ______  Two-mode result: ______  Decision and outstanding evidence: ______
