"""Body tracking: runs MediaPipe Pose on a video and draws the skeleton replay."""

import os
import subprocess

import cv2
import imageio_ffmpeg
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "pose_landmarker_full.task")

TARGET_FPS = 15
MAX_WIDTH = 960

CONNECTIONS = [(c.start, c.end) for c in vision.PoseLandmarksConnections.POSE_LANDMARKS]


def track_video(video_path, replay_path):
    """Find the player's 33 body points in each sampled frame and save a skeleton replay.

    Returns a dict with:
      landmarks: array (frames, 33, 4) of x, y (0-1, relative to the frame), z, visibility; NaN where no player was found
      world: array (frames, 33, 3) of the same points in metres around the hips, used for joint angles
      times: seconds from the start of the video for each sampled frame
      fps, width, height: of the sampled video
    """
    source_fps, width, height = _probe(video_path)
    step = max(1, round(source_fps / TARGET_FPS))
    fps = source_fps / step
    reader = _start_reader(video_path, step, width, height)
    writer = _start_writer(replay_path, width, height, fps)
    frame_size = width * height * 3

    options = vision.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
    )

    landmarks, world, times = [], [], []
    frame_index = 0
    with vision.PoseLandmarker.create_from_options(options) as landmarker:
        while True:
            data = reader.stdout.read(frame_size)
            if len(data) < frame_size:
                break
            frame = np.frombuffer(data, np.uint8).reshape(height, width, 3).copy()

            timestamp_ms = int(frame_index * step * 1000 / source_fps)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp_ms)

            if result.pose_landmarks:
                points = np.array([[p.x, p.y, p.z, p.visibility] for p in result.pose_landmarks[0]])
                world_points = np.array([[p.x, p.y, p.z] for p in result.pose_world_landmarks[0]])
                _draw_skeleton(frame, points)
            else:
                points = np.full((33, 4), np.nan)
                world_points = np.full((33, 3), np.nan)

            landmarks.append(points)
            world.append(world_points)
            times.append(timestamp_ms / 1000)
            writer.stdin.write(frame.tobytes())
            frame_index += 1

    reader.stdout.close()
    reader.wait()
    writer.stdin.close()
    writer.wait()
    if not landmarks:
        raise ValueError("This video has no frames we could read.")

    return {
        "landmarks": np.array(landmarks),
        "world": np.array(world),
        "times": np.array(times),
        "fps": fps,
        "width": width,
        "height": height,
    }


def _probe(video_path):
    """Read the frame rate and the (upright, shrunk) frame size from the video's first frame."""
    cap = cv2.VideoCapture(video_path)
    ok, frame = cap.read() if cap.isOpened() else (False, None)
    source_fps = cap.get(cv2.CAP_PROP_FPS) or 30
    cap.release()
    if not ok:
        raise ValueError("Could not open this video. Try an MP4 or MOV file.")
    height, width = frame.shape[:2]
    if width > MAX_WIDTH:
        width, height = MAX_WIDTH, int(height * MAX_WIDTH / width) // 2 * 2
    return source_fps, width, height


def _start_reader(path, step, width, height):
    """Decode the video with ffmpeg, keeping every step-th frame at our size.

    ffmpeg decodes on all processor cores, and runs alongside MediaPipe, so this is much faster than OpenCV.
    """
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-i", path,
        "-vf", f"select=not(mod(n\\,{step})),scale={width}:{height}:flags=area", "-fps_mode", "passthrough",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-",
    ]
    return subprocess.Popen(command, stdout=subprocess.PIPE)


def _start_writer(path, width, height, fps):
    """Pipe frames into ffmpeg so the replay is an H.264 MP4 that plays in every browser."""
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{width}x{height}", "-r", f"{fps:.3f}", "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        path,
    ]
    return subprocess.Popen(command, stdin=subprocess.PIPE)


def _draw_skeleton(frame, points):
    height, width = frame.shape[:2]
    xy = [(int(x * width), int(y * height)) for x, y in points[:, :2]]
    for start, end in CONNECTIONS:
        if points[start, 3] > 0.5 and points[end, 3] > 0.5:
            cv2.line(frame, xy[start], xy[end], (80, 220, 120), 2, cv2.LINE_AA)
    for i, (x, y) in enumerate(xy):
        if points[i, 3] > 0.5:
            cv2.circle(frame, (x, y), 3, (255, 255, 255), -1, cv2.LINE_AA)
