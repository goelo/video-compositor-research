# Video Compositor Research

Fork of [karpathy/autoresearch](https://github.com/karpathy/autoresearch), adapted for **video composition parameter optimization**.

Instead of training ML models, an LLM agent iterates on video composition parameters (Ken Burns, transitions, trim points, audio levels) to achieve commercial-quality promotional videos.

## How It Works

Same autonomous research loop as autoresearch:

1. **Agent** reads `program.md` for instructions
2. **Agent** modifies `compose.py` (the only editable file)
3. **Agent** runs `python3 compose.py` → renders a video
4. **Agent** extracts frames → sends to vision LLM for quality scoring
5. **Agent** logs score to `results.tsv`
6. **If improved**: keep the change. **If worse**: git reset.
7. **Loop forever** until manually stopped.

## Project Structure

```
evaluate.py    — Fixed evaluation harness (DO NOT MODIFY)
compose.py      — Composition config + rendering (AGENT MODIFIES THIS)
program.md      — Agent instructions (HUMAN MODIFIES THIS)
README.md      — This file
```

## Quick Start

```bash
# Verify source videos exist
ls ~/.openclaw/workspace/projects/zuishanhe-baijiu/videos-30fps/scene_*.mp4

# Run baseline render
python3 compose.py

# Extract frames for evaluation
python3 -c "from evaluate import *; extract_frames('outputs/latest.mp4', 'eval-frames/')"
```

## Setup for Autonomous Research

1. Fork this repo
2. Point your coding agent (Claude Code, Codex, etc.) at this directory
3. Give it `program.md` as context
4. Say: "Read program.md and kick off a new experiment!"
5. Go to sleep. Wake up to results.

## The Metric

`quality_score` (0-10) — evaluated by LLM on 5 dimensions:
- Transition Naturalness
- Camera Movement Quality
- Rhythm & Pacing
- Compositional Stability
- Overall Polish

## Differences from Original autoresearch

| Original | This Fork |
|----------|-----------|
| train.py (ML model) | compose.py (video composition) |
| prepare.py (data/eval) | evaluate.py (frame extraction/scoring) |
| val_bpb metric | quality_score (0-10) |
| 5 min time budget per experiment | ~30-60 sec per render |
| GPU required | ffmpeg only (CPU) |
| PyTorch | No ML dependencies |

## License

MIT
