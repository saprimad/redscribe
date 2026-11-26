"""Compact, local scientific PDF report; no inference or participant text."""
import argparse
import csv
import math
import os
from pathlib import Path
import tempfile
import textwrap
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

MODEL_NAMES = {
    "large-v3": ("OpenAI Whisper Large-v3", "openai/whisper-large-v3"),
    "turbo": ("OpenAI Whisper Large-v3 Turbo", "openai/whisper-large-v3-turbo"),
    "Mesolitica Whisper v3": ("Mesolitica Whisper Large-v3 Turbo v3", "mesolitica/Malaysian-whisper-large-v3-turbo-v3"),
    "Mesolitica XLS-R 300M": ("Mesolitica wav2vec2 XLS-R 300M", "mesolitica/wav2vec2-xls-r-300m-mixed"),
    "Meta MMS 1B (Malay)": ("Meta MMS 1B All (Malay adapter)", "facebook/mms-1b-all"),
    "Qwen3-ASR 1.7B": ("Qwen3-ASR 1.7B", "Qwen/Qwen3-ASR-1.7B"),
    "BuzzASR Malay": ("BuzzASR Malay", "BuzzASR/malay"),
    **{k:("OpenAI Whisper "+k.title(),"openai/whisper-"+k) for k in ("tiny","base","small","medium")}
}
NAVY="#243B53"
GREY="#536579"
RED="#A4262C"

def _read(directory,name):
    with (directory/name).open(encoding="utf-8-sig",newline="") as stream:
        return list(csv.DictReader(stream))

def _number(value):
    try:
        n=Decimal(str(value))
        return n if n.is_finite() else None
    except (InvalidOperation,ValueError,TypeError):
        return None

def _fmt(value,kind="count"):
    n=_number(value)
    if n is None:
        return "N/A"
    if kind=="count":
        return f"{int(n):,}" if n==n.to_integral_value() else f"{n:,.2f}"
    if kind=="percent":
        return f"{n*100:.2f}%"
    if kind=="seconds":
        if n<0:
            return "N/A"
        minutes,seconds=divmod(n,60)
        return f"{int(minutes)}m {seconds:05.2f}s"
    if kind=="rtf":
        return f"{n:.4f}"
    return f"{n:,.1f}"

def _name(key):
    return MODEL_NAMES.get(key,(str(key),"Not recorded"))[0]

