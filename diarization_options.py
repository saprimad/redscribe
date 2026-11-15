"""Local pyannote pipeline choices; no imports or downloads of model runtimes."""
DEFAULT_DIARIZATION_MODEL = "pyannote/speaker-diarization-community-1"
DIARIZATION_MODELS = {
    "Community-1 (Recommended)": DEFAULT_DIARIZATION_MODEL,
    "3.1 (Legacy / comparison)": "pyannote/speaker-diarization-3.1",
}
DEFAULT_DIARIZATION_CHOICE = next(iter(DIARIZATION_MODELS))


def describe_diarization(choice):
    if DIARIZATION_MODELS[choice] == DEFAULT_DIARIZATION_MODEL:
        return "Recommended local pipeline. Accept Community-1 conditions on Hugging Face. Automatic or expected speaker count."
    return ("Older local pipeline for comparison. Accept both speaker-diarization-3.1 and segmentation-3.0 conditions "
            "on Hugging Face. Uses the same token; runtime compatibility still needs testing.")
