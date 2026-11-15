import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk, font as tkfont
from faster_whisper import WhisperModel
import threading
import time
import os
import re
import shutil
import subprocess
import tempfile
import gc
import traceback
import json
import math
from io import BytesIO
from collections import Counter
from token_store import TokenStoreError, resolve_token, save_token, remove_saved_token

from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.label import DataLabelList
from docx import Document
from docx.shared import Inches
from matplotlib.figure import Figure


# =========================
# CONFIG
# =========================
DEFAULT_MODEL_SIZE = "large-v3"
WHISPER_MODELS = ("large-v3", "turbo", "medium", "small", "base")

# Whisper device priority: try the GPU first, then fall back to the CPU.
WHISPER_DEVICE_PRIORITY = ["cuda", "cpu"]

# Compute type selected for each device.
WHISPER_COMPUTE_TYPE = {
    "cuda": "float16",   # Fast and efficient on supported NVIDIA GPUs.
    "cpu": "int8"        # Reduces memory and processing requirements on CPUs.
}


def cpu_thread_budget() -> int:
    """Leave some logical processors available during CPU transcription.

    This limits worker threads, not total system CPU utilisation. Other
    processes and libraries can still use CPU time independently.
    """
    logical_processors = os.cpu_count() or 2
    seventy_percent = max(1, math.floor(logical_processors * 0.7))
    return min(seventy_percent, max(1, logical_processors - 2))

# Speaker diarisation model.
# Notes:
# 1. Install: pip install pyannote.audio
# 2. Sign in to Hugging Face, or provide a token through the GUI or HF_TOKEN.
# 3. Accept the model conditions on Hugging Face when required.
DIARIZATION_MODEL = "pyannote/speaker-diarization-community-1"

APP_VERSION = "2.0.0"
APP_TITLE = f"RedScribe v{APP_VERSION} – Research Speech Transcription System"
TRANSCRIPTION_LANGUAGES = {"Auto detect": None, "Bahasa Melayu": "ms", "English": "en"}


class TranscriptionCancelled(Exception):
    """The user requested a safe stop before report export began."""


def model_settings_path() -> str:
    config_root = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(config_root, "RedScribe", "settings.json")


def load_model_preference() -> str:
    try:
        with open(model_settings_path(), encoding="utf-8") as settings_file:
            selected = json.load(settings_file).get("whisper_model")
        if selected in WHISPER_MODELS:
            return selected
    except (OSError, ValueError, AttributeError):
        pass
    return DEFAULT_MODEL_SIZE


def save_model_preference(selected: str) -> None:
    if selected not in WHISPER_MODELS:
        raise ValueError("Unsupported Whisper model")
    path = model_settings_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # No token or study details are stored in this file.
    with open(path, "w", encoding="utf-8") as settings_file:
        json.dump({"whisper_model": selected}, settings_file)


# =========================
# UTILS
# =========================
def sec_to_hms(sec: float) -> str:
    sec = max(0, int(sec))
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def sec_to_mmss(sec: float) -> str:
    sec = max(0, int(sec))
    m = sec // 60
    s = sec % 60
    return f"{m:02d}:{s:02d}"


