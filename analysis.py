"""Footwork analysis: turns tracked body points into stats and feedback tips."""

import warnings

import numpy as np

# MediaPipe body point numbers.
NOSE = 0
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
LEFT_HIP, RIGHT_HIP = 23, 24
LEFT_KNEE, RIGHT_KNEE = 25, 26
LEFT_ANKLE, RIGHT_ANKLE = 27, 28
LEFT_HEEL, RIGHT_HEEL = 29, 30
FEET = [LEFT_ANKLE, RIGHT_ANKLE, LEFT_HEEL, RIGHT_HEEL]

# The nose sits at about 91% of a person's standing height.
NOSE_HEIGHT_RATIO = 0.91
# The hip joints sit at about 50% of standing height, measured to the ankles and heels.
HIP_HEIGHT_RATIO = 0.50
# How wide a phone's main camera sees in landscape video (about 68 degrees on most phones).
CAMERA_FOV_DEGREES = 68
# Gaps in tracking shorter than this are filled in; longer gaps stay empty.
MAX_GAP_S = 0.5
# Foot movement slower than this is treated as standing still (tracking wobble).
MOVING_SPEED = 0.5  # metres per second
# Even elite players rarely pass this, so faster jumps are tracking errors (e.g. switching to another person).
MAX_SPEED = 7.0  # metres per second
# A move away from base further than this counts as a footwork movement.
MOVE_DISTANCE = 0.8  # metres
# The player has recovered once back within this distance of base.
RECOVERED_DISTANCE = 0.5  # metres
# Taking longer than this to get back means the rally ended (walking to pick up the shuttle), not slow footwork.
MAX_RECOVERY_S = 3.0
# Knee bends deeper than this, with the feet far apart, count as a lunge.
LUNGE_KNEE_ANGLE = 120  # degrees
LUNGE_STANCE = 0.45  # feet apart, as a share of the player's height


def analyze(tracking, height_cm):
    landmarks = tracking["landmarks"]
    world = tracking["world"]
    times = tracking["times"]
    width, height = tracking["width"], tracking["height"]
    height_m = height_cm / 100

    pixels = landmarks[:, :, :2] * [width, height]
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        feet = _fill_gaps(np.nanmean(pixels[:, FEET], axis=1), times)
        hips = _fill_gaps(np.nanmean(pixels[:, [LEFT_HIP, RIGHT_HIP]], axis=1), times)
    nose = _fill_gaps(pixels[:, NOSE], times)
    tracked = ~np.isnan(feet[:, 0])
    if tracked.sum() < 10:
        raise ValueError("We couldn't find a player in this video. Make sure their whole body is in view.")


    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        from_nose = np.linalg.norm(feet - nose, axis=1) / NOSE_HEIGHT_RATIO
        from_nose[nose[:, 1] < 0.02 * height] = np.nan
        from_hips = np.linalg.norm(feet - hips, axis=1) / HIP_HEIGHT_RATIO
        body_px = np.fmax(from_nose, from_hips)
    body_px = _rolling_percentile(body_px, times, window_s=1.5, q=90)

    focal_px = (width / 2) / np.tan(np.radians(CAMERA_FOV_DEGREES / 2))
    depth = focal_px * height_m / body_px
    side = (feet[:, 0] - width / 2) * depth / focal_px
    ground = _smooth(np.column_stack([side, depth]), times, window_s=0.4)

    step = np.linalg.norm(np.diff(ground, axis=0), axis=1)
    dt = np.diff(times)
    speed = np.where(dt > 0, step / dt, np.nan)
    jumps = speed > MAX_SPEED
    speed[jumps] = np.nan
    step[jumps] = np.nan
    speed = _smooth(speed[:, None], times[1:])[:, 0]
    moving = speed > MOVING_SPEED

    distance_m = float(np.nansum(np.where(moving, step, 0)))
    moving_time = float(np.nansum(np.where(moving, dt, 0)))
    duration = float(times[-1] - times[0]) or 1

    base = np.nanmedian(ground, axis=0)
    position_m = (ground - base) * [1, -1]

    zones = _zone_shares(position_m)
    moves = _find_moves(position_m, times)
    lunges = _find_lunges(world, times, height_m)
    stance_ratio = _base_stance(world, position_m)

    stats = {
        "duration_s": round(duration, 1),
        "tracked_pct": round(float(tracked.mean()) * 100),
        "distance_m": round(distance_m, 1),
        "avg_speed": round(distance_m / moving_time, 2) if moving_time else 0,
        "top_speed": round(float(np.nanpercentile(speed, 97)), 2) if np.any(moving) else 0,
        "moving_pct": round(moving_time / duration * 100),
        "zones": zones,
        "moves": len(moves),
        "recovery_s": _mean([m["recovery_s"] for m in moves if m["recovery_s"] is not None]),
        "recovery_by_direction": _recovery_by_direction(moves),
        "lunges": len(lunges),
        "lunge_knee_angle": _mean([l["knee_angle"] for l in lunges]),
        "stance_ratio": stance_ratio,
    }
    chart_data = {"times": times, "speed": np.concatenate([[0], speed]), "position_m": position_m}
    return stats, chart_data, feedback(stats)


