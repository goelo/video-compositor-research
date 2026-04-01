# Video Compositor Research

用 LLM agent 自动迭代优化视频拼接参数，目标是达到商业广告入门级效果。

## Setup

1. **Agree on a run tag**: propose a tag (e.g. `apr1`). Branch `autoresearch/<tag>` must not exist.
2. **Create the branch**: `git checkout -b autoresearch/<tag>` from current master.
3. **Read the in-scope files**:
   - `README.md` — repo context
   - `evaluate.py` — evaluation harness (DO NOT MODIFY). Contains frame extraction, eval prompt template, score parsing.
   - `compose.py` — the file you modify. Contains the composition config and ffmpeg rendering pipeline.
4. **Verify source videos exist**: Check that `~/.openclaw/workspace/projects/zuishanhe-baijiu/videos-30fps/` contains `scene_00.mp4` ~ `scene_08.mp4`. Check `audio/voiceover_00.mp3` ~ `audio/voiceover_08.mp3` and `audio/bgm.mp3` exist.
5. **Initialize results.tsv**: Create with header: `commit\tquality_score\tduration_seconds\trender_seconds\tfile_size_mb\tstatus\tdescription`
6. **Confirm and go**: Run baseline render first.

## Experimentation

Each experiment renders a video in under ~60 seconds. You launch it as: `python3 compose.py > run.log 2>&1`

**What you CAN do:**
- Modify `compose.py` — this is the only file you edit. Everything is fair game:
  - `COMPOSITION["scenes"][i]["trimStart"]` / `trimEnd` — which segment of source video to use
  - `COMPOSITION["scenes"][i]["zoomStart"]` / `zoomEnd` — Ken Burns zoom range
  - `COMPOSITION["transitions"][i]["type"]` — transition type (fade, dissolve, wipeleft, wiperight, fadeblack, fadewhite, circlecrop, radial, smoothleft, smoothright, distance, pixelize, wipeup, wipedown, slideleft, slideright)
  - `COMPOSITION["transitions"][i]["duration"]` — transition duration in seconds (0.3~1.5)
  - `COMPOSITION["bgm"]["volume"]` — BGM volume (0.10~0.40)
  - `COMPOSITION["bgm"]["fadeIn"]` / `fadeOut` — BGM fade durations
  - `COMPOSITION["scenes"][i]["voDelay"]` — voiceover delay within each scene
  - The rendering logic itself (zoompan expressions, xfade chain, audio mix)

**What you CANNOT do:**
- Modify `evaluate.py`. It is the ground truth evaluation harness.
- Install new packages. Only use ffmpeg/ffprobe (already on system) and Python stdlib.
- Modify source videos or audio files.
- Use the browser or any external tools to evaluate. Evaluation is done by analyzing extracted frames.

## The Metric

The quality metric is `quality_score` (0-10), evaluated by an LLM analyzing 10 extracted frames from the rendered video.

**Evaluation process:**
1. After rendering, extract frames: call `extract_frames("outputs/latest.mp4", "eval-frames/", num_frames=10)` from `evaluate.py`
2. Build eval prompt: `build_eval_prompt(COMPOSITION, duration, num_scenes)` from `evaluate.py`
3. Send the prompt + frame images to the vision LLM for scoring
4. Parse the response: `parse_eval_response(text)` from `evaluate.py`
5. The `TOTAL` score from the LLM response is the `quality_score`

**Evaluation dimensions (each 1-10):**
1. **Transition Naturalness**: Smooth scene transitions? No hard cuts/black frames?
2. **Camera Movement Quality**: Cinematic Ken Burns? Not mechanical/too fast/slow?
3. **Rhythm & Pacing**: Engaging pace? No dragging or rushing?
4. **Compositional Stability**: Subjects centered during zoom/pan?
5. **Overall Polish**: Looks like a real ad vs. student project?

## Logging results

Log to `results.tsv` (tab-separated):

```
commit	quality_score	duration_seconds	render_seconds	file_size_mb	status	description
```

1. git commit hash (7 chars)
2. quality_score (0.0 for crashes)
3. video duration in seconds
4. render time in seconds
5. file size in MB
6. status: `keep`, `discard`, or `crash`
7. short description

## The Experiment Loop

LOOP FOREVER:

1. Look at the git state
2. Tune `compose.py` with an experimental idea
3. git commit
4. Render: `python3 compose.py > run.log 2>&1`
5. Extract metrics: `grep "^quality_score:\|^duration_seconds:\|^render_seconds:\|^file_size_mb:" run.log`
6. Extract frames from the rendered video
7. Send frames to LLM for evaluation → get quality_score
8. If crash: read error, attempt fix, or log as crash and move on
9. Record results in results.tsv
10. If quality_score improved, keep the commit
11. If quality_score equal or worse, git reset

**Timeout**: Each render should take under 60 seconds. If it exceeds 120 seconds, kill and treat as crash.

**Crashes**: If render fails, check `run.log` tail. Fix simple bugs (typos, missing files). If fundamentally broken, log crash and move on.

**NEVER STOP**: Once the loop starts, run indefinitely. If stuck, try combining previous near-misses, try more radical changes, re-read the composition config for new angles.

## Available Transition Types

| Type | Effect | Good For |
|------|--------|----------|
| fade | Cross-fade | General soft transition |
| fadeblack | Fade through black | Section breaks, mood shift |
| fadewhite | Fade through white | Dreamlike, flashback |
| dissolve | Dissolve | Natural flow |
| wipeleft | Left wipe | Action cut-in |
| wiperight | Right wipe | Action cut-in |
| wipeup | Up wipe | Reveal, unfold |
| wipedown | Down wipe | Descent, ending |
| slideleft | Slide left | Narrative shift |
| slideright | Slide right | Narrative shift |
| circlecrop | Circle reveal | Ceremony, focus |
| radial | Radial expand | Highlight moment |
| smoothleft | Smooth left | Elegant transition |
| smoothright | Smooth right | Elegant transition |
| distance | Distance dissolve | Time jump |
| pixelize | Pixelate | Tech, digital theme |

## Ken Burns Guidelines

| Scene Type | zoomStart | zoomEnd | Effect |
|-----------|-----------|---------|--------|
| Atmospheric/landscape | 1.00 | 1.04~1.08 | Slow push-in |
| Product close-up | 1.00 | 1.08~1.12 | Medium push-in |
| Craft/action | 1.00 | 1.10~1.16 | Faster push-in |
| Pull-back/reveal | 1.06~1.10 | 1.00 | Slow pull-out |
| Stable/breathing | 1.00 | 1.00 | No movement |

## Tips for the Agent

- **Start with the baseline**: First run is always the current config as-is. Record the baseline score.
- **Change one thing at a time**: Don't modify all scenes simultaneously. Change one transition type, or one Ken Burns value, evaluate, then iterate.
- **Pay attention to transition timing**: The xfade offset calculation must be exact. If you change transition duration, the offsets change for all subsequent transitions.
- **BGM should not overpower voiceover**: volume 0.15~0.30 is the sweet spot.
- **Shorter transitions feel more modern**: 0.5~0.8s is typical for social media ads. 1.0s+ feels slow.
- **Match transition type to content mood**: Don't use wipe for emotional moments. Don't use fadeblack between similar scenes.
- **zoompan d=1**: Always use d=1 in zoompan (one output frame per input frame). Never set d to frame count.
