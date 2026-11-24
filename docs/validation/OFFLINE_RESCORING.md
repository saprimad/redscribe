# Offline re-scoring

Run `python -m redscribe.benchmark.benchmark_rescore RUN_MANIFEST REFERENCE_MANIFEST NEW_REPORT.json [--model MODEL_KEY]` from repository root. CPU-only, no ASR imports. Verifies reference/source and prediction hashes and byte count; compares original WER/CER and error counts. Output is exclusive, never overwrites. Supports all models in one pilot manifest or one selected model. Legacy predictions without hashes are unverifiable. Multi-recording batch orchestration and GUI integration remain pending. CI pending. Local private files only.