def feedback(stats):
    tips = []

    recovery = stats["recovery_s"]
    if recovery is not None:
        if recovery > 1.5:
            tips.append(("work", f"Recovery to base averages {recovery} s. Push back to the centre straight after each shot so you're ready earlier."))
        elif recovery < 1.0:
            tips.append(("good", f"Fast recovery: you get back to base in {recovery} s on average."))

    by_direction = stats["recovery_by_direction"]
    if len(by_direction) >= 2:
        slowest = max(by_direction, key=by_direction.get)
        fastest = min(by_direction, key=by_direction.get)
        if by_direction[slowest] - by_direction[fastest] > 0.4:
            tips.append(("work", f"Recovery is slowest after moves to the {slowest} ({by_direction[slowest]} s vs {by_direction[fastest]} s to the {fastest}). Drill that corner."))

    angle = stats["lunge_knee_angle"]
    if stats["lunges"] and angle is not None:
        if angle > 105:
            tips.append(("work", f"Your lunges are shallow (knee at {angle:.0f}° on average). Bend the front knee closer to 90° to reach low shots."))
        elif angle < 75:
            tips.append(("work", f"Your lunges are very deep (knee at {angle:.0f}°). Keep the front knee above the ankle to protect it."))
        else:
            tips.append(("good", f"Good lunge depth: your front knee bends to about {angle:.0f}°."))

    zones = stats["zones"]
    if zones["back"] > 50:
        tips.append(("work", f"You spend {zones['back']}% of the time near the back. Check your base isn't too deep, so you can reach the net in time."))
    if zones["front"] > 50:
        tips.append(("work", f"You spend {zones['front']}% of the time near the front. Your base may be too close to the net."))
    if abs(zones["left"] - zones["right"]) > 30:
        heavy = "left" if zones["left"] > zones["right"] else "right"
        tips.append(("work", f"Your movement leans to the {heavy} side ({zones[heavy]}% of the time). Practise moving evenly to both sides."))

    stance = stats["stance_ratio"]
    if stance is not None:
        if stance < 1.0:
            tips.append(("work", "Your ready stance is narrow. Set your feet a little wider than your shoulders between shots for a faster first step."))
        else:
            tips.append(("good", "Solid ready stance: your feet are wider than your shoulders at base."))

    if stats["top_speed"] >= 3:
        tips.append(("good", f"Explosive movement: your top speed reached {stats['top_speed']} m/s."))

    if stats["moving_pct"] < 25:
        tips.append(("work", f"You're moving only {stats['moving_pct']}% of the time. Stay light on your feet with small steps between shots."))

    if not tips:
        tips.append(("good", "Balanced footwork across the court. Keep it up!"))
    return tips


def _fill_gaps(points, times):
    points = points.copy()
    found = ~np.isnan(points[:, 0])
    if found.sum() < 2:
        return points
    found_idx = np.flatnonzero(found)
    for a, b in zip(found_idx[:-1], found_idx[1:]):
        if b - a > 1 and times[b] - times[a] <= MAX_GAP_S:
            for col in range(points.shape[1]):
                points[a + 1:b, col] = np.interp(times[a + 1:b], [times[a], times[b]], [points[a, col], points[b, col]])
    return points


def _smooth(values, times, window_s=0.3):
    if len(times) < 2:
        return values
    dt = np.median(np.diff(times))
    half = max(1, int(round(window_s / dt / 2)))
    smoothed = np.full_like(values, np.nan)
    for i in range(len(values)):
        if np.isnan(values[i, 0]):
            continue
        smoothed[i] = np.nanmean(values[max(0, i - half):i + half + 1], axis=0)
    return smoothed


