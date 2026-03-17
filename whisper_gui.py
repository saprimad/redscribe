import os
import re
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from collections import Counter

import ollama
from faster_whisper import WhisperModel

from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.label import DataLabelList


# =========================
# CONFIG
# =========================
MODEL_SIZE = "small"
QWEN_MODEL = "qwen2.5:1.5b"
APP_TITLE = "RedScribe – Research Speech Transcription System"

WHISPER_DEVICE_PRIORITY = ["cuda", "cpu"]
WHISPER_COMPUTE_TYPE = {
    "cuda": "float16",
    "cpu": "int8"
}

LANGUAGE_MAP = {
    "Auto": None,
    "English": "en",
    "Malay": "ms"
}

# Request Ollama to use GPU.
# Note: actual behavior still depends on Ollama + model + available VRAM.
OLLAMA_OPTIONS = {
    "num_gpu": 999,
    "temperature": 0.2
}

# Optional environment hints for Ollama
os.environ.setdefault("OLLAMA_NUM_GPU", "999")


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


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def open_folder(path: str):
    try:
        os.startfile(path)
    except Exception:
        pass


def create_whisper_model():
    last_error = None
    for device in WHISPER_DEVICE_PRIORITY:
        compute_type = WHISPER_COMPUTE_TYPE.get(device, "int8")
        try:
            model = WhisperModel(MODEL_SIZE, device=device, compute_type=compute_type)
            return model, device, compute_type
        except Exception as e:
            last_error = e
    raise RuntimeError(f"Gagal load Whisper model pada semua device. Error terakhir: {last_error}")


def parse_qwen_output(raw_text: str) -> dict:
    text = (raw_text or "").strip()

    result = {
        "meaning": "",
        "code": "",
        "category": "",
        "sjt": "",
        "raw": text
    }

    patterns = {
        "meaning": r"Meaning:\s*(.*?)(?=\nCode:|\nCategory:|\nSJT:|$)",
        "code": r"Code:\s*(.*?)(?=\nMeaning:|\nCategory:|\nSJT:|$)",
        "category": r"Category:\s*(.*?)(?=\nMeaning:|\nCode:|\nSJT:|$)",
        "sjt": r"SJT:\s*(.*?)(?=\nMeaning:|\nCode:|\nCategory:|$)",
    }

    for key, pattern in patterns.items():
        m = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if m:
            result[key] = m.group(1).strip()

    return result


# =========================
# EXCEL WRITER
# =========================
def save_xlsx_with_reports(
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
    ai_rows: list[dict]
):
    wb = Workbook()

    ws1 = wb.active
    ws1.title = "Early_Report"

    ws1["A1"] = "Study & Processing Metadata"
    ws1["A1"].font = ws1["A1"].font.copy(bold=True)

    meta = [
        ("Application", "RedScribe – Research Speech Transcription System"),
        ("Project / Study", meta_from_gui.get("project", "")),
        ("Researcher", meta_from_gui.get("researcher", "")),
        ("Interview / Audio Label", meta_from_gui.get("label", "")),
        ("Processing Period", meta_from_gui.get("period", "")),
        ("Selected Language", meta_from_gui.get("selected_language", "Auto")),
        ("Audio File", os.path.basename(audio_path)),
        ("Audio Duration", sec_to_hms(audio_duration_s)),
        ("Language (Detected/Selected)", detected_language or meta_from_gui.get("selected_language", "Auto")),
        ("Whisper Model & Mode", f"{MODEL_SIZE} ({actual_device.upper()} | {actual_compute_type})"),
        ("Ollama Model", QWEN_MODEL),
        ("Ollama GPU Requested", "Yes (num_gpu=999)"),
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
    ]

    r2 = r + 3
    for k, v in summary:
        ws1[f"A{r2}"] = k
        ws1[f"B{r2}"] = v
        r2 += 1

    r3 = r2 + 2
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
    ws1.column_dimensions["C"].width = 18
    ws1.column_dimensions["D"].width = 16
    ws1.column_dimensions["E"].width = 16
    ws1.column_dimensions["F"].width = 16

    ws2 = wb.create_sheet("Transcription")
    headers = [
        "Utterance No.",
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
            sec_to_hms(rrow["start_s"]),
            sec_to_hms(rrow["end_s"]),
            rrow["text"],
            "",
            ""
        ])

    widths = [14, 20, 18, 70, 40, 25]
    for col_idx, w in enumerate(widths, start=1):
        ws2.column_dimensions[get_column_letter(col_idx)].width = w

    ws3 = wb.create_sheet("AI_Coding")
    ai_headers = [
        "Utterance No.",
        "Timestamp",
        "Transcript",
        "Meaning",
        "Code",
        "Category",
        "SJT",
        "Raw AI Output"
    ]
    ws3.append(ai_headers)

    for row in ai_rows:
        ws3.append([
            row.get("utterance_no", ""),
            row.get("timestamp", ""),
            row.get("transcript", ""),
            row.get("meaning", ""),
            row.get("code", ""),
            row.get("category", ""),
            row.get("sjt", ""),
            row.get("raw", "")
        ])

    ai_widths = [14, 14, 60, 40, 28, 22, 14, 60]
    for col_idx, w in enumerate(ai_widths, start=1):
        ws3.column_dimensions[get_column_letter(col_idx)].width = w

    wb.save(xlsx_path)


