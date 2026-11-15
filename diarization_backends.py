"""Optional NVIDIA Sortformer adapter with the same turn schema as pyannote."""
import gc
import importlib
import math
import re

from model_options import ModelPreflightError

DEFAULT_DIARIZER = "pyannote Community-1"
SORTFORMER = "NVIDIA Sortformer"
SORTFORMER_CHECKPOINT = "nvidia/diar_streaming_sortformer_4spk-v2.1"
SORTFORMER_FILENAME = "diar_streaming_sortformer_4spk-v2.1.nemo"
DIARIZATION_MODELS = {
    DEFAULT_DIARIZER: "pyannote/speaker-diarization-community-1",
    SORTFORMER: SORTFORMER_CHECKPOINT,
}


def describe_diarizer(selected):
    if selected == SORTFORMER:
        return ("Sortformer v2.1: automatic detection, up to 4 speakers. Expected speaker count is not used. "
                "Requires optional NeMo runtime and CUDA; first use downloads weights. HF access rules depend on the checkpoint.")
    return "Community-1: automatic or expected speaker count. Requires Hugging Face access and accepted model conditions."


def preflight_diarizer(selected):
    if selected not in DIARIZATION_MODELS:
        raise ModelPreflightError("Unknown diarisation model. Choose a model in Settings.")
    if selected == DEFAULT_DIARIZER:
        return "pyannote Community-1 selected; model access will be checked when loading."
    try:
        torch = importlib.import_module("torch")
        if not torch.cuda.is_available():
            raise ModelPreflightError("NVIDIA Sortformer requires CUDA in this integration. Choose pyannote or check CUDA-enabled PyTorch.")
        runtime = importlib.import_module("nemo.collections.asr.models")
        getattr(runtime, "SortformerEncLabelModel")
    except ModelPreflightError:
        raise
    except Exception as exc:
        raise ModelPreflightError(
            "NVIDIA Sortformer runtime cannot load. Install the optional dependencies in a compatible environment:\n"
            "python -m pip install -r requirements-sortformer.txt\npython -m pip check\n\n"
            "NeMo is intended for a compatible Linux/CUDA environment; native Windows remains unvalidated. "
            "pyannote can still be selected without NeMo. No diarisation model was downloaded."
        ) from exc
    return "Sortformer NeMo runtime and CUDA available; automatic detection of up to 4 speakers."


def parse_sortformer_output(output, duration):
    """NeMo diarize(audio=[one_file]) returns List[List[str]]. Fail on API drift."""
    if not isinstance(output, list) or len(output) != 1 or not isinstance(output[0], list):
        raise ValueError("Unsupported Sortformer output; expected one recording with a list of speaker segments.")
    turns = []
    for segment in output[0]:
        if not isinstance(segment, str):
            raise ValueError("Unsupported Sortformer segment type.")
        parts = segment.split()
        if len(parts) != 3:
            raise ValueError("Invalid Sortformer speaker segment.")
        start, end = float(parts[0]), float(parts[1])
        match = re.fullmatch(r"(?:speaker_|SPEAKER_)?([0-3])", parts[2])
        if not match or not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start:
            raise ValueError("Invalid Sortformer timestamps or speaker index.")
        # Postprocessing frame rounding can slightly extend beyond audio duration.
        start, end = min(start, duration), min(end, duration)
        if end > start:
            turns.append({"start": start, "end": end, "speaker": f"SPEAKER_{int(match[1]):02d}"})
    return sorted(turns, key=lambda row: (row["start"], row["end"], row["speaker"]))


def run_sortformer(audio_path, hf_token=None, speaker_count_text="", progress_callback=None,
                   check_stop=lambda: None):
    """One continuous recording; keep speaker cache/IDs across NeMo internal chunks.

    No independent chunks with reset speaker identities. Leave diarisation model
    weights in FP32, independent of the ASR FP16 setting. No hidden CPU fallback.
    """
    def report(message):
        check_stop()
        if progress_callback:
            progress_callback(message)

    preflight_diarizer(SORTFORMER)
    import torch
    from huggingface_hub import hf_hub_download
    from nemo.collections.asr.models import SortformerEncLabelModel
    from faster_whisper.audio import decode_audio

    model = audio = output = None
    try:
        report("Sortformer: checking cached weights / downloading missing model files...")
        path = hf_hub_download(repo_id=SORTFORMER_CHECKPOINT, filename=SORTFORMER_FILENAME,
                               token=hf_token or None)
        report("Sortformer: loading diarisation model into CUDA memory (FP32)...")
        model = SortformerEncLabelModel.restore_from(restore_path=path, map_location=torch.device("cpu"))
        model.to(device="cuda", dtype=torch.float32).eval()
        # Model-card configuration for long recorded conversations.
        model.sortformer_modules.chunk_len = 340
        model.sortformer_modules.chunk_right_context = 40
        model.sortformer_modules.fifo_len = 40
        model.sortformer_modules.spkcache_update_period = 300
        model.sortformer_modules.spkcache_len = 188
        if speaker_count_text.strip():
            report("Sortformer uses automatic speaker count (up to 4); expected speaker count is not applied.")
        report("Sortformer ready. Preparing 16 kHz mono audio...")
        audio = decode_audio(audio_path, sampling_rate=16000)
        if not len(audio):
            raise ValueError("No decodable audio for Sortformer.")
        duration = len(audio) / 16000
        report("Sortformer: detecting speakers across the recording...")
        with torch.inference_mode():
            output = model.diarize(audio=[audio], sample_rate=16000, batch_size=1,
                                   num_workers=0, include_tensor_outputs=False, verbose=False)
        report("Sortformer: preparing speaker timeline...")
        return parse_sortformer_output(output, duration)
    finally:
        model = audio = output = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
