"""
Video composition script. This is the single file the agent modifies.

Contains:
- Composition config (JSON-serializable)
- ffmpeg rendering pipeline
- Scene/transition/Ken Burns definitions

Usage: python3 compose.py
Output: outputs/latest.mp4 + metrics printed to stdout

This script is the "train.py" of video compositor research.
The agent modifies the config values and rendering logic to improve quality.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Project paths (relative to this script)
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent
CLIPS_DIR = SCRIPT_DIR / "clips"
KB_DIR = SCRIPT_DIR / "kb-clips"
OUTPUTS_DIR = SCRIPT_DIR / "outputs"
EVAL_DIR = SCRIPT_DIR / "eval-frames"

# Source videos (醉山河 project)
SOURCE_DIR = Path.home() / ".openclaw/workspace/projects/zuishanhe-baijiu"

# ---------------------------------------------------------------------------
# Composition Config — THIS IS WHAT THE AGENT TUNES
# ---------------------------------------------------------------------------

COMPOSITION = {
    "scenes": [
        {
            "file": str(SOURCE_DIR / "videos-30fps/scene_00.mp4"),
            "trimStart": 0.8,
            "trimEnd": 4.6,
            "voiceover": str(SOURCE_DIR / "audio/voiceover_00.mp3"),
            "voDelay": 0.3,
            "zoomStart": 1.0,
            "zoomEnd": 1.06,
        },
        {
            "file": str(SOURCE_DIR / "videos-30fps/scene_01.mp4"),
            "trimStart": 1.0,
            "trimEnd": 4.8,
            "voiceover": str(SOURCE_DIR / "audio/voiceover_01.mp3"),
            "voDelay": 0.3,
            "zoomStart": 1.0,
            "zoomEnd": 1.10,
        },
        {
            "file": str(SOURCE_DIR / "videos-30fps/scene_02.mp4"),
            "trimStart": 2.8,
            "trimEnd": 6.8,
            "voiceover": str(SOURCE_DIR / "audio/voiceover_02.mp3"),
            "voDelay": 0.3,
            "zoomStart": 1.0,
            "zoomEnd": 1.12,
        },
        {
            "file": str(SOURCE_DIR / "videos-30fps/scene_03.mp4"),
            "trimStart": 4.8,
            "trimEnd": 7.6,
            "voiceover": str(SOURCE_DIR / "audio/voiceover_03.mp3"),
            "voDelay": 0.3,
            "zoomStart": 1.08,
            "zoomEnd": 1.0,
        },
        {
            "file": str(SOURCE_DIR / "videos-30fps/scene_04.mp4"),
            "trimStart": 2.8,
            "trimEnd": 7.8,
            "voiceover": str(SOURCE_DIR / "audio/voiceover_04.mp3"),
            "voDelay": 0.3,
            "zoomStart": 1.0,
            "zoomEnd": 1.16,
        },
        {
            "file": str(SOURCE_DIR / "videos-30fps/scene_05.mp4"),
            "trimStart": 4.8,
            "trimEnd": 7.8,
            "voiceover": str(SOURCE_DIR / "audio/voiceover_05.mp3"),
            "voDelay": 0.3,
            "zoomStart": 1.06,
            "zoomEnd": 1.0,
        },
        {
            "file": str(SOURCE_DIR / "videos-30fps/scene_06.mp4"),
            "trimStart": 0.6,
            "trimEnd": 3.2,
            "voiceover": str(SOURCE_DIR / "audio/voiceover_06.mp3"),
            "voDelay": 0.3,
            "zoomStart": 1.0,
            "zoomEnd": 1.10,
        },
        {
            "file": str(SOURCE_DIR / "videos-30fps/scene_07.mp4"),
            "trimStart": 0.8,
            "trimEnd": 3.2,
            "voiceover": str(SOURCE_DIR / "audio/voiceover_07.mp3"),
            "voDelay": 0.3,
            "zoomStart": 1.0,
            "zoomEnd": 1.08,
        },
        {
            "file": str(SOURCE_DIR / "videos-30fps/scene_08.mp4"),
            "trimStart": 2.0,
            "trimEnd": 6.5,
            "voiceover": str(SOURCE_DIR / "audio/voiceover_08.mp3"),
            "voDelay": 0.3,
            "zoomStart": 1.0,
            "zoomEnd": 1.15,
        },
    ],
    "transitions": [
        {"type": "dissolve",   "duration": 0.8},
        {"type": "wipeleft",   "duration": 0.8},
        {"type": "wiperight",  "duration": 0.8},
        {"type": "fadeblack",  "duration": 0.8},
        {"type": "fadeblack",  "duration": 0.8},
        {"type": "circlecrop", "duration": 0.8},
        {"type": "dissolve",   "duration": 0.8},
        {"type": "fadeblack",  "duration": 0.8},
    ],
    "bgm": {
        "file": str(SOURCE_DIR / "audio/bgm.mp3"),
        "volume": 0.25,
        "fadeIn": 2.0,
        "fadeOut": 3.0,
    },
    "output": {
        "width": 1080,
        "height": 1920,
        "crf": 18,
        "fps": 30,
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_duration(file_path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", file_path],
        capture_output=True, text=True
    )
    return float(r.stdout.strip())


def get_frame_count(file_path: str) -> int:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", file_path],
        capture_output=True, text=True
    )
    return int(r.stdout.strip())


# ---------------------------------------------------------------------------
# Step 1: Trim clips
# ---------------------------------------------------------------------------

def trim_clips(config: dict) -> list[float]:
    CLIPS_DIR.mkdir(exist_ok=True)
    durations = []

    for i, scene in enumerate(config["scenes"]):
        idx = f"{i:02d}"
        out_file = CLIPS_DIR / f"scene_{idx}.mp4"

        if out_file.exists():
            d = get_duration(str(out_file))
            durations.append(d)
            continue

        ts = scene.get("trimStart", 0)
        te = scene.get("trimEnd")
        cmd = ["ffmpeg", "-y"]
        if ts > 0:
            cmd += ["-ss", str(ts)]
        if te:
            cmd += ["-to", str(te)]
        cmd += ["-i", scene["file"], "-c:v", "libx264",
                "-r", str(config["output"]["fps"]), "-an", str(out_file)]

        subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        d = get_duration(str(out_file))
        durations.append(d)

    return durations


# ---------------------------------------------------------------------------
# Step 2: Ken Burns
# ---------------------------------------------------------------------------

def apply_ken_burns(config: dict, durations: list[float]) -> list[float]:
    KB_DIR.mkdir(exist_ok=True)
    fps = config["output"]["fps"]
    kb_durations = []

    for i, scene in enumerate(config["scenes"]):
        idx = f"{i:02d}"
        out_file = KB_DIR / f"scene_{idx}.mp4"

        if out_file.exists():
            d = get_duration(str(out_file))
            kb_durations.append(d)
            continue

        zs = scene.get("zoomStart", 1.0)
        ze = scene.get("zoomEnd", 1.0)
        fc = get_frame_count(str(CLIPS_DIR / f"scene_{idx}.mp4"))
        step = abs(ze - zs) / max(fc, 1)

        if ze > zs:
            z_expr = f"min(zoom+{step:.6f},{ze})"
        elif ze < zs:
            z_expr = f"max(zoom-{step:.6f},{ze})"
        else:
            z_expr = "1.0"

        cmd = [
            "ffmpeg", "-y",
            "-i", str(CLIPS_DIR / f"scene_{idx}.mp4"),
            "-vf", f"zoompan=z='{z_expr}':d=1:s=720x1280:fps={fps}",
            "-c:v", "libx264", "-crf", "20", "-preset", "fast",
            str(out_file),
        ]

        subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        d = get_duration(str(out_file))
        kb_durations.append(d)

    return kb_durations


# ---------------------------------------------------------------------------
# Step 3: Render with xfade + audio
# ---------------------------------------------------------------------------

def render(config: dict, durations: list[float]) -> str:
    OUTPUTS_DIR.mkdir(exist_ok=True)
    scenes = config["scenes"]
    transitions = config.get("transitions", [])
    bgm = config.get("bgm", {})
    out_cfg = config["output"]
    fps = out_cfg["fps"]
    W = out_cfg["width"]
    H = out_cfg["height"]
    crf = out_cfg["crf"]
    N = len(scenes)

    TRANS_DUR = transitions[0].get("duration", 0.8) if transitions else 0.8
    total = sum(durations) - (N - 1) * TRANS_DUR if N > 1 else sum(durations)

    output_path = OUTPUTS_DIR / "latest.mp4"

    args = ["ffmpeg", "-y"]
    for i in range(N):
        args += ["-i", str(KB_DIR / f"scene_{i:02d}.mp4")]

    # Voiceover inputs
    vo_input_counter = 0
    for i, scene in enumerate(scenes):
        if scene.get("voiceover"):
            args += ["-i", scene["voiceover"]]
            vo_input_counter += 1

    bgm_idx = None
    if bgm.get("file"):
        args += ["-i", bgm["file"]]
        bgm_idx = N + vo_input_counter

    # Video filter: xfade chain
    fc = []
    prev = "[0:v]"
    if N > 1:
        cum = 0
        for i in range(N - 1):
            cum += durations[i]
            offset = cum - TRANS_DUR
            t_type = transitions[i].get("type", "fade") if i < len(transitions) else "fade"
            t_dur = transitions[i].get("duration", TRANS_DUR) if i < len(transitions) else TRANS_DUR
            out_label = f"[v{i:02d}]"
            fc.append(f"{prev}[{i+1}:v]xfade=transition={t_type}:duration={t_dur}:offset={offset:.6f}{out_label}")
            prev = out_label
    fc.append(f"{prev}scale={W}x{H},format=yuv420p[vfinal]")

    # Audio filter: voiceover delays
    starts = []
    cum = 0
    for i in range(N):
        starts.append(cum)
        cum += durations[i]
        if i < N - 1:
            cum -= TRANS_DUR

    vo_counter = 0
    vo_labels = []
    for i, scene in enumerate(scenes):
        if scene.get("voiceover"):
            delay = int((starts[i] + scene.get("voDelay", 0.3)) * 1000)
            fc.append(f"[{N + vo_counter}:a]adelay={delay}|{delay}[vo{i}]")
            vo_labels.append(f"[vo{i}]")
            vo_counter += 1

    # Mix voiceovers
    if vo_labels:
        n_vo = len(vo_labels)
        all_vo = "".join(vo_labels)
        fc.append(f"{all_vo}amix=inputs={n_vo}:duration=longest[vos]")

    # BGM
    if bgm_idx is not None:
        vol = bgm.get("volume", 0.25)
        fade_in = bgm.get("fadeIn", 2.0)
        fade_out = bgm.get("fadeOut", 3.0)
        bgm_start = total - fade_out
        fc.append(f"[{bgm_idx}:a]volume={vol},afade=t=in:st=0:d={fade_in},afade=t=out:st={bgm_start:.2f}:d={fade_out}[bgm]")
        if vo_labels:
            fc.append("[vos][bgm]amix=inputs=2:weights=1 0.25[aout]")
        else:
            fc.append("[bgm]acopy[aout]")
    elif vo_labels:
        fc.append("[vos]acopy[aout]")

    filter_complex = ";".join(fc)
    args += ["-filter_complex", filter_complex]
    args += ["-map", "[vfinal]"]
    if vo_labels or bgm_idx is not None:
        args += ["-map", "[aout]"]
    args += ["-c:v", "libx264", "-crf", str(crf), "-preset", "fast"]
    if vo_labels or bgm_idx is not None:
        args += ["-c:a", "aac", "-b:a", "192k"]
    args += ["-t", f"{total:.2f}"]
    args += [str(output_path)]

    result = subprocess.run(args, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        print("RENDER ERROR:", result.stderr[-1000:], file=sys.stderr)
        sys.exit(1)

    return str(output_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    start_time = time.time()

    print("=== Video Compositor Research ===")
    print()

    # Step 1: Trim
    print("Step 1: Trimming clips...")
    durations = trim_clips(COMPOSITION)
    print(f"  {len(durations)} clips, total {sum(durations):.1f}s raw")

    # Step 2: Ken Burns
    print("Step 2: Ken Burns...")
    kb_durations = apply_ken_burns(COMPOSITION, durations)
    print(f"  Done")

    # Step 3: Render
    print("Step 3: Rendering...")
    output_path = render(COMPOSITION, kb_durations)
    render_time = time.time() - start_time

    duration = get_duration(output_path)
    file_size = os.path.getsize(output_path) / (1024 * 1024)

    # Print metrics (same format as autoresearch train.py)
    print()
    print("---")
    print(f"quality_score:    0.000000")  # placeholder, LLM evaluates separately
    print(f"duration_seconds: {duration:.1f}")
    print(f"render_seconds:  {render_time:.1f}")
    print(f"file_size_mb:    {file_size:.1f}")
    print(f"num_scenes:       {len(COMPOSITION['scenes'])}")
    print(f"num_transitions:  {len(COMPOSITION.get('transitions', []))}")
    print(f"output:           {output_path}")


if __name__ == "__main__":
    main()
