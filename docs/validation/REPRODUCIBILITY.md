# Reproducibility — initial provenance

Pilot manifests now capture Python, platform, processor, selected package versions, Git commit and dirty flag where available, and explicit Whisper decoding policy. Existing audio/reference/prediction hashes and model result device/precision are retained. Missing provenance is null, not guessed. Optional adapter parameters, exact model revisions, GPU/driver and RAM inventory, participant mapping and full dataset manifest remain pending. Local only; no participant data in CI. CI pending.
