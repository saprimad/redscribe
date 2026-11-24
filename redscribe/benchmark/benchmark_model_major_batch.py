"""Experimental local model-major batch entry point; not wired into desktop UI."""
from pathlib import Path
from uuid import uuid4
from .benchmark_dataset import verify_dataset
from .benchmark_reference import verify_reference, sha256_file
from .benchmark_fast_metrics import raw_wer_fast as raw_wer, raw_cer_fast as raw_cer, ENGINE
from importlib.metadata import version
from .benchmark_matrix_checkpoint import MatrixCheckpoint
from .benchmark_model_major import run_model_major

def run_model_major_batch(dataset_path, models, output, *, language="ms",
                          session_factory=None, stopped=lambda:False, duration_check=None,
                          warmup_audio=None, monitor_factory=None):
    dataset = verify_dataset(dataset_path)
    models = list(models)
    if not models or len(set(models)) != len(models):
        raise ValueError("Select distinct models")
    pairs = {p["participant_id"]:p for p in dataset["pairs"]}
    if duration_check is None:
        from .benchmark_pilot import _decode_duration
        duration_check = _decode_duration
    durations = {pid:duration_check(p["audio"]) for pid,p in pairs.items()}
    output = Path(output).resolve()
    output.mkdir(parents=True,exist_ok=True)
    identity = {"models":models,"recordings":list(pairs),"dataset":dataset,
                "language":language,"policy":"raw-v1-cuda-fp16","scoring_engine":ENGINE,
                "rapidfuzz_version":version("rapidfuzz")}
    warmup_path = Path(warmup_audio).resolve() if warmup_audio else None
    if warmup_path:
        warmup_hash = sha256_file(warmup_path)
        if warmup_hash in {p["audio_sha256"] for p in pairs.values()}:
            raise ValueError("Warm-up must not use study audio")
        identity["warmup_sha256"] = warmup_hash
    identity["resource_monitoring"] = monitor_factory is not None
    matrix = MatrixCheckpoint(output/"matrix.json",identity)

    def reference(pid):
        p = pairs[pid]
        if sha256_file(p["audio"]) != p["audio_sha256"] or sha256_file(p["reference_manifest"]) != p["reference_manifest_sha256"]:
            raise ValueError("Dataset changed")
        refpath = Path(p["reference_manifest"])
        ref = verify_reference(refpath)
        return (refpath.parent/ref["scoring_text_file"]).read_bytes().decode("utf-8")

    def scores(ref,pred):
        return {"wer":raw_wer(ref,pred).rate,"cer":raw_cer(ref,pred).rate}

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
        return {"prediction":pred,"device":session.device,"precision":session.precision,"resources":resources}

    def save(model,pid,row):
        if row["status"]=="completed":
            result = row.pop("result")
            path = output/(uuid4().hex+".txt")
            with path.open("xb") as f:
                f.write(result.pop("prediction").encode("utf-8"))
            pred = path.read_bytes().decode("utf-8")
            row.update(result, prediction_file=path.name,prediction_sha256=sha256_file(path),
                       audio_seconds=durations[pid],rtf=row["inference_seconds"]/durations[pid],**scores(reference(pid),pred))
        matrix.record(model,pid,row)

    def verified(model,pid,row):
        try:
            path = (output/row["prediction_file"]).resolve()
            if path.parent != output or sha256_file(path)!=row["prediction_sha256"]:
                return False
            return all(row[k]==v for k,v in scores(reference(pid),path.read_bytes().decode("utf-8")).items())
        except (OSError,ValueError,KeyError):
            return False

    def open_session(key):
        if session_factory is not None:
            return session_factory(key)
        from asr_backends import EXTRA_MODELS
        from model_options import preflight_model
        preflight_model(key,language)
        if key in EXTRA_MODELS:
            from .benchmark_local_session import LocalBenchmarkSession
            return LocalBenchmarkSession(key,language)
        from .benchmark_whisper_session import WhisperSession
        return WhisperSession(key,language)

    def warmup(session):
        if sha256_file(warmup_path) != identity["warmup_sha256"]:
            raise ValueError("Warm-up audio changed")
        session.transcribe(str(warmup_path))

    run_model_major(models,pairs,open_model=open_session,infer=infer,
        close_model=lambda s:s.close(),checkpoint=save,stopped=stopped,
        is_verified=lambda m,p:matrix.verified(m,p,verified),
        warmup=warmup if warmup_path else None)
    return matrix.state
