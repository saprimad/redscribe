"""Scientific CSV exports from model-major matrix; rates are fractions."""
from .benchmark_reporting import build_summary, SUMMARY_FIELDS, _atomic_csv, _counts
from statistics import mean, median
import math

def build_matrix_reports(state):
    identity=state["identity"]
    models=identity["models"]
    items=[]
    rows=[]
    for pid in identity["recordings"]:
        records={m:state["results"].get(m,{}).get(pid,{}) for m in models}
        items.append({"model_results":records})
        for m,r in records.items():
            row={"participant_id":pid,"model_key":m,"status":r.get("status","not_run")}
            for k in ("wer","cer","word_substitutions","word_deletions","word_insertions",
                      "reference_words","char_substitutions","char_deletions","char_insertions",
                      "reference_characters","audio_seconds","inference_seconds","rtf","device","precision","session_id"):
                row[k]=r.get(k) if row["status"]=="completed" else None
            for word,metric,keys in ((True,"wer",("word_substitutions","word_deletions","word_insertions","reference_words")),(False,"cer",("char_substitutions","char_deletions","char_insertions","reference_characters"))):
                if _counts(r,word=word) is None:
                    for k in (*keys,metric):
                        row[k]=None
            for k in ("cleanup_status","cleanup_error","worker_exit_code","worker_log"):
                row[k]=r.get(k)
            resources=r.get("resources") or {} if row["status"]=="completed" else {}
            for k in ("gpu_util_percent_peak","gpu_memory_used_mb_peak","gpu_temperature_c_peak","cpu_percent_peak","ram_used_mb_peak","sample_count","gpu_source","ram_source"):
                row[k]=resources.get(k)
            rows.append(row)
    summary=build_summary({"models":models,"items":items})
    efficiency=[]
    for m in models:
        selected=[r for r in rows if r["model_key"]==m and r["status"]=="completed"]
        valid=[r for r in selected if all(isinstance(r[k],(float,int)) and math.isfinite(r[k]) and r[k]>0 for k in ("audio_seconds","inference_seconds"))]
        times=[r["inference_seconds"]/r["audio_seconds"] for r in valid]
        efficiency.append({"model_key":m,"recordings_timed":len(valid),
            "mean_rtf":mean(times) if times else None,"median_rtf":median(times) if times else None,
            "aggregate_rtf":sum(r["inference_seconds"] for r in valid)/sum(r["audio_seconds"] for r in valid) if valid else None})
    for entry in efficiency:
        selected=[r for r in rows if r["model_key"]==entry["model_key"] and r["status"]=="completed"]
        for k in ("gpu_util_percent_peak","gpu_memory_used_mb_peak","gpu_temperature_c_peak","cpu_percent_peak","ram_used_mb_peak"):
            values=[r[k] for r in selected if isinstance(r[k],(int,float)) and math.isfinite(r[k])]
            entry[k+"_max"]=max(values,default=None)
            entry[k+"_recordings"]=len(values)
    return summary,rows,efficiency

def export_matrix_reporting(directory,state):
    summary,rows,efficiency=build_matrix_reports(state)
    _atomic_csv(directory/"model_summary.csv",SUMMARY_FIELDS,summary)
    if rows:
        _atomic_csv(directory/"recording_results.csv",tuple(rows[0]),rows)
    if efficiency:
        _atomic_csv(directory/"efficiency_summary.csv",tuple(efficiency[0]),efficiency)
