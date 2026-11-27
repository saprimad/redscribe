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
SHORT_NAMES = {
    "large-v3":"Whisper Large-v3", "turbo":"Whisper Turbo",
    "Mesolitica Whisper v3":"Mesolitica Whisper", "Mesolitica XLS-R 300M":"Mesolitica XLS-R",
    "Meta MMS 1B (Malay)":"Meta MMS 1B", "Qwen3-ASR 1.7B":"Qwen3-ASR 1.7B",
    "BuzzASR Malay":"BuzzASR Malay",
    **{k:"Whisper "+k.title() for k in ("tiny","base","small","medium")}
}
def short_name(key):
    return SHORT_NAMES.get(key,str(key))

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
    from matplotlib.lines import Line2D
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
    labels={m:short_name(m) for m in models}
    completed=[r for r in rows if r.get("status")=="completed"]
    ids={r.get("participant_id") for r in rows}
    import re
    safe_ids=sorted(str(i) for i in ids if isinstance(i,str) and re.fullmatch(r"(?:P|R)[0-9]{1,6}",i))
    scope=("Recording ID: "+(safe_ids[0] if len(safe_ids)==1 else "restricted ID")) if len(ids)==1 else f"Multi-recording corpus — {len(ids)} recordings"
    common.sort(key=lambda r: (_number(r.get("corpus_wer")) is None, _number(r.get("corpus_wer")) or Decimal(0)))
    order={r["model_key"]:i for i,r in enumerate(common)}
    attempted.sort(key=lambda r:order.get(r["model_key"],len(order)))
    efficiency=sorted(efficiency,key=lambda r:order.get(r["model_key"],len(order)))
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
                fig.text(.075,.965,"RedScribe©",fontsize=17,color=RED,weight="bold")
                fig.text(.925,.967,"SCIENTIFIC BENCHMARK REPORT",ha="right",fontsize=8,color=GREY)
                fig.add_artist(Line2D([.075,.925],[.947,.947],transform=fig.transFigure,color=NAVY,lw=1))
                fig.text(.075,.92,kicker.upper(),fontsize=9,color=GREY,weight="bold")
                fig.text(.075,.886,title,fontsize=20,color=NAVY,weight="bold")
                fig.text(.075,.035,"Faculty of Pharmacy, Universiti Teknologi MARA (UiTM)",fontsize=8,color=GREY)
                fig.text(.925,.035,f"{page:02d} / 08",ha="right",fontsize=9,color=GREY)
                fig.text(.925,.929,scope,ha="right",fontsize=8,color=GREY)
                return fig
            def heading(fig,y,text):
                fig.text(.075,y,text,fontsize=12,weight="bold",color=NAVY)
            def prose(fig,y,text,width=96):
                for line in textwrap.wrap(text,width=width):
                    fig.text(.075,y,line,fontsize=9,color=NAVY)
                    y-=.017
                return y-.012
            def table(fig,top,headers,values,widths=None,highlight_errors=False):
                values=values or [["N/A"]+[""]*(len(headers)-1)]
                if widths is None and headers[0]=="Model":
                    widths=[.30]+[.70/(len(headers)-1)]*(len(headers)-1)
                height=(.018 if len(values)>7 else .024)*(len(values)+1)
                ax=fig.add_axes([.075,top-height,.85,height])
                ax.axis("off")
                t=ax.table(cellText=values,colLabels=headers,cellLoc="right",colLoc="right",colWidths=widths,bbox=[0,0,1,1])
                t.auto_set_font_size(False)
                t.set_fontsize(7.5 if len(headers)>5 else 8.5)
                for (i,j),cell in t.get_celld().items():
                    cell.set_edgecolor("white")
                    cell.set_linewidth(.7)
                    cell.PAD=.045
                    cell.set_facecolor(NAVY if i==0 else ("#EDF2F7" if i%2 else "#F8FAFC"))
                    cell.get_text().set_color("white" if i==0 else NAVY)
                    if i==0:
                        cell.get_text().set_weight("bold")
                    if j==0:
                        cell.get_text().set_ha("left")
                if highlight_errors:
                    # Within-row relative error composition, not clinical or validated quality thresholds.
                    for i,row in enumerate(values,1):
                        counts=[_number(str(v).replace(",","")) for v in row[1:4]]
                        if any(v is None for v in counts) or len(set(counts))<2:
                            continue
                        for j,v in enumerate(counts,1):
                            t[i,j].set_facecolor("#F8D7DA" if v==max(counts) else "#DDF1E3" if v==min(counts) else "#FFF0C2")
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

            fig=base("01   Executive summary and scope","ASR benchmark overview")
            for i,(value,caption) in enumerate(((str(len(models)),"Selected models"),(str(len(ids)),"Recordings"),(f"{len(completed)}/{len(rows)}","Completed observations"))):
                x=.075+i*.29
                fig.text(x,.81,value,fontsize=28,color=NAVY,weight="bold")
                fig.text(x,.78,caption,fontsize=9,color=GREY)
            y=prose(fig,.735,"Full-length local ASR evaluation. Results are descriptive; completion does not establish accuracy or full audio coverage.")
            heading(fig,y,"Dataset and benchmark coverage")
            y=table(fig,y-.02,["Measure","Value"],[
                ["Recording ID / scope",safe_ids[0] if len(ids)==1 and len(safe_ids)==1 else f"{len(ids)} recordings"],
                ["Unique audio duration",_fmt(consistent_total("audio_seconds"),"seconds")],
                ["Reference words",_fmt(consistent_total("reference_words"))],
                ["Reference characters",_fmt(consistent_total("reference_characters"))],
                ["Common scored recordings",str(n_common)],
                ["Lowest common-cohort WER",best("corpus_wer")],
                ["Lowest common-cohort CER",best("corpus_cer")]], [.48,.52])
            heading(fig,y,"02  Completion and failures")
            y=table(fig,y-.02,["Model","Total","Done","Failed","Cancelled","Not run","Unavail."],
                table_rows(attempted,[(k,"count") for k in ("recordings_total","recordings_completed","recordings_failed","recordings_cancelled","recordings_not_run","recordings_unavailable")]))
            prose(fig,y,"Unavail. = unavailable. Repeated observations of the same recording are paired, not independent.")
            save(fig)

            fig=base("03   Model inventory and provenance","Models and environment")
            y=.842
            for m in models:
                full,checkpoint=MODEL_NAMES.get(m,(str(m),"Not recorded"))
                fig.text(.075,y,full,fontsize=9.5,weight="bold",color=NAVY)
                fig.text(.10,y-.017,checkpoint,fontsize=8,color=GREY)
                y-=.034
            heading(fig,y-.012,"Recorded runtime environment")
            y-=.04
            y=table(fig,y+.01,["Parameter","Recorded value"],[[key,str(metadata.get(key) or "Not recorded")] for key in ("Run commit","Python","Platform","CUDA build","GPU","RAM","Scoring engine","RapidFuzz")],[.27,.73])
            prose(fig,y,"Model identifiers are registry labels; exact loaded revisions must be checked in the protected checkpoint. Report generated (UTC): "+datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"))
            save(fig)

            fig=base("04   Recognition accuracy","Recognition performance")
            fields=[("corpus_wer","percent"),("corpus_cer","percent")]
            headers=["Model","WER","CER"]
            if len(ids)>1:
                headers=["Model","Scored n","Corpus WER","Corpus CER","Macro WER","Macro CER"]
                fields=[("word_scored","count")]+fields+[("macro_wer","percent"),("macro_cer","percent")]
            y=table(fig,.845,headers,table_rows(common,fields))
            y=prose(fig,y,"Ordered by unrounded WER (ascending); missing scores last. Equal scores are not distinct ranks.")
            y=prose(fig,y,"WER = (word substitutions + deletions + insertions) / reference words. CER applies the same formula to characters. Corpus rates pool counts; macro rates average recording-level rates.")
            valid=[r for r in common if _number(r.get("corpus_wer")) is not None and _number(r.get("corpus_cer")) is not None]
            if valid:
                ax=fig.add_axes([.32,.17,.58,min(.32,max(.10,y-.20))])
                pos=list(range(len(valid)))
                ax.barh([i-.18 for i in pos],[float(_number(r["corpus_wer"])*100) for r in valid],height=.32,color="#386B9C",label="WER")
                ax.barh([i+.18 for i in pos],[float(_number(r["corpus_cer"])*100) for r in valid],height=.32,color="#D9A348",label="CER")
                ax.set_yticks(pos,[labels[r["model_key"]] for r in valid],fontsize=8)
                ax.invert_yaxis()
                ax.set_xlabel("Error rate (%)",fontsize=8)
                ax.tick_params(axis="x",labelsize=8)
                ax.legend(loc="upper right",fontsize=7,frameon=False)
                ax.spines[["top","right"]].set_visible(False)
                ax.set_axisbelow(True)
                ax.grid(axis="x",alpha=.15)
            else:
                prose(fig,.36,"No common scored observations available.")
            fig.text(.075,.115,"Figure 1. Corpus WER and CER on the common completed cohort.",fontsize=9,color=GREY)
            prose(fig,.087,"Lower is better. WER can exceed 100%; neither metric measures semantic accuracy.")
            save(fig)

            fig=base("05   Absolute edit counts","Error composition")
            heading(fig,.842,"Word-level errors")
            y=table(fig,.822,["Model","Substitutions","Deletions","Insertions","Reference words"],
                table_rows(common,[(k,"count") for k in ("word_substitutions","word_deletions","word_insertions","reference_words")]),highlight_errors=True)
            heading(fig,y,"Character-level errors")
            y=table(fig,y-.02,["Model","Substitutions","Deletions","Insertions","Reference chars"],
                table_rows(common,[(k,"count") for k in ("char_substitutions","char_deletions","char_insertions","reference_characters")]),highlight_errors=True)
            from matplotlib.patches import Rectangle
            for i,(label,colour) in enumerate((("Largest","#F8D7DA"),("Intermediate","#FFF0C2"),("Smallest","#DDF1E3"))):
                x=.075+i*.27
                fig.add_artist(Rectangle((x,y-.005),.021,.013,transform=fig.transFigure,facecolor=colour,edgecolor="#D5DEE8",lw=.5))
                fig.text(x+.029,y,label,fontsize=8,color=NAVY)
            y=prose(fig,y-.027,"Colours compare error types within each model, not accuracy thresholds. Equal counts share a colour; all-equal rows remain neutral.")
            prose(fig,y,"S = replacement; D = missing unit; I = extra unit. Counts are exact integers. Edit counts alone cannot identify dialect normalisation or hallucination.")
            save(fig)

            fig=base("06   Output length and error profile","Output length analysis")
            def length_values(row,prefix,refkey):
                ref,d,i=(_number(row.get(k)) for k in (refkey,prefix+"_deletions",prefix+"_insertions"))
                if any(v is None for v in (ref,d,i)) or ref<=0 or d>ref:
                    return None,None
                return ref-d+i,(ref-d+i)/ref
            lengths=[]
            for row in common:
                words,wr=length_values(row,"word","reference_words")
                chars,cr=length_values(row,"char","reference_characters")
                lengths.append([labels[row["model_key"]],_fmt(words),_fmt(wr,"percent"),_fmt(chars),_fmt(cr,"percent")])
            y=table(fig,.845,["Model","ASR words","Word ratio","ASR chars","Char ratio"],lengths)
            y=prose(fig,y,"Generated units = reference units − deletions + insertions. A ratio of 100% indicates equal length, not accurate transcription.")
            available=[]
            for row in common:
                counts=[_number(row.get("word_"+k)) for k in ("substitutions","deletions","insertions")]
                if all(v is not None for v in counts):
                    available.append((labels[row["model_key"]],counts))
            if available:
                ax=fig.add_axes([.32,.22,.58,min(.28,max(.12,y-.25))])
                left=[0.0]*len(available)
                for j,(name,color) in enumerate(zip(("Substitution","Deletion","Insertion"),("#D5A43C","#C45B5B","#648BB4"))):
                    vals=[float(v[j]) for _,v in available]
                    ax.barh(range(len(vals)),vals,left=left,label=name,color=color)
                    left=[a+b for a,b in zip(left,vals)]
                ax.set_yticks(range(len(available)),[n for n,_ in available],fontsize=7)
                ax.invert_yaxis()
                ax.set_xlabel("Absolute word-level edit counts",fontsize=8)
                ax.tick_params(axis="x",labelsize=8)
                ax.legend(loc="upper center",bbox_to_anchor=(.5,-.15),ncol=3,fontsize=7,frameon=False)
                ax.spines[["top","right"]].set_visible(False)
                ax.set_axisbelow(True)
                ax.grid(axis="x",alpha=.15)
            fig.text(.075,.12,"Figure 2. Absolute word-level edit composition.",fontsize=9,color=GREY)
            prose(fig,.095,"Length imbalance and edit composition are diagnostic indicators, not evidence of truncation or hallucination.")
            save(fig)

            fig=base("07   Efficiency and resource observations","Computational performance")
            values=table_rows(efficiency,[(k,kind) for k,kind in (("loading_seconds_total","decimal"),("inference_seconds_total","decimal"),("loading_inference_seconds_total","decimal"),("aggregate_rtf","rtf"))])
            # All durations are seconds; loading is counted once per observed session.
            y=table(fig,.845,["Model","Loading (s)","Inference (s)","Combined (s)","RTF"],values,[.32,.17,.17,.18,.16])
            y=prose(fig,y,"Loading is counted once per recorded completed session. Combined = loading + inference; excludes warm-up, scoring, cleanup and reporting. RTF excludes loading. Missing timings remain N/A.")
            heading(fig,y,"Observed system-wide peaks")
            y=table(fig,y-.02,["Model","GPU MB","GPU °C","RAM MB","GPU util. %"],
                table_rows(efficiency,[(k,"decimal") for k in ("gpu_memory_used_mb_peak_max","gpu_temperature_c_peak_max","ram_used_mb_peak_max","gpu_util_percent_peak_max")]))
            y=prose(fig,y,"RTF = inference seconds / audio seconds. Aggregate RTF pools durations. Lower is faster. Timings and resources are available completed observations, not necessarily the common accuracy cohort.")
            prose(fig,y,"GPU and RAM observations are system-wide sampled peaks, not model-exclusive allocations. N/A means unavailable, not zero.")
            save(fig)

            fig=base("08   Scientific figures","Accuracy and speed")
            figure(fig,"accuracy_speed",[.075,.46,.85,.38])
            fig.text(.075,.435,"Figure 3. Aggregate RTF versus corpus WER, common timed cohort.",fontsize=9,color=GREY)
            if n_common>1:
                figure(fig,"wer_distribution",[.075,.10,.41,.30])
                figure(fig,"cer_distribution",[.51,.10,.41,.30])
                fig.text(.075,.075,"Figures 4–5. Recording-level WER and CER distributions.",fontsize=9,color=GREY)
            else:
                y=prose(fig,.39,"Distribution plots omitted: fewer than two common scored recordings. A single observation does not describe variability.")
                heading(fig,y,"Descriptive findings")
                y=prose(fig,y-.025,"Lowest observed common-cohort WER: "+best("corpus_wer")+". Lowest observed CER: "+best("corpus_cer")+".")
                timed=[r for r in efficiency if _number(r.get("aggregate_rtf")) is not None]
                if timed:
                    fastest=min(timed,key=lambda r:_number(r["aggregate_rtf"]))
                    y=prose(fig,y,"Lowest observed aggregate RTF: "+labels[fastest["model_key"]]+" ("+_fmt(fastest["aggregate_rtf"],"rtf")+"). Timings alone do not verify audio coverage.")
                for field,description in (("word_deletions","word deletions"),("word_insertions","word insertions")):
                    valid=[r for r in common if _number(r.get(field)) is not None]
                    if valid:
                        highest=max(valid,key=lambda r:_number(r[field]))
                        y=prose(fig,y,"Largest observed count of "+description+": "+labels[highest["model_key"]]+" ("+_fmt(highest[field])+").")
            save(fig)

            fig=base("09   Integrity and interpretation","Scientific safeguards")
            y=.84
            y=prose(fig,y,f"Completed observations with recorded zero worker exit code: {sum(_number(r.get('worker_exit_code'))==0 for r in completed)} of {len(completed)}.")
            y=prose(fig,y,"This report is derived from saved benchmark results. Structured publication includes PDF and supporting files in its publication checksum manifest; standalone legacy exports may not.")
            heading(fig,y,"Limitations and pending validation")
            y-=.025
            for s in ("No claim of model superiority follows from a single recording.",
                      "Missing, failed and cancelled observations must not be treated as zero-error scores.",
                      "Actual processed chunk coverage and GPU-synchronised timing are not independently verified. Exact model revisions, decoding configuration and alignment also require verification.",
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
