"""Charts for the results page, drawn as PNG pictures with Matplotlib."""

import matplotlib

matplotlib.use("Agg")  
import matplotlib.pyplot as plt
import numpy as np

GREEN = "#1f9d55"
TEXT = "#1c2420"
MUTED = "#5d6a63"
GRID = "#e3e8e5"


def heatmap(position_m, path):
    """Where the player spent their time, seen from above with the net at the top."""
    pos = position_m[~np.isnan(position_m[:, 0])]
    x, y = pos[:, 0], -pos[:, 1]  
    reach = float(np.clip(np.percentile(np.abs(pos), 98) + 0.3, 2.0, 4.0))

    fig, ax = plt.subplots(figsize=(4.2, 4.6), dpi=150)
    counts, _, _ = np.histogram2d(x, y, bins=20, range=[[-reach, reach], [-reach, reach]])
    image = ax.imshow(np.sqrt(counts.T), origin="lower", extent=[-reach, reach, -reach, reach], cmap="YlOrRd", interpolation="bicubic", aspect="equal")
    ax.plot(0, 0, marker="+", color=TEXT, markersize=14, markeredgewidth=2)
    ax.annotate("base", (0, 0), xytext=(6, 6), textcoords="offset points", color=TEXT, fontsize=11)
    ax.set_title("Net", color=MUTED, fontsize=12, pad=6)
    ax.set_xlabel("Back of court", color=MUTED, fontsize=12)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color(GRID)
    key = fig.colorbar(image, ax=ax, orientation="horizontal", fraction=0.04, pad=0.1, ticks=[])
    key.outline.set_visible(False)
    key.ax.set_xlabel("less time  ←  time spent  →  more time", color=MUTED, fontsize=10)
    fig.tight_layout()
    fig.savefig(path, transparent=False, facecolor="white")
    plt.close(fig)


def speed_over_time(times, speed, path):
    fig, ax = plt.subplots(figsize=(5.2, 2.6), dpi=150)
    ax.fill_between(times, np.nan_to_num(speed), color=GREEN, alpha=0.25, linewidth=0)
    ax.plot(times, speed, color=GREEN, linewidth=1.4)
    ax.set_xlabel("Time in video (s)", color=MUTED, fontsize=11)
    ax.set_ylabel("Speed (m/s)", color=MUTED, fontsize=11)
    ax.set_xlim(times[0], times[-1])
    ax.set_ylim(bottom=0)
    ax.tick_params(colors=MUTED, labelsize=10)
    ax.grid(axis="y", color=GRID)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    fig.tight_layout()
    fig.savefig(path, facecolor="white")
    plt.close(fig)
