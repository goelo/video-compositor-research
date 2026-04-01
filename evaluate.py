"""
Evaluation utilities for video compositor research.
Fixed evaluation harness — agents should NOT modify this file.

Provides:
- extract_frames(): Sample key frames from rendered video
- evaluate_quality(): LLM-based visual quality scoring
- render_video(): Call ffmpeg compose pipeline
"""

import subprocess
import json
import os
import sys
from pathlib import Path
from dataclasses import dataclass, asdict

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TIME_BUDGET = 300  # seconds max per render (safety)
DEFAULT_FPS = 30
EVAL_FRAMES = 10  # number of frames to extract for evaluation


# ---------------------------------------------------------------------------
# Frame extraction
# ---------------------------------------------------------------------------

def extract_frames(video_path: str, output_dir: str, num_frames: int = EVAL_FRAMES) -> list[str]:
    """Extract evenly-spaced frames from a video for LLM evaluation."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    duration = get_duration(video_path)
    if duration <= 0:
        raise ValueError(f"Cannot get duration of {video_path}")
    
    frame_paths = []
    for i in range(num_frames):
        timestamp = duration * (i + 0.5) / num_frames
        out_path = os.path.join(output_dir, f"frame_{i:03d}.jpg")
        
        r = subprocess.run(
            ["ffmpeg", "-y", "-ss", str(timestamp), "-i", video_path,
             "-frames:v", "1", "-q:v", "2", out_path],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode == 0 and os.path.exists(out_path):
            frame_paths.append(out_path)
    
    return frame_paths


# ---------------------------------------------------------------------------
# Duration / info
# ---------------------------------------------------------------------------

def get_duration(file_path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", file_path],
        capture_output=True, text=True
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def get_file_size_mb(file_path: str) -> float:
    return os.path.getsize(file_path) / (1024 * 1024)


# ---------------------------------------------------------------------------
# Evaluation prompt for LLM
# ---------------------------------------------------------------------------

EVAL_PROMPT_TEMPLATE = """You are a professional video editor evaluating a short promotional video (vertical 9:16 format).

Below are {num_frames} frames extracted at even intervals from a {duration:.1f}s video with {num_scenes} scenes.

## Evaluation Criteria (score each 1-10):

1. **Transition Naturalness** (转场自然度): Do scene transitions look smooth? Any hard cuts, black frames, or jarring jumps?
2. **Camera Movement Quality** (运镜质量): Does the Ken Burns effect feel cinematic? Or mechanical/too fast/too slow?
3. **Rhythm & Pacing** (节奏感): Is the pace engaging? Any scenes that drag or feel rushed?
4. **Compositional Stability** (构图稳定性): Do subjects stay centered during zoom/pan? Any clipping or awkward framing?
5. **Overall Polish** (整体观感): Does this look like a real commercial ad vs. a student project?

## Current Composition Config:
```json
{config_json}
```

## Instructions:
1. Look at each frame carefully
2. Pay special attention to frames at scene boundaries (these show transitions)
3. Score each criterion 1-10
4. Give a total score (average of 5 criteria)
5. Provide ONE specific, actionable improvement suggestion for the next iteration

## Output Format (strictly follow this):
```
TRANSITION: X/10
CAMERA: X/10
RHYTHM: X/10
COMPOSITION: X/10
POLISH: X/10
TOTAL: X.X/10
IMPROVEMENT: <one specific suggestion>
```"""


@dataclass
class EvalResult:
    transition: float
    camera: float
    rhythm: float
    composition: float
    polish: float
    total: float
    improvement: str
    
    def to_tsv_row(self) -> str:
        return f"{self.transition:.1f}\t{self.camera:.1f}\t{self.rhythm:.1f}\t{self.composition:.1f}\t{self.polish:.1f}\t{self.total:.1f}\t{self.improvement}"


def parse_eval_response(text: str) -> EvalResult:
    """Parse LLM evaluation response into EvalResult."""
    scores = {}
    improvement = ""
    
    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith("TRANSITION:"):
            scores["transition"] = float(line.split("/")[0].split(":")[-1].strip())
        elif line.startswith("CAMERA:"):
            scores["camera"] = float(line.split("/")[0].split(":")[-1].strip())
        elif line.startswith("RHYTHM:"):
            scores["rhythm"] = float(line.split("/")[0].split(":")[-1].strip())
        elif line.startswith("COMPOSITION:"):
            scores["composition"] = float(line.split("/")[0].split(":")[-1].strip())
        elif line.startswith("POLISH:"):
            scores["polish"] = float(line.split("/")[0].split(":")[-1].strip())
        elif line.startswith("TOTAL:"):
            scores["total"] = float(line.split("/")[0].split(":")[-1].strip())
        elif line.startswith("IMPROVEMENT:"):
            improvement = line.split(":", 1)[1].strip()
    
    if "total" not in scores:
        # Fallback: compute average
        available = [v for k, v in scores.items() if k != "total"]
        scores["total"] = sum(available) / max(len(available), 1)
    
    return EvalResult(
        transition=scores.get("transition", 0),
        camera=scores.get("camera", 0),
        rhythm=scores.get("rhythm", 0),
        composition=scores.get("composition", 0),
        polish=scores.get("polish", 0),
        total=scores.get("total", 0),
        improvement=improvement
    )


def build_eval_prompt(config: dict, duration: float, num_scenes: int) -> str:
    """Build the evaluation prompt for the LLM."""
    return EVAL_PROMPT_TEMPLATE.format(
        num_frames=EVAL_FRAMES,
        duration=duration,
        num_scenes=num_scenes,
        config_json=json.dumps(config, indent=2, ensure_ascii=False)
    )