# =========================
# MAIN APP
# =========================
class RedScribeApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1320x820")

        self.project = tk.StringVar()
        self.researcher = tk.StringVar()
        self.label = tk.StringVar()
        self.period = tk.StringVar(value=time.strftime("%Y-%m"))
        self.audio_path = tk.StringVar()
        self.language_choice = tk.StringVar(value="English")

        self.base_output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
        self.last_output_folder = None
        self.progress_var = tk.DoubleVar(value=0.0)

        self.actual_whisper_device = "unknown"
        self.actual_whisper_compute_type = "unknown"

        self.ai_rows = []

        self.build_ui()
        self.load_default_prompt()

    def build_ui(self):
        top = tk.Frame(self.root)
        top.pack(fill="x", padx=10, pady=6)

        tk.Label(top, text="Project & File Information", font=("Segoe UI", 10, "bold")).pack(anchor="w")

        def row_entry(parent, label, var):
            fr = tk.Frame(parent)
            fr.pack(fill="x", pady=2)
            tk.Label(fr, text=label, width=24, anchor="w").pack(side="left")
            tk.Entry(fr, textvariable=var).pack(side="left", fill="x", expand=True)
            return fr

        row_entry(top, "Project / Study Name", self.project)
        row_entry(top, "Researcher Name / Initials", self.researcher)
        row_entry(top, "Interview / Audio Label", self.label)

        period_fr = tk.Frame(top)
        period_fr.pack(fill="x", pady=2)
        tk.Label(period_fr, text="Month / Period (YYYY-MM)", width=24, anchor="w").pack(side="left")
        tk.Entry(period_fr, textvariable=self.period, width=12).pack(side="left")
        tk.Button(period_fr, text="Pick…", command=self.pick_period).pack(side="left", padx=6)

        lang_fr = tk.Frame(top)
        lang_fr.pack(fill="x", pady=2)
        tk.Label(lang_fr, text="Transcription Language", width=24, anchor="w").pack(side="left")
        lang_box = ttk.Combobox(
            lang_fr,
            textvariable=self.language_choice,
            values=["Auto", "English", "Malay"],
            state="readonly",
            width=18
        )
        lang_box.pack(side="left")

        file_fr = tk.Frame(top)
        file_fr.pack(fill="x", pady=2)
        tk.Label(file_fr, text="Audio File", width=24, anchor="w").pack(side="left")
        tk.Entry(file_fr, textvariable=self.audio_path).pack(side="left", padx=4, fill="x", expand=True)
        tk.Button(file_fr, text="Browse…", command=self.browse_file).pack(side="left")

        tk.Label(top, text="Supported formats: mp3, wav, m4a, mp4", fg="gray").pack(anchor="w", pady=(2, 6))

        prompt_header = tk.Frame(top)
        prompt_header.pack(fill="x", pady=(4, 2))

        tk.Label(prompt_header, text="AI Instruction / Prompt", font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Button(prompt_header, text="Reset AI Prompt", command=self.load_default_prompt).pack(side="right")

        self.prompt_box = scrolledtext.ScrolledText(top, height=8, wrap="word")
        self.prompt_box.pack(fill="x", pady=(0, 6))

        main_panel = tk.Frame(self.root)
        main_panel.pack(fill="both", expand=True, padx=10, pady=5)

        left_panel = tk.Frame(main_panel)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 5))

        tk.Label(left_panel, text="Live Transcript", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.live_box = scrolledtext.ScrolledText(left_panel, height=20, state="disabled", wrap="word")
        self.live_box.pack(fill="both", expand=True)

        right_panel = tk.Frame(main_panel)
        right_panel.pack(side="left", fill="both", expand=True, padx=(5, 0))

        tk.Label(right_panel, text="AI Meaning & Coding", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.qwen_box = scrolledtext.ScrolledText(right_panel, height=20, state="disabled", wrap="word")
        self.qwen_box.pack(fill="both", expand=True)

        self.live_box.tag_configure("ts", foreground="blue")
        self.live_box.tag_configure("txt", foreground="black")

        status_row = tk.Frame(self.root)
        status_row.pack(fill="x", padx=10, pady=(0, 6))

        self.status = tk.StringVar(value="Idle")
        tk.Label(status_row, textvariable=self.status).pack(side="left")

        self.progress = ttk.Progressbar(
            status_row,
            orient="horizontal",
            mode="determinate",
            maximum=100,
            variable=self.progress_var,
            length=340
        )
        self.progress.pack(side="right")

        ctrl = tk.Frame(self.root)
        ctrl.pack(fill="x", padx=10, pady=6)

        self.start_btn = tk.Button(
            ctrl,
            text="Start Transcription",
            command=self.start,
            bg="#BFE8BF",
            activebackground="#A7DCA7",
            relief="raised",
            padx=10,
            pady=4
        )
        self.start_btn.pack(side="right", padx=4)

        self.open_btn = tk.Button(
            ctrl,
            text="Open Output Folder",
            command=self.open_output_folder,
            bg="#FFE59A",
            activebackground="#FFD56A",
            relief="raised",
            padx=10,
            pady=4
        )
        self.open_btn.pack(side="right", padx=4)

        footer = tk.Label(self.root, text="© Mad Sapri Tumiran | Support", fg="gray", cursor="hand2")
        footer.pack(side="bottom", pady=3)
        footer.bind("<Button-1>", self.show_support)

    def load_default_prompt(self):
        default_prompt = (
            "You are a qualitative research assistant.\n"
            "Important rules:\n"
            "1. Do NOT translate the transcript.\n"
            "2. Keep the original language exactly as spoken in the transcript.\n"
            "3. If the transcript is in Malay, respond in Malay.\n"
            "4. If the transcript is in English, respond in English.\n"
            "5. Do not rewrite or paraphrase the transcript into another language.\n"
            "6. Give short structured output only.\n\n"
            "Output exactly in this format:\n"
            "Meaning:\n"
            "Code:\n"
            "Category:\n"
            "SJT:"
        )
        self.prompt_box.delete("1.0", "end")
        self.prompt_box.insert("1.0", default_prompt)

    def show_support(self, _event=None):
        messagebox.showinfo(
            "About RedScribe",
            "RedScribe\n"
            "Research Speech Transcription System\n\n"
            "© Mad Sapri Tumiran\n\n"
            "Support:\n"
            "saprimad@moh.gov.my"
        )

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
            filetypes=[("Audio files", "*.mp3 *.wav *.m4a *.mp4")]
        )
        if path:
            self.audio_path.set(path)

    def open_output_folder(self):
        if self.last_output_folder and os.path.isdir(self.last_output_folder):
            open_folder(self.last_output_folder)
        else:
            ensure_dir(self.base_output_dir)
            open_folder(self.base_output_dir)

    def log_live_segment(self, ts: str, text: str):
        self.live_box.configure(state="normal")
        self.live_box.insert("end", f"[{ts}] ", ("ts",))
        self.live_box.insert("end", f"{text}\n", ("txt",))
        self.live_box.see("end")
        self.live_box.configure(state="disabled")

    def log_qwen_result(self, text: str):
        self.qwen_box.configure(state="normal")
        self.qwen_box.insert("end", f"{text}\n\n")
        self.qwen_box.see("end")
        self.qwen_box.configure(state="disabled")

    def ask_qwen(self, text):
        try:
            custom_prompt = self.prompt_box.get("1.0", "end").strip()
            response = ollama.chat(
                model=QWEN_MODEL,
                messages=[
                    {"role": "system", "content": custom_prompt},
                    {"role": "user", "content": text}
                ],
                options=OLLAMA_OPTIONS
            )
            return response["message"]["content"]
        except Exception as e:
            return f"Meaning:\nQwen error\nCode:\nError\nCategory:\nSystem\nSJT:\nError ({e})"

    def process_qwen_sequentially(self, segments_for_qwen):
        total = len(segments_for_qwen)
        if total == 0:
            return

        for idx, item in enumerate(segments_for_qwen, start=1):
            ts = item["ts"]
            seg_text = item["text"]

            self.root.after(0, self.status.set, f"AI coding {idx}/{total} with {QWEN_MODEL} (GPU requested)...")
            raw_result = self.ask_qwen(seg_text)
            parsed = parse_qwen_output(raw_result)

            pretty = (
                f"[{ts}]\n"
                f"Meaning: {parsed['meaning']}\n"
                f"Code: {parsed['code']}\n"
                f"Category: {parsed['category']}\n"
                f"SJT: {parsed['sjt']}"
            )
            self.root.after(0, self.log_qwen_result, pretty)

            self.ai_rows.append({
                "utterance_no": idx,
                "timestamp": ts,
                "transcript": seg_text,
                "meaning": parsed["meaning"],
                "code": parsed["code"],
                "category": parsed["category"],
                "sjt": parsed["sjt"],
                "raw": parsed["raw"]
            })

        self.root.after(
            0,
            self.status.set,
            f"Completed - 100% | Whisper {self.actual_whisper_device.upper()} ({self.actual_whisper_compute_type}) | Qwen GPU requested"
        )

    def start(self):
        if not self.audio_path.get():
            messagebox.showwarning("Missing file", "Please select an audio file.")
            return

        self.live_box.configure(state="normal")
        self.live_box.delete("1.0", "end")
        self.live_box.configure(state="disabled")

        self.qwen_box.configure(state="normal")
        self.qwen_box.delete("1.0", "end")
        self.qwen_box.configure(state="disabled")

        self.ai_rows = []
        self.progress_var.set(0.0)
        self.status.set("Loading model...")
        self.start_btn.config(state="disabled")

        threading.Thread(target=self.run_whisper, daemon=True).start()

    def run_whisper(self):
        start_clock = time.time()

        audio_path = self.audio_path.get()
        audio_base = os.path.splitext(os.path.basename(audio_path))[0]

        period = (self.period.get() or time.strftime("%Y-%m")).strip()
        if not re.match(r"^\d{4}-\d{2}$", period):
            period = time.strftime("%Y-%m")

        out_folder = os.path.join(self.base_output_dir, period)
        ensure_dir(out_folder)
        self.last_output_folder = out_folder

        filename_base = build_output_name(
            project=self.project.get(),
            period=period,
            label=self.label.get(),
            researcher=self.researcher.get(),
            audio_base=audio_base
        )
        xlsx_path = os.path.join(out_folder, f"{filename_base}.xlsx")

        selected_language_label = self.language_choice.get()
        selected_language_code = LANGUAGE_MAP.get(selected_language_label, None)

        try:
            model, actual_device, actual_compute_type = create_whisper_model()
            self.actual_whisper_device = actual_device
            self.actual_whisper_compute_type = actual_compute_type
        except Exception as e:
            self.root.after(
                0,
                lambda: messagebox.showerror("Whisper Error", f"Gagal load model Whisper.\n\n{e}")
            )
            self.root.after(0, self.status.set, "Failed to load model")
            self.root.after(0, lambda: self.start_btn.config(state="normal"))
            return

        self.root.after(
            0,
            self.status.set,
            f"Transcribing with {actual_device.upper()} ({actual_compute_type}) - 0% | ETA --:--"
        )

        try:
            segments, info = model.transcribe(
                audio_path,
                language=selected_language_code,
                task="transcribe",
                vad_filter=True,
                beam_size=5,
                condition_on_previous_text=True
            )
        except Exception as e:
            self.root.after(
                0,
                lambda: messagebox.showerror("Transcription Error", f"Gagal transcribe audio.\n\n{e}")
            )
            self.root.after(0, self.status.set, "Transcription failed")
            self.root.after(0, lambda: self.start_btn.config(state="normal"))
            return

        duration_s = float(getattr(info, "duration", 0.0)) or 0.0
        t0 = time.time()

        utterance_rows = []
        segment_ranges = []
        last_end = 0.0
        segments_for_qwen = []

        for seg in segments:
            seg_text = (seg.text or "").strip()
            st = float(seg.start)
            en = float(seg.end)

            if en > st:
                segment_ranges.append((st, en))
                last_end = max(last_end, en)

            if seg_text:
                ts = sec_to_hms(st)
                self.root.after(0, self.log_live_segment, ts, seg_text)
                segments_for_qwen.append({"ts": ts, "text": seg_text})

                sents = split_sentences_universal(seg_text)
                for ust, uen, s in distribute_times(st, en, sents):
                    s_clean = (s or "").strip()
                    if s_clean:
                        utterance_rows.append({"start_s": ust, "end_s": uen, "text": s_clean})

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
                    f"Transcribing with {actual_device.upper()} ({actual_compute_type}) - {progress:.0f}% | ETA {eta_str}"
                )

        audio_duration_s = float(getattr(info, "duration", last_end))
        elapsed_min = round((time.time() - start_clock) / 60, 2)

        self.root.after(0, self.progress_var.set, 100.0)
        self.root.after(0, self.status.set, f"Transcription done. Starting AI coding with {QWEN_MODEL} (GPU requested)...")

        self.process_qwen_sequentially(segments_for_qwen)

        meta_from_gui = {
            "project": self.project.get().strip(),
            "researcher": self.researcher.get().strip(),
            "label": self.label.get().strip(),
            "period": period,
            "selected_language": selected_language_label,
        }

        try:
            save_xlsx_with_reports(
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
                ai_rows=self.ai_rows
            )
        except Exception as e:
            self.root.after(
                0,
                lambda: messagebox.showerror("Excel Error", f"Gagal simpan fail Excel.\n\n{e}")
            )
            self.root.after(0, self.status.set, "Excel save failed")
            self.root.after(0, lambda: self.start_btn.config(state="normal"))
            return

        def done_popup():
            self.start_btn.config(state="normal")
            messagebox.showinfo(
                "Transcription Completed Successfully",
                f"This transcription was completed by RedScribe – Research Speech Transcription System in {elapsed_min} minutes.\n\n"
                f"Whisper device used: {actual_device.upper()} ({actual_compute_type})\n"
                f"Ollama model used: {QWEN_MODEL}\n"
                f"Ollama GPU requested: Yes\n"
                f"Language selection: {selected_language_label}\n\n"
                "The generated output is ready for researcher-led review and verification.\n\n"
                "Feedback and suggestions for improvement are welcome at\n"
                "saprimad@moh.gov.my\n\n"
                f"Saved Excel:\n{xlsx_path}"
            )
            open_folder(out_folder)

        self.root.after(0, done_popup)


if __name__ == "__main__":
    root = tk.Tk()
    app = RedScribeApp(root)
    root.mainloop()