def generate_pdf(directory, *, data=None, metadata=None):
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.image import imread
    directory=Path(directory)
    if data is None:
        data=tuple(_read(directory,n) for n in ("model_summary.csv","recording_results.csv","efficiency_summary.csv"))
    summary,rows,efficiency=data
    metadata=metadata or {}
    if not summary or not rows:
        raise ValueError("Benchmark exports contain no result rows")
    common=[r for r in summary if r.get("cohort")=="common_completed"]
    attempted=[r for r in summary if r.get("cohort")=="all_attempted"]
    models=list(dict.fromkeys(r.get("model_key","") for r in rows))
    # Labels are short, deterministic model references, not participant identifiers.
    labels={m:f"M{i:02d}" for i,m in enumerate(models,1)}
    completed=[r for r in rows if r.get("status")=="completed"]
    ids={r.get("participant_id") for r in rows}
    n_common=max((int(_number(r.get("word_scored")) or 0) for r in common),default=0)
    def best(metric):
        available=[r for r in common if _number(r.get(metric)) is not None]
        if not available:
            return "Not available"
        v=min(_number(r[metric]) for r in available)
        return ", ".join(labels[r["model_key"]] for r in available if _number(r[metric])==v)+" ("+_fmt(v,"percent")+")"
    def total_time(model):
        values=[_number(r.get("inference_seconds")) for r in completed if r.get("model_key")==model]
        return sum(values) if values and all(v is not None and v>=0 for v in values) else None
    def consistent_total(field):
        by_record={}
        for r in completed:
            v=_number(r.get(field))
            if v is not None:
                by_record.setdefault(r.get("participant_id"),set()).add(v)
        if len(by_record)!=len(ids) or any(len(v)!=1 for v in by_record.values()):
            return None
        return sum(next(iter(v)) for v in by_record.values())
    def table_rows(data,fields):
        return [[labels[r["model_key"]]]+[_fmt(r.get(k),kind) for k,kind in fields] for r in data]
    target=directory/"scientific_report.pdf"
    fd,temp=tempfile.mkstemp(suffix=".pdf",dir=directory)
    os.close(fd)
    try:
        with PdfPages(temp,metadata={"Title":"RedScribe | Scientific benchmark report","Author":"RedScribe"}) as pdf:
            page=0
            def base(kicker,title):
                nonlocal page
                page+=1
                fig=Figure(figsize=(8.27,11.69),facecolor="white")
                fig.text(.075,.965,"RedScribe",fontsize=17,color=RED,weight="bold")
                fig.text(.925,.967,"SCIENTIFIC BENCHMARK  /  V2",ha="right",fontsize=8,color=GREY)
                fig.add_artist(__import__("matplotlib").lines.Line2D([.075,.925],[.947,.947],transform=fig.transFigure,color=NAVY,lw=1))
                fig.text(.075,.92,kicker.upper(),fontsize=9,color=GREY,weight="bold")
                fig.text(.075,.886,title,fontsize=20,color=NAVY,weight="bold")
                fig.text(.075,.035,"RedScribe  |  Derived local research report",fontsize=8,color=GREY)
                fig.text(.925,.035,f"{page:02d}",ha="right",fontsize=9,color=GREY)
                return fig
            def heading(fig,y,text):
                fig.text(.075,y,text,fontsize=12,weight="bold",color=NAVY)
            def prose(fig,y,text,width=96):
                for line in textwrap.wrap(text,width=width):
                    fig.text(.075,y,line,fontsize=9,color=NAVY)
                    y-=.017
                return y-.012
            def table(fig,top,headers,values,widths=None):
                values=values or [["N/A"]+[""]*(len(headers)-1)]
                height=.024*(len(values)+1)
                ax=fig.add_axes([.075,top-height,.85,height])
                ax.axis("off")
                t=ax.table(cellText=values,colLabels=headers,cellLoc="right",colLoc="right",colWidths=widths,bbox=[0,0,1,1])
                t.auto_set_font_size(False)
                t.set_fontsize(8)
                for (i,j),cell in t.get_celld().items():
                    cell.set_edgecolor("white")
                    cell.set_linewidth(.7)
                    cell.set_facecolor(NAVY if i==0 else ("#EDF2F7" if i%2 else "#F8FAFC"))
                    cell.get_text().set_color("white" if i==0 else NAVY)
                    if i==0:
                        cell.get_text().set_weight("bold")
                    if j==0:
                        cell.get_text().set_ha("left")
                return top-height-.035
            def figure(fig,name,box):
                p=directory/(name+".png")
                if not p.is_file():
                    fig.text(box[0],box[1]+box[3]/2,"Figure unavailable",fontsize=10,color=GREY)
                    return
                ax=fig.add_axes(box)
                ax.imshow(imread(p))
                ax.axis("off")
            def save(fig):
                pdf.savefig(fig)
                fig.clear()

            fig=base("01 / 02   Executive summary and scope","ASR benchmark overview")
            for i,(value,caption) in enumerate(((str(len(models)),"Selected models"),(str(len(ids)),"Recordings"),(f"{len(completed)}/{len(rows)}","Completed observations"))):
                x=.075+i*.29
                fig.text(x,.81,value,fontsize=28,color=NAVY,weight="bold")
                fig.text(x,.78,caption,fontsize=9,color=GREY)
            y=prose(fig,.735,"Full-length local ASR evaluation. Results are descriptive; completion does not establish accuracy or full audio coverage.")
            heading(fig,y,"Dataset and benchmark coverage")
            y=table(fig,y-.02,["Measure","Value"],[
                ["Unique audio duration",_fmt(consistent_total("audio_seconds"),"seconds")],
                ["Reference words",_fmt(consistent_total("reference_words"))],
                ["Reference characters",_fmt(consistent_total("reference_characters"))],
                ["Common scored recordings",str(n_common)],
                ["Lowest common-cohort WER",best("corpus_wer")],
                ["Lowest common-cohort CER",best("corpus_cer")]], [.58,.42])
            heading(fig,y,"04  Completion and failures")
            y=table(fig,y-.02,["Model","Total","Done","Failed","Cancelled","Not run","Unavailable"],
                table_rows(attempted,[(k,"count") for k in ("recordings_total","recordings_completed","recordings_failed","recordings_cancelled","recordings_not_run","recordings_unavailable")]))
            prose(fig,y,"Model codes are defined on the next page. Repeated observations of the same recording are paired, not independent.")
            save(fig)

            fig=base("03   Model inventory and provenance","Models and environment")
            y=.842
            for m in models:
                full,checkpoint=MODEL_NAMES.get(m,(str(m),"Not recorded"))
                fig.text(.075,y,labels[m]+"  "+full,fontsize=9.5,weight="bold",color=NAVY)
                fig.text(.10,y-.017,checkpoint,fontsize=8,color=GREY)
                y-=.042
            heading(fig,y-.012,"Recorded runtime environment")
            y-=.04
            for key in ("Run commit","Python","Platform","CUDA build","GPU","RAM","Scoring engine","RapidFuzz"):
                y=prose(fig,y,key+": "+str(metadata.get(key) or "Not recorded"),100)
            prose(fig,y,"Model identifiers are registry labels; exact loaded revisions must be checked in the protected checkpoint. Report generated (UTC): "+datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"))
            save(fig)

            fig=base("05 / 06   Corpus and recording-average accuracy","Recognition performance")
            y=table(fig,.845,["Model","Scored n","Corpus WER","Corpus CER","Macro WER","Macro CER"],
                table_rows(common,[("word_scored","count"),("corpus_wer","percent"),("corpus_cer","percent"),("macro_wer","percent"),("macro_cer","percent")]))
            y=prose(fig,y,"WER = (word substitutions + deletions + insertions) / reference words. CER applies the same formula to characters. Corpus rates pool counts; macro rates average recording-level rates.")
            figure(fig,"corpus_accuracy",[.075,.15,.85,min(.39,max(.1,y-.18))])
            fig.text(.075,.115,"Figure 1. Corpus WER and CER on the common completed cohort.",fontsize=9,color=GREY)
            prose(fig,.087,"Lower is better. WER can exceed 100%; neither metric measures semantic accuracy.")
            save(fig)

            fig=base("07 / 08   Absolute edit counts","Error composition")
            heading(fig,.842,"Word-level errors")
            y=table(fig,.822,["Model","Substitutions","Deletions","Insertions","Reference words"],
                table_rows(common,[(k,"count") for k in ("word_substitutions","word_deletions","word_insertions","reference_words")]))
            heading(fig,y,"Character-level errors")
            y=table(fig,y-.02,["Model","Substitutions","Deletions","Insertions","Reference chars"],
                table_rows(common,[(k,"count") for k in ("char_substitutions","char_deletions","char_insertions","reference_characters")]))
            y=prose(fig,y,"Substitution: a reference unit is replaced. Deletion: a reference unit is missing. Insertion: an extra unit appears. Counts are exact integers, not rounded scientific notation.")
            prose(fig,y,"Edit counts alone cannot distinguish dialect normalisation, hallucination, repetition or coverage failures. Text-level inspection is required.")
            save(fig)

            fig=base("09 / 10   Efficiency and resource observations","Computational performance")
            values=[[labels[r["model_key"]],_fmt(r.get("recordings_timed")),_fmt(total_time(r["model_key"]),"seconds"),_fmt(r.get("aggregate_rtf"),"rtf"),_fmt(r.get("mean_rtf"),"rtf"),_fmt(r.get("median_rtf"),"rtf")] for r in efficiency]
            y=table(fig,.845,["Model","Timed n","Inference time","Aggregate RTF","Mean RTF","Median RTF"],values,[.12,.12,.24,.18,.17,.17])
            heading(fig,y,"Observed system-wide peaks")
            y=table(fig,y-.02,["Model","GPU MB","GPU °C","RAM MB","GPU util. %"],
                table_rows(efficiency,[(k,"decimal") for k in ("gpu_memory_used_mb_peak_max","gpu_temperature_c_peak_max","ram_used_mb_peak_max","gpu_util_percent_peak_max")]))
            y=prose(fig,y,"RTF = inference seconds / audio seconds. Aggregate RTF pools durations. Lower is faster. Timings and resources are available completed observations, not necessarily the common accuracy cohort.")
            prose(fig,y,"GPU and RAM observations are system-wide sampled peaks, not model-exclusive allocations. N/A means unavailable, not zero.")
            save(fig)

            fig=base("11   Scientific figures","Accuracy and speed")
            figure(fig,"accuracy_speed",[.075,.46,.85,.38])
            fig.text(.075,.435,"Figure 2. Aggregate RTF versus corpus WER, common timed cohort.",fontsize=9,color=GREY)
            if n_common>1:
                figure(fig,"wer_distribution",[.075,.10,.41,.30])
                figure(fig,"cer_distribution",[.51,.10,.41,.30])
                fig.text(.075,.075,"Figures 3–4. Recording-level WER and CER distributions.",fontsize=9,color=GREY)
            else:
                prose(fig,.39,"Distribution plots omitted: fewer than two common scored recordings. A single observation does not describe variability.")
            save(fig)

            fig=base("12 / 13   Integrity and interpretation","Scientific safeguards")
            y=.84
            y=prose(fig,y,f"Completed observations with recorded zero worker exit code: {sum(str(r.get('worker_exit_code'))=='0' for r in completed)} of {len(completed)}.")
            y=prose(fig,y,"This report is derived from saved benchmark results. Structured publication includes PDF and supporting files in its publication checksum manifest; standalone legacy exports may not.")
            heading(fig,y,"Limitations")
            y-=.025
            for s in ("No claim of model superiority follows from a single recording.",
                      "Missing, failed and cancelled observations must not be treated as zero-error scores.",
                      "Audio coverage, exact model revisions, decoding configuration and alignment require independent verification.",
                      "Resource peaks depend on hardware, sampling and other system activity.",
                      "Repeated runs may differ; investigate reproducibility before attributing changes to a model."):
                y=prose(fig,y,s)
            heading(fig,y,"Confidentiality")
            y=prose(fig,y-.025,"Raw transcripts, source paths, checkpoint details and diagnostic logs belong in restricted research storage. Do not distribute SENSITIVE DATA without authorisation. Folder segregation is not encryption.")
            prose(fig,y,"Full per-recording results, figures and numerical summaries are available in supporting exports. No participant-level text is included in this report.")
            save(fig)
        os.replace(temp,target)
    finally:
        Path(temp).unlink(missing_ok=True)
    return target

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory",type=Path)
    print(generate_pdf(parser.parse_args().directory))
