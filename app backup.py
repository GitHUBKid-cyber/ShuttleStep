"""ShuttleStep website: upload a badminton video, get footwork feedback."""

import json
import os
import secrets
import shutil
import socket
import subprocess
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
    """A random key that keeps sign-ins safe. Made once, then kept in secret_key.txt."""
    if not os.path.exists(SECRET_KEY_PATH):
        with open(SECRET_KEY_PATH, "w") as f:
            f.write(secrets.token_hex(32))
    with open(SECRET_KEY_PATH) as f:
        return f.read().strip()


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 300 * 1024 * 1024  # 300 MB upload limit
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=365)
app.secret_key = _secret_key()
storage.setup()
auth.init_app(app)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    video = request.files.get("video")
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

    try:
        tracking = tracker.track_video(video_path, os.path.join(result_dir, "replay.mp4"))
        stats, chart_data, tips = analysis.analyze(tracking, height_cm)
    except ValueError as error:
        return render_template("index.html", error=str(error))
    finally:
        os.remove(video_path)

    charts.heatmap(chart_data["position_m"], os.path.join(result_dir, "heatmap.png"))
    charts.speed_over_time(chart_data["times"], chart_data["speed"], os.path.join(result_dir, "speed.png"))
    _save_thumbnail(os.path.join(result_dir, "replay.mp4"), os.path.join(result_dir, "thumb.jpg"), stats["duration_s"])
    with open(os.path.join(result_dir, "summary.json"), "w") as f:
        json.dump({"height_cm": height_cm, "stats": stats, "tips": tips}, f)
    storage.save_analysis(result_id, auth.current_owner(), video.filename, stats)

    return redirect(url_for("results", result_id=result_id))


@app.route("/results/<result_id>")
def results(result_id):
    if not result_id.isalnum():
        abort(404)
    _check_owner(result_id)
    summary_path = os.path.join(RESULTS_DIR, result_id, "summary.json")
    if not os.path.exists(summary_path):
        abort(404)
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


def _check_owner(result_id):
    """Only the person who uploaded a video can see or delete its results."""
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
    """The address other devices on the same Wi-Fi (like your phone) can use to reach this computer."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("8.8.8.8", 80))  # picks the Wi-Fi connection; nothing is actually sent
            return s.getsockname()[0]
        except OSError:
            return None


if __name__ == "__main__":
    port = 8000  # 5000 is taken by AirPlay on many Macs
    print("\n  ShuttleStep is running!")
    print(f"  On this computer, open:  http://localhost:{port}")
    address = _local_network_address()
    if address:
        print(f"  On your phone (same Wi-Fi), open:  http://{address}:{port}")
    print("  To stop it, close this window or press Ctrl+C.")
    print('  (You can ignore the red "development server" warning below.)\n')
    # 0.0.0.0 lets other devices on your Wi-Fi reach the site, not just this computer.
    app.run(host="0.0.0.0", port=port)
