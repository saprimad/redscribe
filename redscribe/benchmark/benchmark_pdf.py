"""Local PDF report from existing benchmark CSV/figure exports, without ASR."""
import argparse
import csv
import math
import os
from pathlib import Path
import tempfile
import textwrap

FIGURES = ("corpus_accuracy", "wer_distribution", "cer_distribution",
           "accuracy_speed", "participant_wer_heatmap")

def _read(directory, name):
    with (directory / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))

def _number(value, percent=False):
    try:
        n = float(value)
        if not math.isfinite(n):
            return "Not available"
        return f"{n*100:.2f}%" if percent else f"{n:.4g}"
    except (TypeError, ValueError):
        return "Not available"

def generate_pdf(directory):
    """Create a separate derived report; never modify source exports."""
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.image import imread
    directory = Path(directory)
    summary = _read(directory, "model_summary.csv")
    rows = _read(directory, "recording_results.csv")
    efficiency = _read(directory, "efficiency_summary.csv")
    if not summary or not rows:
        raise ValueError("Benchmark exports contain no result rows")
    common = [r for r in summary if r.get("cohort") == "common_completed"]
    attempted = [r for r in summary if r.get("cohort") == "all_attempted"]
    models = list(dict.fromkeys(r.get("model_key", "") for r in rows))
    def lines_for(data, fields):
        return [" | ".join(str(r.get(k) or "Not available") if kind == "text"
                   else _number(r.get(k), kind == "percent")
                   for k, kind in fields) for r in data]
    sections = [
        ("Executive summary", [f"Selected models: {len(models)}",
         f"Model-recording observations: {len(rows)}",
         f"Completed observations: {sum(r.get('status') == 'completed' for r in rows)}",
         "Derived from existing benchmark exports. Completion is not proof of accuracy or full audio coverage."]),
        ("Evaluation scope", ["Local full-length benchmark export; each recording may be evaluated by multiple models.",
         "Recording observations are paired, not independent. No participant text, source paths or participant identifiers are reproduced."]),
        ("Model inventory", models),
        ("Completion and failures", lines_for(attempted, [("model_key","text"),("recordings_total","number"),("recordings_completed","number"),("recordings_failed","number"),("recordings_cancelled","number"),("recordings_not_run","number"),("recordings_unavailable","number")])),
        ("Corpus accuracy — common completed cohort", lines_for(common,[("model_key","text"),("word_scored","number"),("corpus_wer","percent"),("corpus_cer","percent")])),
        ("Recording-average accuracy — common cohort", lines_for(common,[("model_key","text"),("macro_wer","percent"),("macro_cer","percent")])),
        ("Word error composition — common cohort", lines_for(common,[("model_key","text"),("word_substitutions","number"),("word_deletions","number"),("word_insertions","number"),("reference_words","number")])),
        ("Character error composition — common cohort", lines_for(common,[("model_key","text"),("char_substitutions","number"),("char_deletions","number"),("char_insertions","number"),("reference_characters","number")])),
        ("Computational efficiency — available completed timings", lines_for(efficiency,[("model_key","text"),("recordings_timed","number"),("mean_rtf","number"),("median_rtf","number"),("aggregate_rtf","number")])),
        ("Resource observations — system-wide peaks", lines_for(efficiency,[("model_key","text"),("gpu_memory_used_mb_peak_max","number"),("gpu_temperature_c_peak_max","number"),("ram_used_mb_peak_max","number")])),
        ("Scientific figures", ["Existing PNG exports are reproduced where available. Missing figures are not fabricated. Single-recording distributions are descriptive only."]),
        ("Runtime and integrity", [f"Completed observations with recorded zero worker exit code: {sum(r.get('status') == 'completed' and r.get('worker_exit_code') == '0' for r in rows)}",
         "This derived PDF is not included in the existing export integrity manifest. Source export hashes should be verified separately.",
         "Audio coverage, alignment and checkpoint provenance require separate verification."]),
        ("Interpretation and limitations", ["WER and CER are edit-error rates, not semantic accuracy. WER may exceed 100%.",
         "RTF is processing time divided by audio duration; timings depend on backend and configuration.",
         "Do not infer model superiority from one recording. Human verification remains necessary.",
         "No missing value is interpreted as zero."])
    ]
    headers = {4:"Model | Total | Completed | Failed | Cancelled | Not run | Unavailable",
               5:"Model | Scored recordings | WER | CER",6:"Model | Macro WER | Macro CER",
               7:"Model | Substitutions | Deletions | Insertions | Reference words",
               8:"Model | Substitutions | Deletions | Insertions | Reference characters",
               9:"Model | Timed recordings | Mean RTF | Median RTF | Aggregate RTF",
               10:"Model | GPU memory MB | GPU temperature C | RAM MB"}
    target = directory / "scientific_report.pdf"
    fd, temp = tempfile.mkstemp(suffix=".pdf", dir=directory)
    os.close(fd)
    try:
        with PdfPages(temp, metadata={"Title":"RedScribe scientific benchmark report","Author":"RedScribe"}) as pdf:
            page = 0
            def base(title):
                nonlocal page
                page += 1
                fig = Figure(figsize=(8.27,11.69), facecolor="white")
                fig.text(.08,.96,"REDSCRIBE  /  SCIENTIFIC BENCHMARK",fontsize=10,color="#536579")
                fig.text(.08,.91,title,fontsize=15,weight="bold",wrap=True)
                fig.text(.08,.04,f"Derived local report  |  {page}",fontsize=9,color="#536579")
                return fig
            for index,(title, entries) in enumerate(sections,1):
                wrapped = [line for entry in entries for line in textwrap.wrap(entry, width=90, break_long_words=True) or [""]]
                if not wrapped:
                    wrapped = ["Not available"]
                for start in range(0,len(wrapped),26):
                    fig = base(f"{index:02d}  {title}" + (" (continued)" if start else ""))
                    if index in headers:
                        fig.text(.08,.86,headers[index],fontsize=8,weight="bold",wrap=True)
                    for j,line in enumerate(wrapped[start:start+26]):
                        fig.text(.08,.82-j*.028,line,fontsize=10)
                    pdf.savefig(fig)
                if index == 11:
                    for name in FIGURES:
                        # Heatmap contains participant IDs; omit from shareable derived PDF.
                        if name == "participant_wer_heatmap":
                            continue
                        image = directory / (name + ".png")
                        if image.is_file():
                            fig = base(name.replace("_"," ").title())
                            ax = fig.add_axes([.07,.19,.86,.64])
                            ax.imshow(imread(image))
                            ax.axis("off")
                            pdf.savefig(fig)
        os.replace(temp,target)
    finally:
        Path(temp).unlink(missing_ok=True)
    return target

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="Existing benchmark output directory")
    print(generate_pdf(parser.parse_args().directory))