def split_sentences_universal(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    parts = re.split(r'(?<=[\.\!\?\u061F\u3002\uFF01\uFF1F])\s+', text)
    parts = [p.strip() for p in parts if p and p.strip()]
    return parts if parts else [text]


def distribute_times(start: float, end: float, sentences: list[str]) -> list[tuple[float, float, str]]:
    dur = max(0.0, end - start)
    if not sentences:
        return []
    if dur == 0:
        return [(start, end, s) for s in sentences]

    weights = [max(1, len(s)) for s in sentences]
    total = float(sum(weights))
    out = []
    t = float(start)

    for i, s in enumerate(sentences):
        if i == len(sentences) - 1:
            t2 = float(end)
        else:
            t2 = t + dur * (weights[i] / total)
        out.append((t, t2, s))
        t = t2
    return out


def basic_tokenize(text: str) -> list[str]:
    text = (text or "").lower()
    tokens = re.findall(r"[a-z0-9]+", text)
    return [t for t in tokens if len(t) >= 3]


def compute_timeline_density(utterance_rows: list[dict], audio_duration_s: float, interval_sec: int = 300):
    buckets = Counter()
    for r in utterance_rows:
        b = int(r["start_s"] // interval_sec)
        buckets[b] += 1

    max_bucket = int(audio_duration_s // interval_sec) if audio_duration_s > 0 else 0
    rows = []
    for b in range(0, max_bucket + 1):
        start_min = b * (interval_sec // 60)
        end_min = start_min + (interval_sec // 60)
        rows.append((f"{start_min}-{end_min}", buckets.get(b, 0)))
    return rows


def compute_speaker_summary(utterance_rows: list[dict]) -> list[tuple[str, int]]:
    speaker_counts = Counter()
    for row in utterance_rows:
        speaker = (row.get("speaker") or "UNKNOWN").strip()
        speaker_counts[speaker] += 1
    return speaker_counts.most_common()


def sanitize_part(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r'[<>:"/\\|?*\n\r\t]', "_", s)
    s = s.replace(" ", "_")
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


def build_output_name(project: str, period: str, label: str, researcher: str, audio_base: str) -> str:
    parts = [
        sanitize_part(project),
        sanitize_part(period),
        sanitize_part(label),
        sanitize_part(researcher),
    ]
    parts = [p for p in parts if p]
    if not parts:
        return sanitize_part(audio_base) or "transcription"
    return "_".join(parts)


def available_output_paths(folder: str, filename_base: str) -> tuple[str, str]:
    """Keep a Word/Excel pair together without overwriting a previous run."""
    suffix = 1
    while True:
        stem = filename_base if suffix == 1 else f"{filename_base}_{suffix}"
        xlsx_path = os.path.join(folder, f"{stem}.xlsx")
        docx_path = os.path.join(folder, f"{stem}.docx")
        if not os.path.exists(xlsx_path) and not os.path.exists(docx_path):
            return xlsx_path, docx_path
        suffix += 1


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def available_output_paths(folder: str, filename_base: str) -> tuple[str, str]:
    """Keep successive Word/Excel exports together without overwriting old results."""
    suffix = 1
    while True:
        stem = filename_base if suffix == 1 else f"{filename_base}_{suffix}"
        xlsx_path = os.path.join(folder, f"{stem}.xlsx")
        docx_path = os.path.join(folder, f"{stem}.docx")
        if not os.path.exists(xlsx_path) and not os.path.exists(docx_path):
            return xlsx_path, docx_path
        suffix += 1


def open_folder(path: str):
    try:
        os.startfile(path)
    except Exception:
        pass


def create_whisper_model(model_size: str):
    """
    Load Whisper on the GPU when possible, with an automatic CPU fallback.

    Return:
        model, actual_device, actual_compute_type
    """
    last_error = None

    for device in WHISPER_DEVICE_PRIORITY:
        compute_type = WHISPER_COMPUTE_TYPE.get(device, "int8")
        try:
            options = {"cpu_threads": cpu_thread_budget(), "num_workers": 1} if device == "cpu" else {}
            model = WhisperModel(model_size, device=device, compute_type=compute_type, **options)
            return model, device, compute_type
        except Exception as e:
            last_error = e

    raise RuntimeError(f"Unable to load the Whisper model on any available device. Last error: {last_error}")


def release_gpu_cache():
    """Release unreferenced model allocations between independent recordings."""
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass



def load_audio_for_pyannote(audio_path: str):
    """
    Load audio as an in-memory waveform for pyannote.

    Why this exists:
    Some Windows setups fail inside pyannote/torchcodec with:
    "name 'AudioDecoder' is not defined".
    Passing an already-loaded waveform avoids pyannote's built-in AudioDecoder path.

    Requires:
        pip install soundfile
        ffmpeg available in PATH
    """
    tmp_dir = tempfile.mkdtemp(prefix="redscribe_diarization_")
    wav_path = os.path.join(tmp_dir, "audio_16k_mono.wav")

    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel", "error",
            "-i", audio_path,
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            wav_path,
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
        except FileNotFoundError:
            raise RuntimeError(
                "FFmpeg was not found in PATH. Install FFmpeg, then close and reopen PowerShell. "
                "Example: winget install Gyan.FFmpeg"
            )
        except subprocess.CalledProcessError as e:
            err = (e.stderr or e.stdout or "").strip()
            raise RuntimeError(f"FFmpeg could not convert the audio for speaker diarisation. Error: {err}")

        try:
            import soundfile as sf
            import torch
        except Exception as e:
            raise RuntimeError(
                "The audio-loading dependencies are incomplete. Install SoundFile with: pip install soundfile\n\n"
                f"Original error: {e}"
            )

        data, sample_rate = sf.read(wav_path, dtype="float32", always_2d=False)
        if getattr(data, "ndim", 1) > 1:
            data = data.mean(axis=1)

        waveform = torch.from_numpy(data).float().unsqueeze(0)
        return {"waveform": waveform, "sample_rate": int(sample_rate)}

    finally:
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass


def create_diarization_pipeline(hf_token: str | None, preferred_device: str = "cpu"):
    """
    Load the pyannote speaker diarisation pipeline.

    The lazy import allows the application to open even when pyannote.audio is
    not installed. Transcription can therefore continue without diarisation.
    """
    try:
        from pyannote.audio import Pipeline
    except Exception as e:
        raise RuntimeError(
            "pyannote.audio is not installed. Install it with:\n"
            "pip install pyannote.audio\n\n"
            f"Original error: {e}"
        )

    token = (
        (hf_token or "").strip()
        or os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGINGFACE_HUB_TOKEN")
        or None
    )

    try:
        if token:
            pipeline = Pipeline.from_pretrained(DIARIZATION_MODEL, token=token)
        else:
            # Use the cached Hugging Face login when no token is entered.
            pipeline = Pipeline.from_pretrained(DIARIZATION_MODEL, token=True)
    except TypeError:
        # Compatibility fallback for older pyannote/huggingface_hub releases.
        if token:
            pipeline = Pipeline.from_pretrained(DIARIZATION_MODEL, use_auth_token=token)
        else:
            pipeline = Pipeline.from_pretrained(DIARIZATION_MODEL, use_auth_token=True)

    if pipeline is None:
        raise RuntimeError(
            "The speaker diarisation model could not be loaded. Confirm that the Hugging Face token "
            "is valid and that the model conditions have been accepted."
        )

    # Use the GPU for pyannote when CUDA is available and Whisper loaded on CUDA.
    if preferred_device == "cuda":
        try:
            import torch
            if torch.cuda.is_available():
                pipeline.to(torch.device("cuda"))
        except Exception:
            pass

    return pipeline


def run_diarization(audio_path: str, hf_token: str | None, preferred_device: str,
                    speaker_count_text: str = "", progress_callback=None) -> list[dict]:
    """
    Return list:
    [
        {"start": 0.0, "end": 3.2, "speaker": "SPEAKER_00"},
        ...
    ]
    """
    def report(stage, completed=None, total=None):
        if progress_callback is not None:
            progress_callback(stage, completed, total)

    report("Loading diarisation model...")
    pipeline = create_diarization_pipeline(hf_token, preferred_device)

    kwargs = {}
    speaker_count_text = (speaker_count_text or "").strip()
    if speaker_count_text:
        try:
            n_speakers = int(speaker_count_text)
            if n_speakers > 0:
                kwargs["num_speakers"] = n_speakers
        except ValueError:
            pass

    # Hooks report work within a stage, not a percentage of the entire run.
    last_update = 0.0
    last_stage = None

    def hook(step_name, step_artifact=None, *, completed=None, total=None, **_kwargs):
        nonlocal last_update, last_stage
        stage = {
            "segmentation": "Detecting speech...",
            "speaker_counting": "Estimating simultaneous speakers...",
            "embeddings": "Analysing speaker characteristics...",
            "discrete_diarization": "Preparing speaker timeline...",
        }.get(step_name, "Processing speaker diarisation...")
        # The full-embeddings event occurs just before global clustering.
        if step_name == "embeddings" and completed is None:
            stage = "Grouping speakers..."
        now = time.monotonic()
        finished = total is not None and completed is not None and completed >= total
        if stage != last_stage or finished or now - last_update >= 0.2:
            report(stage, completed, total)
            last_update, last_stage = now, stage

    try:
        report("Preparing audio for diarisation...")
        diarization_input = load_audio_for_pyannote(audio_path)
        report("Detecting speech...")
        diarization_output = pipeline(diarization_input, hook=hook, **kwargs)
    finally:
        del pipeline
        if "diarization_input" in locals():
            del diarization_input
        release_gpu_cache()

    # pyannote/speaker-diarization-community-1 returns a DiarizeOutput object.
    # The actual Annotation is inside .exclusive_speaker_diarization or .speaker_diarization.
    # Older pyannote pipelines may return the Annotation directly.
    diarization_annotation = None
    for attr_name in ("exclusive_speaker_diarization", "speaker_diarization"):
        if hasattr(diarization_output, attr_name):
            diarization_annotation = getattr(diarization_output, attr_name)
            if diarization_annotation is not None:
                break

    if diarization_annotation is None:
        diarization_annotation = diarization_output

    if not hasattr(diarization_annotation, "itertracks"):
        raise RuntimeError(
            "The pyannote output does not provide itertracks(). "
            f"Output type: {type(diarization_output).__name__}. "
            "Install a current pyannote.audio release and use the community-1 model."
        )

    turns = []
    for turn, _, speaker in diarization_annotation.itertracks(yield_label=True):
        turns.append({
            "start": float(turn.start),
            "end": float(turn.end),
            "speaker": str(speaker)
        })

    turns.sort(key=lambda x: (x["start"], x["end"]))
    return turns


def overlap_seconds(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def assign_speaker(start: float, end: float, diarization_turns: list[dict]) -> str:
    """
    Assign the speaker with the greatest overlap with a Whisper timestamp.

    When no overlap exists, use the segment midpoint as a fallback.
    """
    if not diarization_turns:
        return "UNKNOWN"

    best_speaker = "UNKNOWN"
    best_overlap = 0.0

    for turn in diarization_turns:
        ov = overlap_seconds(start, end, turn["start"], turn["end"])
        if ov > best_overlap:
            best_overlap = ov
            best_speaker = turn["speaker"]

    if best_overlap > 0:
        return best_speaker

    midpoint = (start + end) / 2.0
    for turn in diarization_turns:
        if turn["start"] <= midpoint <= turn["end"]:
            return turn["speaker"]

    return "UNKNOWN"


# =========================
# EXCEL WRITER
# =========================
def save_xlsx_with_early_report(
    xlsx_path: str,
    utterance_rows: list[dict],
    segment_ranges: list[tuple[float, float]],
    audio_path: str,
    audio_duration_s: float,
    processing_minutes: float,
    detected_language: str | None,
    meta_from_gui: dict,
    actual_device: str,
    actual_compute_type: str,
    whisper_model: str,
    diarization_enabled: bool,
    diarization_status: str,
    diarization_model: str
):
    wb = Workbook()

    ws1 = wb.active
    ws1.title = "Early_Report"

    ws1["A1"] = "Study & Processing Metadata"
    ws1["A1"].font = ws1["A1"].font.copy(bold=True)

    speaker_summary = compute_speaker_summary(utterance_rows)
    speakers_detected = ", ".join([speaker for speaker, _ in speaker_summary]) if speaker_summary else "None"

    meta = [
        ("Application", f"RedScribe v{APP_VERSION} – Research Speech Transcription System"),
        ("Project / Study", meta_from_gui.get("project", "")),
        ("Researcher", meta_from_gui.get("researcher", "")),
        ("Interview / Audio Label", meta_from_gui.get("label", "")),
        ("Processing Period", meta_from_gui.get("period", "")),
        ("Audio File", os.path.basename(audio_path)),
        ("Audio Duration", sec_to_hms(audio_duration_s)),
        ("Language (Detected/Selected)", detected_language or "Auto detect"),
        ("Model & Mode", f"{whisper_model} ({actual_device.upper()} | {actual_compute_type})"),
        ("Speaker Diarisation", "Enabled" if diarization_enabled else "Disabled"),
        ("Diarisation Status", diarization_status),
        ("Diarisation Model", diarization_model if diarization_enabled else "Not used"),
        ("Speakers Detected", speakers_detected),
        ("Processing Time", f"{processing_minutes} minutes"),
        ("Generated On", time.strftime("%Y-%m-%d %H:%M:%S")),
        ("Copyright", "© Mad Sapri Tumiran"),
        ("Support", "saprimad@moh.gov.my"),
    ]

    r = 3
    for k, v in meta:
        ws1[f"A{r}"] = k
        ws1[f"B{r}"] = v
        r += 1

    ws1[f"A{r+1}"] = "Transcription Summary"
    ws1[f"A{r+1}"].font = ws1[f"A{r+1}"].font.copy(bold=True)

    total_segments = len(segment_ranges)
    total_utterances = len(utterance_rows)

    all_text = " ".join([x["text"] for x in utterance_rows])
    tokens = basic_tokenize(all_text)
    token_count = len(tokens)
    avg_tokens = round(token_count / total_utterances, 2) if total_utterances else 0.0

    speech_s = 0.0
    for st, en in segment_ranges:
        if en > st:
            speech_s += (en - st)
    speech_s = max(0.0, min(speech_s, audio_duration_s))
    silence_s = max(0.0, audio_duration_s - speech_s)

    summary = [
        ("Total Segments Detected", total_segments),
        ("Total Utterances", total_utterances),
        ("Total Words/Tokens", token_count),
        ("Average Tokens per Utterance", avg_tokens),
        ("Speech Duration", sec_to_hms(speech_s)),
        ("Silence Duration", sec_to_hms(silence_s)),
        ("Total Speakers Detected", len([s for s, _ in speaker_summary if s != "UNKNOWN"])),
    ]

    r2 = r + 3
    for k, v in summary:
        ws1[f"A{r2}"] = k
        ws1[f"B{r2}"] = v
        r2 += 1

    r_spk = r2 + 2
    ws1[f"A{r_spk}"] = "Speaker Utterance Count"
    ws1[f"A{r_spk}"].font = ws1[f"A{r_spk}"].font.copy(bold=True)
    ws1[f"A{r_spk+2}"] = "Speaker"
    ws1[f"B{r_spk+2}"] = "Utterances"

    rr_spk = r_spk + 3
    for speaker, count in speaker_summary:
        ws1[f"A{rr_spk}"] = speaker
        ws1[f"B{rr_spk}"] = count
        rr_spk += 1

    r3 = max(rr_spk + 2, r2 + 5)
    ws1[f"A{r3}"] = "Speech vs Silence Distribution"
    ws1[f"A{r3}"].font = ws1[f"A{r3}"].font.copy(bold=True)

    ws1[f"A{r3+2}"] = "Category"
    ws1[f"B{r3+2}"] = "Duration (minutes)"

    speech_min = round(speech_s / 60.0, 3)
    silence_min = round(silence_s / 60.0, 3)

    ws1[f"A{r3+3}"] = "Speech"
    ws1[f"B{r3+3}"] = speech_min
    ws1[f"A{r3+4}"] = "Silence"
    ws1[f"B{r3+4}"] = silence_min

    chart1 = BarChart()
    chart1.type = "col"
    chart1.title = "Speech vs Silence Distribution"
    chart1.y_axis.title = "Duration (minutes)"
    chart1.x_axis.title = "Category"
    chart1.dataLabels = DataLabelList()
    chart1.dataLabels.showVal = True

    data = Reference(ws1, min_col=2, min_row=r3+2, max_row=r3+4)
    cats = Reference(ws1, min_col=1, min_row=r3+3, max_row=r3+4)
    chart1.add_data(data, titles_from_data=True)
    chart1.set_categories(cats)
    ws1.add_chart(chart1, f"D{r3+2}")

    r4 = r3 + 7
    ws1[f"A{r4}"] = "Timeline Density (5-minute intervals)"
    ws1[f"A{r4}"].font = ws1[f"A{r4}"].font.copy(bold=True)

    ws1[f"A{r4+2}"] = "Interval (min)"
    ws1[f"B{r4+2}"] = "Utterances"

    density_rows = compute_timeline_density(utterance_rows, audio_duration_s, interval_sec=300)
    start_table_row = r4 + 3
    rr = start_table_row
    for interval_label, count in density_rows:
        ws1[f"A{rr}"] = interval_label
        ws1[f"B{rr}"] = count
        rr += 1
    end_table_row = rr - 1

    chart2 = BarChart()
    chart2.type = "col"
    chart2.title = "Utterance Density Over Time"
    chart2.y_axis.title = "Utterance count"
    chart2.x_axis.title = "Time interval (min)"
    chart2.dataLabels = DataLabelList()
    chart2.dataLabels.showVal = False

    data2 = Reference(ws1, min_col=2, min_row=r4+2, max_row=end_table_row)
    cats2 = Reference(ws1, min_col=1, min_row=r4+3, max_row=end_table_row)
    chart2.add_data(data2, titles_from_data=True)
    chart2.set_categories(cats2)
    ws1.add_chart(chart2, f"D{r4+2}")

    r5 = end_table_row + 3
    ws1[f"A{r5}"] = "Top 20 Keywords (Frequency)"
    ws1[f"A{r5}"].font = ws1[f"A{r5}"].font.copy(bold=True)

    ws1[f"A{r5+2}"] = "Rank"
    ws1[f"B{r5+2}"] = "Keyword"
    ws1[f"C{r5+2}"] = "Frequency"

    freq = Counter(tokens).most_common(20)
    rrk = r5 + 3
    for i, (kw, n) in enumerate(freq, start=1):
        ws1[f"A{rrk}"] = i
        ws1[f"B{rrk}"] = kw
        ws1[f"C{rrk}"] = n
        rrk += 1

    ws1.column_dimensions["A"].width = 32
    ws1.column_dimensions["B"].width = 52
    ws1.column_dimensions["C"].width = 16
    ws1.column_dimensions["D"].width = 16
    ws1.column_dimensions["E"].width = 16
    ws1.column_dimensions["F"].width = 16

    ws2 = wb.create_sheet("Transcription")
    headers = [
        "Utterance No.",
        "Speaker",
        "Start Time (hh:mm:ss)",
        "End Time (hh:mm:ss)",
        "Auto Transcript (RedScribe)",
        "Researcher Verification / Correction",
        "Notes"
    ]
    ws2.append(headers)

    for i, rrow in enumerate(utterance_rows, start=1):
        ws2.append([
            i,
            rrow.get("speaker", "UNKNOWN"),
            sec_to_hms(rrow["start_s"]),
            sec_to_hms(rrow["end_s"]),
            rrow["text"],
            "",
            ""
        ])

    widths = [14, 18, 20, 18, 70, 40, 25]
    for col_idx, w in enumerate(widths, start=1):
        ws2.column_dimensions[get_column_letter(col_idx)].width = w

    wb.save(xlsx_path)


def group_consecutive_speaker_turns(utterance_rows: list[dict]) -> list[dict]:
    """Combine adjacent utterances from the same speaker for readable Word output."""
    turns = []
    for row in utterance_rows:
        text = (row.get("text") or "").strip()
        if not text:
            continue

        speaker = row.get("speaker") or "UNKNOWN"
        if turns and turns[-1]["speaker"] == speaker:
            turns[-1]["end_s"] = max(turns[-1]["end_s"], row["end_s"])
            turns[-1]["text"] += " " + text
        else:
            turns.append({
                "speaker": speaker,
                "start_s": row["start_s"],
                "end_s": row["end_s"],
                "text": text,
            })
    return turns


def add_report_table(document, rows: list[tuple[str, object]]):
    table = document.add_table(rows=0, cols=2)
    table.style = "Light Shading Accent 1"
    for label, value in rows:
        cells = table.add_row().cells
        cells[0].text = str(label)
        cells[1].text = str(value)
    return table


def add_bar_chart(document, labels: list[str], values: list[float], ylabel: str):
    """Add a self-contained chart image without writing temporary files."""
    figure = Figure(figsize=(6.2, 2.5), dpi=150)
    axis = figure.subplots()
    bars = axis.bar(labels, values, color="#4f81bd")
    axis.set_ylabel(ylabel)
    axis.grid(axis="y", alpha=0.25)
    axis.set_axisbelow(True)
    axis.bar_label(bars, padding=3, fmt="%g")
    figure.tight_layout()
    image = BytesIO()
    figure.savefig(image, format="png")
    image.seek(0)
    document.add_picture(image, width=Inches(5.8))


def save_docx_transcript(
    docx_path: str,
    utterance_rows: list[dict],
    segment_ranges: list[tuple[float, float]],
    audio_path: str,
    audio_duration_s: float,
    processing_minutes: float,
    detected_language: str | None,
    meta_from_gui: dict,
    actual_device: str,
    actual_compute_type: str,
    whisper_model: str,
    diarization_enabled: bool,
    diarization_status: str,
    diarization_model: str
):
    """Save the Excel early report and grouped transcript in an editable Word file."""
    document = Document()
    document.add_heading("RedScribe Research Report", 0)

    speaker_summary = compute_speaker_summary(utterance_rows)
    speakers_detected = ", ".join(s for s, _ in speaker_summary) if speaker_summary else "None"

    metadata = [
        ("Application", f"RedScribe v{APP_VERSION} – Research Speech Transcription System"),
        ("Project / Study", meta_from_gui.get("project", "")),
        ("Researcher", meta_from_gui.get("researcher", "")),
        ("Interview / Audio Label", meta_from_gui.get("label", "")),
        ("Processing Period", meta_from_gui.get("period", "")),
        ("Audio File", os.path.basename(audio_path)),
        ("Audio Duration", sec_to_hms(audio_duration_s)),
        ("Language (Detected/Selected)", detected_language or "Auto detect"),
        ("Model & Mode", f"{whisper_model} ({actual_device.upper()} | {actual_compute_type})"),
        ("Speaker Diarisation", "Enabled" if diarization_enabled else "Disabled"),
        ("Diarisation Status", diarization_status),
        ("Diarisation Model", diarization_model if diarization_enabled else "Not used"),
        ("Speakers Detected", speakers_detected),
        ("Processing Time", f"{processing_minutes} minutes"),
        ("Generated On", time.strftime("%Y-%m-%d %H:%M:%S")),
        ("Copyright", "© Mad Sapri Tumiran"),
        ("Support", "saprimad@moh.gov.my"),
    ]
    document.add_heading("Study & Processing Metadata", level=1)
    add_report_table(document, metadata)

    all_text = " ".join(row["text"] for row in utterance_rows)
    tokens = basic_tokenize(all_text)
    total_utterances = len(utterance_rows)
    speech_s = sum(max(0.0, end - start) for start, end in segment_ranges)
    speech_s = max(0.0, min(speech_s, audio_duration_s))
    silence_s = max(0.0, audio_duration_s - speech_s)
    summary = [
        ("Total Segments Detected", len(segment_ranges)),
        ("Total Utterances", total_utterances),
        ("Total Words/Tokens", len(tokens)),
        ("Average Tokens per Utterance", round(len(tokens) / total_utterances, 2) if total_utterances else 0.0),
        ("Speech Duration", sec_to_hms(speech_s)),
        ("Silence Duration", sec_to_hms(silence_s)),
        ("Total Speakers Detected", len([s for s, _ in speaker_summary if s != "UNKNOWN"])),
    ]
    document.add_heading("Transcription Summary", level=1)
    add_report_table(document, summary)

    document.add_heading("Speaker Utterance Count", level=1)
    add_report_table(document, [("Speaker", "Utterances"), *speaker_summary])

    speech_minutes = round(speech_s / 60.0, 3)
    silence_minutes = round(silence_s / 60.0, 3)
    document.add_heading("Speech vs Silence Distribution", level=1)
    add_report_table(document, [
        ("Category", "Duration (minutes)"),
        ("Speech", speech_minutes),
        ("Silence", silence_minutes),
    ])
    add_bar_chart(document, ["Speech", "Silence"], [speech_minutes, silence_minutes], "Duration (minutes)")

    density_rows = compute_timeline_density(utterance_rows, audio_duration_s, interval_sec=300)
    document.add_heading("Timeline Density (5-minute intervals)", level=1)
    add_report_table(document, [("Interval (min)", "Utterances"), *density_rows])
    add_bar_chart(document, [label for label, _ in density_rows],
                  [count for _, count in density_rows], "Utterance count")

    document.add_heading("Top 20 Keywords (Frequency)", level=1)
    keyword_table = document.add_table(rows=1, cols=3)
    keyword_table.style = "Light Shading Accent 1"
    for cell, heading in zip(keyword_table.rows[0].cells, ("Rank", "Keyword", "Frequency")):
        cell.text = heading
    for rank, (keyword, count) in enumerate(Counter(tokens).most_common(20), start=1):
        cells = keyword_table.add_row().cells
        cells[0].text = str(rank)
        cells[1].text = keyword
        cells[2].text = str(count)

    document.add_paragraph(
        "Automated draft generated by RedScribe v"
        f"{APP_VERSION}. Verify the wording, timestamps and speaker labels "
        "against the original recording before use."
    )
    document.add_page_break()
    document.add_heading("Transcript", level=1)

    for row in group_consecutive_speaker_turns(utterance_rows):
        paragraph = document.add_paragraph()
        heading = (
            f"[{sec_to_hms(row['start_s'])}–{sec_to_hms(row['end_s'])}] "
            f"{row.get('speaker', 'UNKNOWN')}: "
        )
        paragraph.add_run(heading).bold = True
        paragraph.add_run(row["text"])

    document.save(docx_path)


# =========================
# MAIN APP
# =========================
class RedScribeApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        families = {family.casefold(): family for family in tkfont.families(root)}
        self.ui_font = next((families[name] for name in
                             ("segoe ui", "sf pro text", "helvetica neue", "dejavu sans", "helvetica")
                             if name in families), tkfont.nametofont("TkDefaultFont").actual("family"))
        window_width = max(680, min(1280, self.root.winfo_screenwidth() - 80))
        window_height = max(560, min(760, self.root.winfo_screenheight() - 100))
        self.root.geometry(f"{window_width}x{window_height}")
        self.root.minsize(min(900, window_width), min(580, window_height))

        self.project = tk.StringVar()
        self.researcher = tk.StringVar()
        self.label = tk.StringVar()
        self.period = tk.StringVar(value=time.strftime("%Y-%m"))
        self.audio_path = tk.StringVar()
        self.transcription_language = tk.StringVar(value="Auto detect")
        self.whisper_model = tk.StringVar(value=load_model_preference())

        self.diarization_enabled = tk.BooleanVar(value=True)
        self.hf_token = tk.StringVar()
        self.token_status = tk.StringVar(value="Token status: not checked")
        self.token_summary = tk.StringVar(value="Checking token...")
        self.token_settings_window = None
        self.speaker_count = tk.StringVar()
        self.diarization_summary = tk.StringVar()
        self.file_summary = tk.StringVar(value="No file selected")
        self.study_details_open = False

        self.base_output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
        self.last_output_folder = None
        self.progress_var = tk.DoubleVar(value=0.0)

        self.actual_whisper_device = "unknown"
        self.actual_whisper_compute_type = "unknown"
        self.stop_event = threading.Event()
        self.run_lock = threading.Lock()
        self.run_phase = "idle"

        self.build_ui()
        self.hf_token.trace_add("write", self.token_entry_changed)
        self.audio_path.trace_add("write", self.update_file_summary)
        self.diarization_enabled.trace_add("write", self.update_diarization_summary)
        self.speaker_count.trace_add("write", self.update_diarization_summary)
        self.update_diarization_summary()
        self.root.after(100, self.check_hf_token)

    def build_ui(self):
        self.colours = {
            "background": "#F7F4F6", "surface": "#FFFFFF", "border": "#E4DDE2",
            "text": "#202332", "muted": "#667085", "accent": "#8E1235",
        }
        c = self.colours
        self.root.configure(bg=c["background"])
        self.root.option_add("*Font", (self.ui_font, 10))
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure(".", font=(self.ui_font, 10), background="white", foreground=c["text"])
        style.configure("TButton", padding=(10, 7))
        style.configure("TEntry", padding=5)
        style.configure("TLabelframe", background="white", bordercolor=c["border"])
        style.configure("TLabelframe.Label", background="white", foreground=c["text"])
        style.map("TCheckbutton", background=[("active", "white")])
        style.configure("RedScribe.TButton", font=(self.ui_font, 10), padding=(12, 8),
                        background="#FFFFFF", foreground=c["text"], bordercolor=c["border"])
        style.map("RedScribe.TButton", background=[("active", "#F8ECF0")],
                  foreground=[("disabled", "#9895A0")])
        style.configure("Primary.RedScribe.TButton", background=c["accent"], foreground="white")
        style.map("Primary.RedScribe.TButton", background=[("disabled", "#E5E2E6"), ("active", "#71102A")],
                  foreground=[("disabled", "#9895A0"), ("!disabled", "white")])
        style.configure("Stop.RedScribe.TButton", foreground="#B42318", background="white")
        style.map("Stop.RedScribe.TButton", foreground=[("disabled", "#9895A0"), ("!disabled", "#B42318")])
        style.configure("RedScribe.TCombobox", padding=4, fieldbackground="white")
        style.map("RedScribe.TCombobox", fieldbackground=[("readonly", "white")], background=[("readonly", "white")])
        style.configure("RedScribe.TEntry", padding=6, fieldbackground="white")
        style.configure("RedScribe.Horizontal.TProgressbar", background=c["accent"],
                        troughcolor="#E8E3E8", bordercolor="#E8E3E8", thickness=7)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = tk.Frame(self.root, bg=c["surface"], padx=20, pady=14)
        header.grid(row=0, column=0, sticky="ew")
        mark = tk.Canvas(header, width=44, height=40, bg="white", highlightthickness=0)
        mark.pack(side="left", padx=(0, 12))
        for i, height in enumerate((10, 22, 34, 24, 14)):
            mark.create_line(5 + i * 8, 20 - height / 2, 5 + i * 8, 20 + height / 2,
                             width=5, fill=c["accent"], capstyle="round")
        brand = tk.Frame(header, bg="white")
        brand.pack(side="left")
        tk.Label(brand, text=f"RedScribe  v{APP_VERSION}", font=(self.ui_font, 21, "bold"),
                 bg="white", fg=c["accent"]).pack(anchor="w")
        tk.Label(brand, text="Research Speech Transcription System", bg="white", fg=c["muted"]).pack(anchor="w")
        ttk.Button(header, text="Settings", style="RedScribe.TButton",
                   command=self.open_token_settings).pack(side="right")
        tk.Label(header, text="Audio processed locally", bg="#EDF8EE", fg="#24623B",
                 padx=10, pady=7).pack(side="right", padx=14)

        workspace = tk.Frame(self.root, bg=c["background"])
        workspace.grid(row=1, column=0, sticky="nsew", padx=16, pady=16)
        workspace.rowconfigure(0, weight=1)
        workspace.columnconfigure(1, weight=1)
        sidebar = tk.Frame(workspace, bg=c["background"])
        sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 16))
        sidebar.rowconfigure(0, weight=1)
        # Scroll only the settings column: actions and transcript stay visible.
        self.sidebar_canvas = tk.Canvas(sidebar, width=300, bg=c["background"], highlightthickness=0)
        self.sidebar_canvas.grid(row=0, column=0, sticky="ns")
        scroll = ttk.Scrollbar(sidebar, orient="vertical", command=self.sidebar_canvas.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.sidebar_canvas.configure(yscrollcommand=scroll.set)
        self.sidebar_content = tk.Frame(self.sidebar_canvas, bg=c["background"])
        sidebar_window = self.sidebar_canvas.create_window((0, 0), window=self.sidebar_content, anchor="nw")
        self.sidebar_content.bind("<Configure>", lambda _event: self.sidebar_canvas.configure(
            scrollregion=self.sidebar_canvas.bbox("all")))
        self.sidebar_canvas.bind("<Configure>", lambda event: self.sidebar_canvas.itemconfigure(
            sidebar_window, width=event.width))
        self.root.bind("<MouseWheel>", self.scroll_sidebar, add="+")
        self.root.bind("<Button-4>", self.scroll_sidebar, add="+")
        self.root.bind("<Button-5>", self.scroll_sidebar, add="+")

        def card(title):
            outer = tk.Frame(self.sidebar_content, bg="white", highlightbackground=c["border"], highlightthickness=1)
            outer.pack(fill="x", pady=(0, 10))
            tk.Label(outer, text=title, bg="white", fg=c["text"], font=(self.ui_font, 12, "bold"),
                     padx=14, pady=8, anchor="w").pack(fill="x")
            tk.Frame(outer, bg=c["border"], height=1).pack(fill="x")
            inside = tk.Frame(outer, bg="white", padx=14, pady=8)
            inside.pack(fill="x")
            return inside

        audio = card("Audio file")
        tk.Label(audio, textvariable=self.file_summary, bg="white", fg=c["text"],
                 font=(self.ui_font, 10, "bold"), wraplength=264, justify="left").pack(anchor="w", pady=(0, 8))
        ttk.Button(audio, text="Browse file", style="Primary.RedScribe.TButton", command=self.browse_file).pack(fill="x")

        transcription = card("Transcription")
        tk.Label(transcription, text="Language", bg="white", fg=c["text"]).pack(anchor="w", pady=(0, 5))
        ttk.Combobox(transcription, textvariable=self.transcription_language, values=list(TRANSCRIPTION_LANGUAGES),
                     state="readonly", style="RedScribe.TCombobox", width=20).pack(fill="x", pady=(0, 8))
        tk.Label(transcription, text="Whisper model", bg="white", fg=c["text"]).pack(anchor="w", pady=(0, 5))
        model_choice = ttk.Combobox(transcription, textvariable=self.whisper_model, values=WHISPER_MODELS,
                                    state="readonly", style="RedScribe.TCombobox", width=20)
        model_choice.pack(fill="x")
        model_choice.bind("<<ComboboxSelected>>", self.save_selected_model)

        speakers = card("Speakers")
        self.diarization_badge = tk.Label(speakers, textvariable=self.diarization_summary, bg="white", fg="#24623B",
                                         font=(self.ui_font, 10, "bold"), anchor="w", wraplength=264)
        self.diarization_badge.pack(fill="x", pady=(0, 8))
        self.token_badge = tk.Label(speakers, textvariable=self.token_summary, bg="white", fg=c["muted"], anchor="w", wraplength=264)
        self.token_badge.pack(fill="x", pady=(0, 8))
        ttk.Button(speakers, text="Diarisation settings", style="RedScribe.TButton", command=self.open_token_settings).pack(fill="x")

        study = tk.Frame(self.sidebar_content, bg="white", highlightbackground=c["border"], highlightthickness=1)
        study.pack(fill="x", pady=(0, 12))
        self.study_toggle = ttk.Button(study, text="Study details  +", style="RedScribe.TButton", command=self.toggle_study_details)
        self.study_toggle.pack(fill="x")
        self.study_fields = tk.Frame(study, bg="white", padx=14, pady=8)
        for label, variable in (("Project / Study name", self.project), ("Researcher / Initials", self.researcher),
                                ("Interview / Audio label", self.label)):
            tk.Label(self.study_fields, text=label, bg="white", fg=c["text"]).pack(anchor="w", pady=(0, 4))
            ttk.Entry(self.study_fields, textvariable=variable, width=20, style="RedScribe.TEntry").pack(fill="x", pady=(0, 10))
        tk.Label(self.study_fields, text="Month / Period (YYYY-MM)", bg="white", fg=c["text"]).pack(anchor="w", pady=(0, 4))
        period_row = tk.Frame(self.study_fields, bg="white")
        period_row.pack(fill="x")
        ttk.Entry(period_row, textvariable=self.period, width=12, style="RedScribe.TEntry").pack(side="left", fill="x", expand=True)
        ttk.Button(period_row, text="Pick...", style="RedScribe.TButton", command=self.pick_period).pack(side="left", padx=(6, 0))

        transcript = tk.Frame(workspace, bg="white", highlightbackground=c["border"], highlightthickness=1)
        transcript.grid(row=0, column=1, sticky="nsew")
        transcript.rowconfigure(2, weight=1)
        transcript.columnconfigure(0, weight=1)
        transcript_header = tk.Frame(transcript, bg="white", padx=18, pady=14)
        transcript_header.grid(row=0, column=0, sticky="ew")
        tk.Label(transcript_header, text="Live transcript", bg="white", fg=c["text"], font=(self.ui_font, 19, "bold")).pack(anchor="w")
        tk.Label(transcript_header, textvariable=self.file_summary, bg="white", fg=c["muted"], anchor="w").pack(fill="x", pady=(3, 0))
        self.diarization_activity = tk.StringVar(value="")
        self.diarization_timer = None
        self.diarization_started = None
        self.activity_label = tk.Label(transcript, textvariable=self.diarization_activity, bg="#FCF4F7", fg=c["accent"],
                                      anchor="w", justify="left", wraplength=600, padx=18, pady=8)
        # Reserve this row for live diarisation activity; hide when idle.
        self.activity_label.grid(row=1, column=0, sticky="ew")
        self.activity_label.grid_remove()
        transcript.bind("<Configure>", lambda event: self.activity_label.configure(wraplength=max(180, event.width - 40)))
        self.live_box = scrolledtext.ScrolledText(transcript, height=8, width=30, state="disabled", wrap="word",
                                                  bg="white", fg=c["text"], relief="flat", borderwidth=0,
                                                  font=(self.ui_font, 11), padx=18, pady=12, spacing3=10,
                                                  selectbackground="#F2CED9", selectforeground=c["text"])
        self.live_box.grid(row=2, column=0, sticky="nsew", padx=2, pady=(0, 10))
        self.live_box.tag_configure("ts", foreground=c["muted"], font=(self.ui_font, 9))
        self.live_box.tag_configure("speaker", foreground=c["accent"], font=(self.ui_font, 10, "bold"))
        self.live_box.tag_configure("txt", foreground=c["text"])
        self.live_box.tag_configure("info", foreground="#52657D")
        self.live_box.tag_configure("warn", foreground="#B42318")
        self.speaker_tags = {}
        self.log_info("Your transcript will appear here.\nSelect an audio file, then choose Start transcription.")

        bottom = tk.Frame(self.root, bg="white", padx=16, pady=12, highlightbackground=c["border"], highlightthickness=1)
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)
        self.status = tk.StringVar(value="Ready")
        self.status_label = tk.Label(bottom, textvariable=self.status, bg="white", fg=c["text"], anchor="w", justify="left", wraplength=600)
        self.status_label.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        bottom.bind("<Configure>", lambda event: self.status_label.configure(wraplength=max(180, event.width - 48)))
        self.progress = ttk.Progressbar(bottom, orient="horizontal", mode="determinate", maximum=100,
                                       variable=self.progress_var, length=160, style="RedScribe.Horizontal.TProgressbar")
        self.progress.grid(row=1, column=0, sticky="ew", padx=(0, 18))
        controls = tk.Frame(bottom, bg="white")
        controls.grid(row=1, column=1, sticky="e")
        self.open_btn = ttk.Button(controls, text="Open output folder", command=self.open_output_folder, style="RedScribe.TButton")
        self.open_btn.pack(side="left", padx=(0, 8))
        self.stop_btn = ttk.Button(controls, text="Stop", command=self.stop, state="disabled", style="Stop.RedScribe.TButton")
        self.stop_btn.pack(side="left", padx=(0, 8))
        self.start_btn = ttk.Button(controls, text="Start transcription", command=self.start, style="Primary.RedScribe.TButton")
        self.start_btn.pack(side="left")
        footer = tk.Frame(bottom, bg="white")
        footer.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        support = tk.Label(footer, text="RedScribe | CRDV2026W02110 | Authors & support", bg="white", fg=c["muted"],
                           font=(self.ui_font, 9), cursor="hand2")
        support.pack(side="left")
        support.bind("<Button-1>", self.show_support)
        tk.Label(footer, text="Automated draft - verify against the recording", bg="white", fg=c["muted"], font=(self.ui_font, 9)).pack(side="right")

    def toggle_study_details(self):
        self.study_details_open = not self.study_details_open
        if self.study_details_open:
            self.study_fields.pack(fill="x")
        else:
            self.study_fields.pack_forget()
        self.study_toggle.configure(text="Study details  -" if self.study_details_open else "Study details  +")

    def scroll_sidebar(self, event):
        if not str(event.widget).startswith(str(self.sidebar_canvas)):
            return
        if self.sidebar_content.winfo_height() <= self.sidebar_canvas.winfo_height():
            return
        if getattr(event, "num", None) in (4, 5):
            units = -1 if event.num == 4 else 1
        else:
            delta = getattr(event, "delta", 0)
            if not delta:
                return
            units = -max(1, abs(delta) // 120) if delta > 0 else max(1, abs(delta) // 120)
        self.sidebar_canvas.yview_scroll(units, "units")
        return "break"

    def update_file_summary(self, *_args):
        path = self.audio_path.get().strip()
        self.file_summary.set(os.path.basename(path) if path else "No file selected")

    def update_diarization_summary(self, *_args):
        enabled = self.diarization_enabled.get()
        count = self.speaker_count.get().strip()
        detail = f"{count} expected speakers" if count else "Automatic speaker count"
        self.diarization_summary.set(f"ON - {detail}" if enabled else "OFF - Transcription only")
        self.diarization_badge.configure(fg="#24623B" if enabled else "#667085")

    def begin_diarization_activity(self):
        """Main-thread-only display lifecycle; keep ticking during model calls."""
        self.end_diarization_activity()
        self.activity_label.grid()
        self.diarization_started = time.monotonic()
        self.diarization_stage = "Loading diarisation model..."
        self.diarization_fraction = None
        self.diarization_last_logged_stage = None
        self.diarization_tick = 0
        self.tick_diarization_activity()

    def tick_diarization_activity(self):
        if self.diarization_started is None:
            return
        elapsed = sec_to_hms(time.monotonic() - self.diarization_started)
        indicator = ("·", "··", "···")[self.diarization_tick % 3]
        self.diarization_tick += 1
        detail = self.diarization_stage
        if self.diarization_fraction is not None:
            completed, total = self.diarization_fraction
            detail += f" {completed / total:.0%} of this stage"
        if self.stop_event.is_set():
            detail = "Stopping after the current processing step..."
        display = f"{indicator} {detail} | Elapsed: {elapsed}"
        self.diarization_activity.set(display)
        self.status.set(display)
        self.diarization_timer = self.root.after(500, self.tick_diarization_activity)

    def update_diarization_activity(self, stage, completed=None, total=None):
        if self.diarization_started is None:
            return
        self.diarization_stage = stage
        self.diarization_fraction = (
            (max(0, min(completed, total)), total)
            if total is not None and total > 0 and completed is not None else None
        )
        if stage != self.diarization_last_logged_stage:
            self.log_info(stage)
            self.diarization_last_logged_stage = stage

    def end_diarization_activity(self):
        if self.diarization_timer is not None:
            self.root.after_cancel(self.diarization_timer)
        self.diarization_timer = None
        self.diarization_started = None
        self.diarization_activity.set("")
        self.activity_label.grid_remove()

    def log_diarization_summary(self, turns):
        speakers = {turn["speaker"] for turn in turns}
        self.log_info(f"Diarisation complete — {len(speakers)} speaker label(s) detected.")
        # Bound the preview so long recordings do not flood the UI event queue.
        for turn in turns[:20]:
            self.log_info(f"{sec_to_hms(turn['start'])}–{sec_to_hms(turn['end'])} · {turn['speaker']}")
        if len(turns) > 20:
            self.log_info(f"Showing the first 20 of {len(turns)} speaker turns.")
        self.log_info("Starting transcription...")

    def show_support(self, _event=None):
        messagebox.showinfo(
            "About RedScribe",
            f"RedScribe v{APP_VERSION}\n"
            "Research Speech Transcription System\n\n"
            "Authors:\n"
            "Mad Sapri bin Tumiran\n"
            "Mohd Shahezwan bin Abd Wahab\n"
            "Janattul Ain binti Jamal\n"
            "Nursyuhadah binti Othman\n\n"
            "Malaysia copyright notification: CRDV2026W02110\n\n"
            "Support:\n"
            "saprimad@moh.gov.my"
        )

    def open_token_settings(self):
        """Keep credential controls out of the transcription workspace."""
        if self.token_settings_window is not None and self.token_settings_window.winfo_exists():
            self.token_settings_window.lift()
            self.token_settings_window.focus_set()
            return

        win = tk.Toplevel(self.root)
        self.token_settings_window = win
        win.title("RedScribe Settings - Diarisation")
        win.transient(self.root)
        win.resizable(True, True)
        available_height = max(360, self.root.winfo_screenheight() - 100)
        settings_canvas = tk.Canvas(win, highlightthickness=0, width=520)
        settings_scroll = ttk.Scrollbar(win, orient="vertical", command=settings_canvas.yview)
        settings_scroll.pack(side="right", fill="y")
        settings_canvas.pack(side="left", fill="both", expand=True)
        settings_canvas.configure(yscrollcommand=settings_scroll.set)
        panel = ttk.Frame(settings_canvas, padding=20)
        settings_window = settings_canvas.create_window((0, 0), window=panel, anchor="nw")
        panel.bind("<Configure>", lambda _event: settings_canvas.configure(scrollregion=settings_canvas.bbox("all")))
        settings_canvas.bind("<Configure>", lambda event: settings_canvas.itemconfigure(settings_window, width=event.width))
        ttk.Label(panel, text="Diarisation Settings", font=(self.ui_font, 15, "bold")).pack(anchor="w")
        ttk.Label(panel, text="Speaker detection and Hugging Face access", wraplength=450, foreground="#52606D").pack(anchor="w", pady=(3, 12))
        speaker_options = ttk.LabelFrame(panel, text="Speakers", padding=10)
        speaker_options.pack(fill="x", pady=(0, 12))
        ttk.Checkbutton(speaker_options, text="Enable speaker diarisation",
                        variable=self.diarization_enabled).pack(anchor="w")
        count_row = ttk.Frame(speaker_options)
        count_row.pack(fill="x", pady=(8, 4))
        ttk.Label(count_row, text="Expected speakers").pack(side="left")
        ttk.Entry(count_row, textvariable=self.speaker_count, width=8).pack(side="right")
        ttk.Label(speaker_options, text="Diarisation is on by default. Leave the count blank for automatic detection. Changes apply to the next run.",
                  wraplength=450, foreground="#52606D").pack(anchor="w")

        status_card = ttk.LabelFrame(panel, text="Current token", padding=12)
        status_card.pack(fill="x", pady=(0, 14))
        ttk.Label(status_card, textvariable=self.token_status, wraplength=450,
                  justify="left").pack(fill="x")
        ttk.Label(status_card, text="Availability only; model access has not been tested.",
                  foreground="#52606D", wraplength=450).pack(anchor="w", pady=(8, 0))

        ttk.Label(panel, text="Enter or replace token", font=(self.ui_font, 10, "bold")).pack(anchor="w")
        entry_row = ttk.Frame(panel)
        entry_row.pack(fill="x", pady=(6, 8))
        self.token_entry = ttk.Entry(entry_row, textvariable=self.hf_token, show="*", width=24)
        self.token_entry.pack(side="left", fill="x", expand=True)
        self.show_token_btn = ttk.Button(entry_row, text="Show", width=6, command=self.toggle_token_visibility)
        self.show_token_btn.pack(side="left", padx=(8, 0))
        ttk.Label(panel, text="Leave blank to use a saved token. An unsaved entry is used only for this app session.",
                  foreground="#52606D", wraplength=480, justify="left").pack(anchor="w")

        actions = ttk.Frame(panel)
        actions.pack(fill="x", pady=(14, 16))
        for label, command in (("Save Token", self.save_hf_token),
                               ("Remove Saved", self.remove_hf_token),
                               ("Check Token", self.check_hf_token)):
            ttk.Button(actions, text=label, command=command).pack(side="left", padx=(0, 8))

        ttk.Separator(panel).pack(fill="x")
        ttk.Label(panel, text="Saved tokens use this computer's system credential store. Removing a saved token does not revoke it on Hugging Face or sign out a separate login.",
                  foreground="#52606D", wraplength=480, justify="left").pack(anchor="w", pady=(12, 14))
        ttk.Button(panel, text="Done", command=self.close_token_settings).pack(anchor="e")
        win.protocol("WM_DELETE_WINDOW", self.close_token_settings)
        win.bind("<Escape>", lambda _event: self.close_token_settings())

        def scroll_settings(event):
            if panel.winfo_reqheight() <= settings_canvas.winfo_height():
                return
            if getattr(event, "num", None) in (4, 5):
                units = -1 if event.num == 4 else 1
            else:
                delta = getattr(event, "delta", 0)
                if not delta:
                    return
                units = -max(1, abs(delta) // 120) if delta > 0 else max(1, abs(delta) // 120)
            settings_canvas.yview_scroll(units, "units")
            return "break"

        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            win.bind(sequence, scroll_settings)
        win.update_idletasks()
        width = min(560, self.root.winfo_screenwidth() - 60)
        height = min(panel.winfo_reqheight() + 4, available_height)
        win.minsize(min(480, width), min(380, height))
        x = max(0, min(self.root.winfo_screenwidth() - width,
                      self.root.winfo_rootx() + (self.root.winfo_width() - width) // 2))
        y = max(0, min(self.root.winfo_screenheight() - height,
                      self.root.winfo_rooty() + (self.root.winfo_height() - height) // 2))
        win.geometry(f"{width}x{height}+{x}+{y}")
        win.grab_set()
        self.token_entry.focus_set()
        self.check_hf_token()

    def close_token_settings(self):
        if self.token_settings_window is not None:
            self.token_entry.configure(show="*")
            self.token_settings_window.grab_release()
            self.token_settings_window.destroy()
            self.token_settings_window = None

    def token_entry_changed(self, *_args):
        if self.hf_token.get().strip():
            self.token_status.set("Token: session entry (click Save Token to remember)")
            self.token_summary.set("Session token (not saved)")
        else:
            self.check_hf_token()

    def toggle_token_visibility(self):
        hidden = bool(self.token_entry.cget("show"))
        self.token_entry.configure(show="" if hidden else "*")
        self.show_token_btn.configure(text="Hide" if hidden else "Show")

    def check_hf_token(self):
        """Local availability only; no network validation or secret display."""
        selection = resolve_token(self.hf_token.get())
        status = f"Token: {selection.source}."
        if selection.warning:
            status += f" {selection.warning}"
        self.token_status.set(status)
        if not selection.token:
            summary = "Token not configured"
        elif selection.source == "saved in system credential store":
            summary = "Token saved"
        elif selection.source.startswith("entered in app"):
            summary = "Session token"
        else:
            summary = "Token available"
        self.token_summary.set(summary)
        if hasattr(self, "token_badge"):
            self.token_badge.configure(fg="#24623B" if selection.token else "#667085")

    def save_hf_token(self):
        try:
            save_token(self.hf_token.get())
        except TokenStoreError as exc:
            messagebox.showwarning("Save Token", str(exc))
            return
        self.hf_token.set("")
        self.token_entry.configure(show="*")
        self.show_token_btn.configure(text="Show")
        self.check_hf_token()

    def remove_hf_token(self):
        try:
            remove_saved_token()
        except TokenStoreError as exc:
            messagebox.showwarning("Remove Saved Token", str(exc))
            return
        # Only remove RedScribe's keyring entry; preserve any typed session token.
        self.check_hf_token()
        messagebox.showinfo("Remove Saved Token",
                            "RedScribe's saved token has been removed.\n\n"
                            "Any session token, environment token or Hugging Face login remains available. "
                            "This does not revoke the token on Hugging Face.")

    def save_selected_model(self, _event=None):
        try:
            save_model_preference(self.whisper_model.get())
        except OSError as exc:
            messagebox.showwarning("Whisper Model", f"The model choice could not be saved for next time.\n\n{exc}")

    def pick_period(self):
        win = tk.Toplevel(self.root)
        win.title("Select Month / Period")
        win.resizable(False, False)
        win.grab_set()

        cur = (self.period.get() or time.strftime("%Y-%m")).strip()
        try:
            y0, m0 = cur.split("-")
            y0 = int(y0)
            m0 = int(m0)
        except Exception:
            y0 = int(time.strftime("%Y"))
            m0 = int(time.strftime("%m"))

        year_var = tk.IntVar(value=y0)
        month_var = tk.IntVar(value=m0)

        tk.Label(win, text="Year").grid(row=0, column=0, padx=10, pady=8, sticky="w")
        tk.Spinbox(win, from_=2000, to=2100, textvariable=year_var, width=8).grid(row=0, column=1, padx=10, pady=8)

        tk.Label(win, text="Month").grid(row=1, column=0, padx=10, pady=8, sticky="w")
        tk.Spinbox(win, from_=1, to=12, textvariable=month_var, width=8).grid(row=1, column=1, padx=10, pady=8)

        def apply():
            y = year_var.get()
            m = month_var.get()
            self.period.set(f"{y:04d}-{m:02d}")
            win.destroy()

        btns = tk.Frame(win)
        btns.grid(row=2, column=0, columnspan=2, pady=10)
        tk.Button(btns, text="Cancel", command=win.destroy).pack(side="right", padx=6)
        tk.Button(btns, text="Apply", command=apply).pack(side="right", padx=6)

    def browse_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Audio/video files", "*.mp3 *.wav *.m4a *.mp4")]
        )
        if path:
            self.audio_path.set(path)

    def open_output_folder(self):
        if self.last_output_folder and os.path.isdir(self.last_output_folder):
            open_folder(self.last_output_folder)
        else:
            ensure_dir(self.base_output_dir)
            open_folder(self.base_output_dir)

    def log_live_segment(self, ts: str, speaker: str, text: str):
        if speaker not in self.speaker_tags:
            tag = f"speaker_{len(self.speaker_tags)}"
            palette = ("#8E1235", "#2458A6", "#24735B", "#8C4E12")
            self.live_box.tag_configure(tag, foreground=palette[len(self.speaker_tags) % len(palette)],
                                        font=(self.ui_font, 10, "bold"))
            self.speaker_tags[speaker] = tag
        self.live_box.configure(state="normal")
        self.live_box.insert("end", f"{ts}   ", ("ts",))
        self.live_box.insert("end", f"{speaker}\n", (self.speaker_tags[speaker],))
        self.live_box.insert("end", f"{text}\n\n", ("txt",))
        self.live_box.see("end")
        self.live_box.configure(state="disabled")

    def log_warning(self, text: str):
        self.live_box.configure(state="normal")
        self.live_box.insert("end", f"{text}\n", ("warn",))
        self.live_box.see("end")
        self.live_box.configure(state="disabled")

    def log_info(self, text: str):
        self.live_box.configure(state="normal")
        self.live_box.insert("end", f"{text}\n", ("info",))
        self.live_box.see("end")
        self.live_box.configure(state="disabled")

    def stop(self):
        with self.run_lock:
            if self.run_phase != "processing":
                return
            self.stop_event.set()
        self.stop_btn.config(state="disabled")
        self.status.set("Stopping after the current processing step...")

    def check_stop(self):
        if self.stop_event.is_set():
            raise TranscriptionCancelled()

    def begin_saving(self):
        with self.run_lock:
            self.check_stop()
            self.run_phase = "saving"
        self.root.after(0, lambda: self.stop_btn.config(state="disabled"))
        self.root.after(0, self.status.set, "Saving reports...")

    def finish_run(self, cancelled: bool):
        self.end_diarization_activity()
        with self.run_lock:
            self.run_phase = "idle"
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        if cancelled:
            self.progress_var.set(0.0)
            self.status.set("Stopped; no reports were saved for this run")
            self.log_warning("Stopped by user. No Word or Excel report was saved for this run.")

    def start(self):
        inputs = {
            "audio_path": self.audio_path.get().strip(),
            "project": self.project.get().strip(),
            "researcher": self.researcher.get().strip(),
            "label": self.label.get().strip(),
            "period": self.period.get().strip(),
            "diarization_enabled": bool(self.diarization_enabled.get()),
            "hf_token": self.hf_token.get().strip(),
            "speaker_count": self.speaker_count.get().strip(),
            "language": TRANSCRIPTION_LANGUAGES[self.transcription_language.get()],
            "whisper_model": self.whisper_model.get(),
        }

        if not inputs["audio_path"]:
            messagebox.showwarning("Missing file", "Please select an audio file.")
            return

        if not os.path.isfile(inputs["audio_path"]):
            messagebox.showwarning("File not found", "The selected audio file no longer exists.")
            return

        if inputs["diarization_enabled"]:
            inputs["hf_token"] = resolve_token(inputs["hf_token"]).token

        with self.run_lock:
            if self.run_phase != "idle":
                return
            self.stop_event.clear()
            self.run_phase = "processing"

        self.live_box.configure(state="normal")
        self.live_box.delete("1.0", "end")
        self.live_box.configure(state="disabled")

        self.speaker_tags.clear()
        self.progress_var.set(0.0)
        self.status.set(f"Loading {inputs['whisper_model']} model...")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

        threading.Thread(target=self.run_whisper, args=(inputs,), daemon=True).start()

    def run_whisper(self, inputs: dict):
        cancelled = False
        try:
            self._run_whisper(inputs)
        except TranscriptionCancelled:
            cancelled = True
        except Exception:
            error_text = traceback.format_exc()
            try:
                with open(os.path.join(self.base_output_dir, "redscribe_error.log"), "a", encoding="utf-8") as log:
                    log.write(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')}\n{error_text}\n")
            except OSError:
                pass
            self.root.after(0, self.status.set, "Transcription failed")
            self.root.after(0, lambda: self.start_btn.config(state="normal"))
            self.root.after(0, lambda: messagebox.showerror(
                "RedScribe Error", "The run stopped unexpectedly. See output/redscribe_error.log for details."))
        finally:
            release_gpu_cache()
            self.root.after(0, self.finish_run, cancelled)

    def _run_whisper(self, inputs: dict):
        start_clock = time.time()

        audio_path = inputs["audio_path"]
        audio_base = os.path.splitext(os.path.basename(audio_path))[0]

        period = inputs["period"] or time.strftime("%Y-%m")
        if not re.match(r"^\d{4}-\d{2}$", period):
            period = time.strftime("%Y-%m")

        out_folder = os.path.join(self.base_output_dir, period)
        ensure_dir(out_folder)
        self.last_output_folder = out_folder

        filename_base = build_output_name(
            project=inputs["project"],
            period=period,
            label=inputs["label"],
            researcher=inputs["researcher"],
            audio_base=audio_base
        )
        xlsx_path, docx_path = available_output_paths(out_folder, filename_base)

        try:
            model, actual_device, actual_compute_type = create_whisper_model(inputs["whisper_model"])
            self.check_stop()
            self.actual_whisper_device = actual_device
            self.actual_whisper_compute_type = actual_compute_type
        except TranscriptionCancelled:
            raise
        except Exception as e:
            self.check_stop()
            error_text = str(e)
            self.root.after(
                0,
                lambda error_text=error_text: messagebox.showerror("Whisper Error", f"The Whisper model could not be loaded.\n\n{error_text}")
            )
            self.root.after(0, self.status.set, "Failed to load model")
            self.root.after(0, lambda: self.start_btn.config(state="normal"))
            return

        diarization_enabled = inputs["diarization_enabled"]
        diarization_turns = []
        diarization_status = "Disabled"

        if diarization_enabled:
            self.root.after(0, self.begin_diarization_activity)

            def report_diarization(stage, completed=None, total=None):
                self.check_stop()
                self.root.after(0, self.update_diarization_activity, stage, completed, total)

            try:
                diarization_turns = run_diarization(
                    audio_path=audio_path,
                    hf_token=inputs["hf_token"],
                    preferred_device=actual_device,
                    speaker_count_text=inputs["speaker_count"],
                    progress_callback=report_diarization
                )
                speakers = sorted({t["speaker"] for t in diarization_turns})
                self.check_stop()
                diarization_status = f"Completed ({len(speakers)} speaker label(s))"
                self.root.after(0, self.log_diarization_summary, diarization_turns)
            except TranscriptionCancelled:
                raise
            except Exception as e:
                self.check_stop()
                diarization_status = f"Skipped / failed: {e}"
                self.root.after(
                    0,
                    self.log_warning,
                    "Speaker diarisation was skipped. Transcription will continue without speaker labels.\n"
                    f"Reason: {e}\n"
                )
                diarization_turns = []
            finally:
                self.root.after(0, self.end_diarization_activity)

        self.check_stop()

        self.root.after(
            0,
            self.status.set,
            f"Transcribing {inputs['whisper_model']} with {actual_device.upper()} ({actual_compute_type}) - 0% | ETA --:--"
        )

        try:
            segments, info = model.transcribe(
                audio_path,
                language=inputs.get("language"),
                task="transcribe",
                vad_filter=True,
                beam_size=5
            )
            self.check_stop()
            language_code = getattr(info, "language", None)
            if inputs.get("language") is None and language_code:
                language_name = {"cy": "Welsh", "ms": "Bahasa Melayu", "en": "English"}.get(
                    language_code, language_code
                )
                self.root.after(0, self.log_info, f"Auto detected language: {language_name} ({language_code})")
        except TranscriptionCancelled:
            raise
        except Exception as e:
            self.check_stop()
            error_text = str(e)
            self.root.after(
                0,
                lambda error_text=error_text: messagebox.showerror("Transcription Error", f"The audio could not be transcribed.\n\n{error_text}")
            )
            self.root.after(0, self.status.set, "Transcription failed")
            self.root.after(0, lambda: self.start_btn.config(state="normal"))
            return

        duration_s = float(getattr(info, "duration", 0.0)) or 0.0
        t0 = time.time()

        utterance_rows = []
        segment_ranges = []
        last_end = 0.0

        for seg in segments:
            self.check_stop()
            seg_text = (seg.text or "").strip()
            st = float(seg.start)
            en = float(seg.end)

            if en > st:
                segment_ranges.append((st, en))
                last_end = max(last_end, en)

            if seg_text:
                ts = sec_to_hms(st)
                segment_speaker = assign_speaker(st, en, diarization_turns)
                self.root.after(0, self.log_live_segment, ts, segment_speaker, seg_text)

                sents = split_sentences_universal(seg_text)
                for ust, uen, s in distribute_times(st, en, sents):
                    s_clean = (s or "").strip()
                    if s_clean:
                        utterance_speaker = assign_speaker(ust, uen, diarization_turns)
                        utterance_rows.append({
                            "speaker": utterance_speaker,
                            "start_s": ust,
                            "end_s": uen,
                            "text": s_clean
                        })

            if duration_s > 0:
                progress = min(100.0, (en / duration_s) * 100.0)
                elapsed = time.time() - t0

                if progress > 0.5:
                    total_est = elapsed * (100.0 / progress)
                    eta = max(0.0, total_est - elapsed)
                    eta_str = sec_to_mmss(eta)
                else:
                    eta_str = "--:--"

                self.root.after(0, self.progress_var.set, progress)
                self.root.after(
                    0,
                    self.status.set,
                    f"Transcribing {inputs['whisper_model']} with {actual_device.upper()} ({actual_compute_type}) - {progress:.0f}% | ETA {eta_str}"
                )

        self.begin_saving()
        audio_duration_s = float(getattr(info, "duration", last_end))
        elapsed_min = round((time.time() - start_clock) / 60, 2)

        meta_from_gui = {
            "project": inputs["project"],
            "researcher": inputs["researcher"],
            "label": inputs["label"],
            "period": period,
        }

        try:
            save_xlsx_with_early_report(
                xlsx_path=xlsx_path,
                utterance_rows=utterance_rows,
                segment_ranges=segment_ranges,
                audio_path=audio_path,
                audio_duration_s=audio_duration_s,
                processing_minutes=elapsed_min,
                detected_language=getattr(info, "language", None),
                meta_from_gui=meta_from_gui,
                actual_device=actual_device,
                actual_compute_type=actual_compute_type,
                whisper_model=inputs["whisper_model"],
                diarization_enabled=diarization_enabled,
                diarization_status=diarization_status,
                diarization_model=DIARIZATION_MODEL
            )
        except Exception as e:
            error_text = str(e)
            self.root.after(
                0,
                lambda error_text=error_text: messagebox.showerror("Excel Error", f"The Excel workbook could not be saved.\n\n{error_text}")
            )
            self.root.after(0, self.status.set, "Excel save failed")
            self.root.after(0, lambda: self.start_btn.config(state="normal"))
            return

        word_error = None
        try:
            save_docx_transcript(
                docx_path=docx_path,
                utterance_rows=utterance_rows,
                segment_ranges=segment_ranges,
                audio_path=audio_path,
                audio_duration_s=audio_duration_s,
                processing_minutes=elapsed_min,
                detected_language=getattr(info, "language", None),
                meta_from_gui=meta_from_gui,
                actual_device=actual_device,
                actual_compute_type=actual_compute_type,
                whisper_model=inputs["whisper_model"],
                diarization_enabled=diarization_enabled,
                diarization_status=diarization_status,
                diarization_model=DIARIZATION_MODEL
            )
        except Exception as exc:
            word_error = str(exc)

        def done_popup():
            self.progress_var.set(100.0)
            self.status.set(
                "Completed; Word export failed" if word_error
                else f"Completed - 100% | {actual_device.upper()} ({actual_compute_type})"
            )
            self.start_btn.config(state="normal")

            if word_error:
                messagebox.showwarning(
                    "Word Export Failed",
                    f"The transcription and Excel export were completed.\n\n"
                    f"Saved Excel:\n{xlsx_path}\n\n"
                    f"The Word file could not be saved:\n{word_error}"
                )
            else:
                messagebox.showinfo(
                    "Transcription Completed Successfully",
                    f"RedScribe completed transcription in {elapsed_min} minutes.\n\n"
                    f"Whisper device: {actual_device.upper()} ({actual_compute_type})\n"
                    f"Speaker diarisation: {diarization_status}\n\n"
                    "Review the transcript and speaker labels against the recording.\n\n"
                    f"Saved Excel:\n{xlsx_path}\n\n"
                    f"Saved Word:\n{docx_path}"
                )
            open_folder(out_folder)

        self.root.after(0, done_popup)


if __name__ == "__main__":
    root = tk.Tk()
    app = RedScribeApp(root)
    root.mainloop()