def _rolling_percentile(values, times, window_s, q):
    dt = np.median(np.diff(times)) if len(times) > 1 else 1
    half = max(1, int(round(window_s / dt / 2)))
    out = np.full(len(values), np.nan)
    for i in range(len(values)):
        window = values[max(0, i - half):i + half + 1]
        if np.any(~np.isnan(window)):
            out[i] = np.nanpercentile(window, q)
    out[np.isnan(out)] = np.nanpercentile(values, q)
    return out


def _zone_shares(position_m):
    pos = position_m[~np.isnan(position_m[:, 0])]
    x, y = pos[:, 0], pos[:, 1]
    lo, hi = np.percentile(y, [2, 98])
    third = (hi - lo) / 3 or 1
    front = y < lo + third
    back = y > hi - third
    shares = {
        "front": front.mean(),
        "middle": (~front & ~back).mean(),
        "back": back.mean(),
        "left": (x < np.mean(np.percentile(x, [2, 98]))).mean(),
        "right": (x >= np.mean(np.percentile(x, [2, 98]))).mean(),
    }
    return {k: round(float(v) * 100) for k, v in shares.items()}


def _find_moves(position_m, times):
    distance = np.linalg.norm(position_m, axis=1)
    moves = []
    i = 0
    n = len(distance)
    while i < n:
        if not distance[i] > MOVE_DISTANCE:
            i += 1
            continue
        start = i
        while i < n and not distance[i] < RECOVERED_DISTANCE:
            i += 1
        segment = distance[start:i]
        peak = start + int(np.nanargmax(segment))
        recovery = float(times[i] - times[peak]) if i < n else None
        if recovery is not None and recovery > MAX_RECOVERY_S:
            recovery = None
        x, y = position_m[peak]
        if abs(y) > abs(x):
            direction = "front" if y < 0 else "back"
        else:
            direction = "left" if x < 0 else "right"
        moves.append({"peak_time": float(times[peak]), "direction": direction, "recovery_s": recovery})
    return moves


def _recovery_by_direction(moves):
    grouped = {}
    for move in moves:
        if move["recovery_s"] is not None:
            grouped.setdefault(move["direction"], []).append(move["recovery_s"])
    return {direction: _mean(values) for direction, values in grouped.items() if len(values) >= 2}


def _knee_angle(world, hip, knee, ankle):
    a = world[:, hip] - world[:, knee]
    b = world[:, ankle] - world[:, knee]
    cos = np.sum(a * b, axis=1) / (np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1))
    return np.degrees(np.arccos(np.clip(cos, -1, 1)))


def _find_lunges(world, times, height_m):
    left = _knee_angle(world, LEFT_HIP, LEFT_KNEE, LEFT_ANKLE)
    right = _knee_angle(world, RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE)
    knee = np.fmin(left, right)
    leg = np.nanmedian(np.linalg.norm(world[:, LEFT_HIP] - world[:, LEFT_ANKLE], axis=1))
    stance = np.linalg.norm(world[:, LEFT_ANKLE] - world[:, RIGHT_ANKLE], axis=1) / (leg / 0.53)
    in_lunge = (knee < LUNGE_KNEE_ANGLE) & (stance > LUNGE_STANCE)

    lunges = []
    i = 0
    while i < len(in_lunge):
        if not in_lunge[i]:
            i += 1
            continue
        start = i
        while i < len(in_lunge) and in_lunge[i]:
            i += 1
        if times[i - 1] - times[start] >= 0.1 or i - start >= 2:
            lunges.append({"time": float(times[start]), "knee_angle": float(np.nanmin(knee[start:i]))})
    return lunges


def _base_stance(world, position_m):
    at_base = np.linalg.norm(position_m, axis=1) < RECOVERED_DISTANCE
    if at_base.sum() < 5:
        return None
    feet = np.linalg.norm(world[at_base, LEFT_ANKLE] - world[at_base, RIGHT_ANKLE], axis=1)
    shoulders = np.linalg.norm(world[at_base, LEFT_SHOULDER] - world[at_base, RIGHT_SHOULDER], axis=1)
    ratio = np.nanmedian(feet / shoulders)
    return None if np.isnan(ratio) else round(float(ratio), 2)


def _mean(values):
    values = [v for v in values if v is not None]
    return round(float(np.mean(values)), 2) if values else None
