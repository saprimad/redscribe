"""Experimental local model-major batch entry point; not wired into desktop UI."""
from pathlib import Path
import math
from uuid import uuid4
from .benchmark_dataset import verify_dataset
from .benchmark_reference import verify_reference, sha256_file
from .benchmark_fast_metrics import raw_wer_fast as raw_wer, raw_cer_fast as raw_cer, ENGINE
from importlib.metadata import version
from .benchmark_matrix_checkpoint import MatrixCheckpoint
from .benchmark_model_major import run_model_major

MAX_FULL_AUDIO_SECONDS = 7200

def validate_duration(seconds):
    if not math.isfinite(seconds) or not 0 < seconds <= MAX_FULL_AUDIO_SECONDS:
        raise ValueError(f'Full-length audio must be between 0 and {MAX_FULL_AUDIO_SECONDS} seconds; got {seconds}')
    return seconds

def decode_full_duration(path):
    from faster_whisper.audio import decode_audio
    waveform = decode_audio(str(path), sampling_rate=16000)
    return validate_duration(len(waveform) / 16000)

def _run_model_major_batch(dataset_path, models, output, *, language="ms",
                          session_factory=None, stopped=lambda:False, duration_check=None,
                          warmup_audio=None, monitor_factory=None, progress=lambda *args: None):
    progress('Startup',None,'Verifying approved dataset and reference integrity')
    dataset = verify_dataset(dataset_path)
    models = list(models)
    if not models or len(set(models)) != len(models):
        raise ValueError("Select distinct models")
    pairs = {p["participant_id"]:p for p in dataset["pairs"]}
    if duration_check is None:
        duration_check = decode_full_duration
    durations = {}
    for index,(pid,p) in enumerate(pairs.items(),1):
        progress("Startup",None,f"Decoding audio duration {index}/{len(pairs)}")
        durations[pid]=validate_duration(duration_check(p["audio"]))
    output = Path(output).resolve()
    output.mkdir(parents=True,exist_ok=True)
    identity = {"models":models,"recordings":list(pairs),"dataset":dataset,
                "language":language,"policy":"raw-v1-cuda-fp16","scoring_engine":ENGINE,
                "rapidfuzz_version":version("rapidfuzz"),"max_audio_seconds":MAX_FULL_AUDIO_SECONDS,"reporting_schema":1}
    from .benchmark_provenance import runtime_provenance, hardware_provenance
    progress("Startup",None,"Collecting runtime provenance")
    identity["runtime_provenance"] = runtime_provenance()
    progress("Startup",None,"Collecting hardware and CUDA provenance")
    identity["hardware_provenance"] = hardware_provenance() if session_factory is None else None
    identity["requested_device"] = "cuda"
    identity["requested_precision"] = "float16"
    identity["inference_kind"] = "native" if session_factory is None else "injected"
    warmup_path = Path(warmup_audio).resolve() if warmup_audio else None
    if warmup_path:
        warmup_hash = sha256_file(warmup_path)
        if warmup_hash in {p["audio_sha256"] for p in pairs.values()}:
            raise ValueError("Warm-up must not use study audio")
        identity["warmup_sha256"] = warmup_hash
    identity["resource_monitoring"] = monitor_factory is not None
    progress("Startup",None,"Initialising checkpoint")
    matrix = MatrixCheckpoint(output/"matrix.json",identity)
    # A prior export manifest must not certify a new or interrupted run.
    (output/'export_integrity.json').unlink(missing_ok=True)

    def reference(pid):
        p = pairs[pid]
        if sha256_file(p["audio"]) != p["audio_sha256"] or sha256_file(p["reference_manifest"]) != p["reference_manifest_sha256"]:
            raise ValueError("Dataset changed")
        refpath = Path(p["reference_manifest"])
        ref = verify_reference(refpath)
        return (refpath.parent/ref["scoring_text_file"]).read_bytes().decode("utf-8")

    def scores(ref,pred):
        w,c = raw_wer(ref,pred),raw_cer(ref,pred)
        return {"wer":w.rate,"cer":c.rate,
                "word_substitutions":w.substitutions,"word_deletions":w.deletions,
                "word_insertions":w.insertions,"reference_words":w.reference_units,
                "char_substitutions":c.substitutions,"char_deletions":c.deletions,
                "char_insertions":c.insertions,"reference_characters":c.reference_units}

    def infer(session,pid):
        ref = reference(pid)
        resources = None
        if monitor_factory is None:
            pred = session.transcribe(pairs[pid]["audio"])
        else:
            with monitor_factory() as monitor:
                pred = session.transcribe(pairs[pid]["audio"])
            resources = monitor.summary()
        if reference(pid) != ref:
            raise ValueError("Reference changed during inference")
        return {"prediction":pred,"device":session.device,"precision":session.precision,"resources":resources,
                "model_provenance":getattr(session,"provenance",None)}

    def save(model,pid,row):
        if row["status"]=="completed":
            result = row.pop("result")
            path = output/(uuid4().hex+".txt")
            payload = result.pop("prediction").encode("utf-8")
            try:
                with path.open("xb") as f:
                    f.write(payload)
                    f.flush()
                    import os
                    os.fsync(f.fileno())
                if path.read_bytes() != payload:
                    raise OSError("Prediction read-back mismatch")
            except BaseException:
                path.unlink(missing_ok=True)
                raise
            pred = payload.decode("utf-8")
            row.update(result, prediction_file=path.name,prediction_sha256=sha256_file(path),
                       audio_seconds=durations[pid],rtf=row["inference_seconds"]/durations[pid],**scores(reference(pid),pred))
        matrix.record(model,pid,row)
        progress(model,pid,row['status'])

    def verified(model,pid,row):
        try:
            path = (output/row["prediction_file"]).resolve()
            if path.parent != output or sha256_file(path)!=row["prediction_sha256"]:
                return False
            return all(row[k]==v for k,v in scores(reference(pid),path.read_bytes().decode("utf-8")).items())
        except (OSError,ValueError,KeyError):
            return False

    def create_session(key):
        if session_factory is not None:
            return session_factory(key)
        from .benchmark_isolated_session import IsolatedSession
        return IsolatedSession(key, language, output / ("asr-worker-" + uuid4().hex + ".log"))

    def open_session(key):
        session = create_session(key)
        try:
            previous = [row for row in matrix.state["results"].get(key,{}).values()
                        if row.get("status") == "completed"]
            for row in previous:
                if (row.get("model_provenance") != getattr(session,"provenance",None)
                    or row.get("device") != session.device
                    or row.get("precision") != session.precision):
                    raise ValueError("Resume model provenance mismatch; use a new output directory")
            return session
        except BaseException:
            session.close()
            raise

    def warmup(session):
        if sha256_file(warmup_path) != identity["warmup_sha256"]:
            raise ValueError("Warm-up audio changed")
        session.transcribe(str(warmup_path))

    progress('Startup',None,'Checking saved benchmark cells')
    verified_cells=set()
    for m in models:
        for p in pairs:
            if stopped():
                break
            if matrix.verified(m,p,verified):
                verified_cells.add((m,p))
                progress(m,p,'completed')
            else:
                progress(m,p,'pending')
    def close_session(session):
        session.close()
        error = getattr(session, "cleanup_error", None)
        model = (getattr(session, "provenance", None) or {}).get("model_key", "ASR")
        if session_factory is None:
            for pid, row in list(matrix.state["results"].get(model, {}).items()):
                if row.get("status") == "completed" and (model,pid) not in verified_cells:
                    matrix.record(model,pid,dict(row,
                        cleanup_status="failed" if error else "completed",
                        cleanup_error=error,
                        shutdown_strategy=session.shutdown_strategy,
                        worker_exit_code=session.process.exitcode,
                        worker_log=session.log_path.name))
        if error:
            progress(model, None, "cleanup_failed; verified predictions retained")
    run_model_major(models,pairs,open_model=open_session,infer=infer,
        close_model=close_session,checkpoint=save,stopped=stopped,
        is_verified=lambda m,p:(m,p) in verified_cells and matrix.verified(m,p,verified),
        warmup=warmup if warmup_path else None,progress=progress)
    # Never export stale completed cells after cancellation or failed verification.
    for m in models:
        for p in pairs:
            row=matrix.state['results'].get(m,{}).get(p,{})
            if row.get('status')=='completed' and not verified(m,p,row):
                matrix.record(m,p,{'status':'failed','stage':'integrity','error':'Saved prediction or score failed verification'})
                progress(m,p,'failed')
    from .benchmark_matrix_reporting import export_matrix_reporting
    progress("Reporting", None, "CSV export")
    export_matrix_reporting(output,matrix.state)
    from .benchmark_publication import export_publication
    progress("Reporting", None, "Excel and figures")
    export_publication(output,matrix.state)
    from .benchmark_export_integrity import write_export_manifest
    progress("Reporting", None, "Export integrity manifest")
    write_export_manifest(output)
    return matrix.state


def run_model_major_batch(dataset_path,models,output,**kwargs):
    from .benchmark_output_lock import output_lock
    with output_lock(output):
        return _run_model_major_batch(dataset_path,models,output,**kwargs)
