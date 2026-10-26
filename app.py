"""ShuttleStep website: upload a badminton video, get footwork feedback."""

import json
import os
import secrets
import shutil
import socket
import subprocess
import threading
import time
import uuid
from datetime import timedelta

import imageio_ffmpeg
from flask import Flask, abort, redirect, render_template, request, url_for

import analysis
import auth
import charts
import storage
import tracker

BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
RESULTS_DIR = os.path.join(BASE_DIR, "static", "results")
SECRET_KEY_PATH = os.path.join(BASE_DIR, "secret_key.txt")
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".webm"}


def _secret_key():
    if not os.path.exists(SECRET_KEY_PATH):
        with open(SECRET_KEY_PATH, "w") as f:
            f.write(secrets.token_hex(32))
    with open(SECRET_KEY_PATH) as f:
        return f.read().strip()


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 300 * 1024 * 1024  
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=365)
app.secret_key = _secret_key()
storage.setup()
auth.init_app(app)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return {"status": "ok", "service": "ShuttleStep"}


@app.route("/analyze", methods=["POST"])
def analyze():
    started = time.monotonic()
    print(f"[UPLOAD] Request received, content_length={request.content_length}", flush=True)
    video = request.files.get("video")
    print(f"[UPLOAD] Multipart parsed after {time.monotonic() - started:.1f}s", flush=True)
    if not video or not video.filename:
        return render_template("index.html", error="Please choose a video first.")
    extension = os.path.splitext(video.filename)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        return render_template("index.html", error="That file type isn't supported. Please upload an MP4 or MOV video.")

    try:
        height_cm = float(request.form.get("height_cm", ""))
    except ValueError:
        return render_template("index.html", error="Please enter the player's height in centimetres.")
    if not 100 <= height_cm <= 230:
        return render_template("index.html", error="Height should be between 100 and 230 cm.")

    result_id = uuid.uuid4().hex[:12]
    result_dir = os.path.join(RESULTS_DIR, result_id)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(result_dir)
    video_path = os.path.join(UPLOAD_DIR, result_id + extension)
    video.save(video_path)
    print(f"[UPLOAD] Saved file after {time.monotonic() - started:.1f}s", flush=True)
    owner = auth.current_owner()
    _write_status(result_dir, {"state": "working", "owner": owner})
    job = threading.Thread(target=_run_analysis, args=(result_id, video_path, height_cm, video.filename, owner), daemon=True)
    job.start()
    print(f"[UPLOAD] Background job started; redirecting after {time.monotonic() - started:.1f}s", flush=True)
    return redirect(url_for("results", result_id=result_id))


analysis_lock = threading.Lock()


def _run_analysis(result_id, video_path, height_cm, video_name, owner):
    result_dir = os.path.join(RESULTS_DIR, result_id)
    try:
        print(f"[JOB {result_id}] Waiting for analysis slot", flush=True)
        with analysis_lock:
            print(f"[JOB {result_id}] Tracking started", flush=True)
            tracking = tracker.track_video(video_path, os.path.join(result_dir, "replay.mp4"))
            stats, chart_data, tips = analysis.analyze(tracking, height_cm)
            charts.heatmap(chart_data["position_m"], os.path.join(result_dir, "heatmap.png"))
            charts.speed_over_time(chart_data["times"], chart_data["speed"], os.path.join(result_dir, "speed.png"))
            _save_thumbnail(os.path.join(result_dir, "replay.mp4"), os.path.join(result_dir, "thumb.jpg"), stats["duration_s"])
        with open(os.path.join(result_dir, "summary.json"), "w") as f:
            json.dump({"height_cm": height_cm, "stats": stats, "tips": tips}, f)
        storage.save_analysis(result_id, owner, video_name, stats)
        print(f"[JOB {result_id}] Analysis completed", flush=True)
    except ValueError as error:
        print(f"[JOB {result_id}] Invalid video: {error}", flush=True)
        _write_status(result_dir, {"state": "error", "owner": owner, "error": str(error)})
    except Exception:
        print(f"[JOB {result_id}] Unexpected analysis error", flush=True)
        app.logger.exception("Analysis failed for %s", result_id)
        _write_status(result_dir, {"state": "error", "owner": owner, "error": "Something went wrong while analyzing this video. Please try another clip."})
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)


def _write_status(result_dir, status):
    with open(os.path.join(result_dir, "status.json"), "w") as f:
        json.dump(status, f)


@app.route("/results/<result_id>")
def results(result_id):
    if not result_id.isalnum():
        abort(404)
    summary_path = os.path.join(RESULTS_DIR, result_id, "summary.json")
    if not os.path.exists(summary_path):
        return _analysis_progress(result_id)
    _check_owner(result_id)
    with open(summary_path) as f:
        summary = json.load(f)
    files = {name: url_for("static", filename=f"results/{result_id}/{name}") for name in ("replay.mp4", "heatmap.png", "speed.png")}
    return render_template("results.html", stats=summary["stats"], tips=summary["tips"], files=files)


@app.route("/videos")
def videos():
    analyses = storage.list_analyses(auth.current_owner())
    return render_template("videos.html", analyses=analyses)


@app.route("/videos/<result_id>/delete", methods=["POST"])
def delete_video(result_id):
    _check_owner(result_id)
    storage.delete_analysis(result_id)
    shutil.rmtree(os.path.join(RESULTS_DIR, result_id), ignore_errors=True)
    return redirect(url_for("videos"))


def _analysis_progress(result_id):
    status_path = os.path.join(RESULTS_DIR, result_id, "status.json")
    if not os.path.exists(status_path):
        abort(404)
    with open(status_path) as f:
        status = json.load(f)
    if status["owner"] != auth.current_owner():
        abort(404)
    if status["state"] == "error":
        return render_template("index.html", error=status["error"])
    return render_template("analyzing.html")


def _check_owner(result_id):
    row = storage.get_analysis(result_id)
    if row is None or row["owner"] != auth.current_owner():
        abort(404)


def _save_thumbnail(replay_path, thumb_path, duration_s):
    command = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-ss", f"{duration_s / 3:.1f}",
               "-i", replay_path, "-frames:v", "1", "-vf", "scale=480:-2", thumb_path]
    subprocess.run(command, check=False)


@app.errorhandler(413)
def too_large(_):
    return render_template("index.html", error="That video is too big. Please upload a clip under 300 MB (about 2 minutes)."), 413


def _local_network_address():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("8.8.8.8", 80))  
            return s.getsockname()[0]
        except OSError:
            return None


if __name__ == "__main__":
    port = 8000  
    print("\n  ShuttleStep is running!")
    print(f"  On this computer, open:  http://localhost:{port}")
    address = _local_network_address()
    if address:
        print(f"  On your phone (same Wi-Fi), open:  http://{address}:{port}")
    print("  To stop it, close this window or press Ctrl+C.")
    print('  (You can ignore the red "development server" warning below.)\n')
    app.run(host="0.0.0.0", port=port)
