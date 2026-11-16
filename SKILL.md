---
name: studio-video-director
description: Studio-grade AI video and Shorts production pipeline. Use when planning, scripting, generating, assembling, or quality-gating any video: hackathon demos (16:9), Shorts/Reels (9:16), product commercials, movie breakdowns, viral clipping, or any multi-scene narrated video. Enforces true stereo audio, -14 to -16 LUFS loudness, a visual cut every 3-4 seconds, zero static slideshows, and a strict aspect-ratio lock. Free tier is $0 (local FFmpeg + Whisper only); Pro adds multi-scene assembly, auto-ducking, caption burning, niche templates, and batch gating.
---

# Studio Video Director

A battle-tested, measurement-driven pipeline for producing studio-grade
videos with free local tools. Every rule below was paid for with real
failed builds: mono mixes, over-compressed audio, slideshow Shorts,
clipped captions, and dead air. A build that violates any gate is a
failed build -- fix it, don't ship it.

## When to use this skill

- Any video deliverable: hackathon demo, product demo, Short/Reel,
  movie breakdown, commercial, tutorial, trailer, podcast clip.
- Before rendering: planning, script, storyboard, shot prompts.
- After rendering: the 10-gate pre-delivery check on the FINAL encode.
- When a video "looks fine but feels amateur": run the gate, fix the
  failing gates, re-check. The gate names the exact defect.

## The 8-step workflow

1. **Brief** -- one paragraph: audience, one idea, one CTA, length,
   aspect (pick ONE and lock it: `16:9` demo/long-form or `9:16`
   Shorts/Reels -- NEVER mix ratios in a project).
2. **Crew plan (6 roles)** -- Director (vision + cut list), Writer
   (script, <=30 words per shot, ~150 wpm), DP (camera + framing),
   Art Director (palette + set), VFX (motion + transitions), Sound
   Designer (VO + music + SFX). Each role signs off before generation.
3. **Storyboard + cut list** -- written BEFORE animating. A visual or
   camera cut at least every 3-4 s (no gap > 4 s, hard fail). Hook in
   the first 3 s: title/question + motion. Never a static cover opener.
4. **Prompts (six-part)** -- per segment, <=10 s each, using
   `references/prompt-template.md`: duration/format, subject, scene,
   beats with timestamps, camera language, sound/dialogue, constraints.
   Reuse the subject description VERBATIM across segments.
5. **Generate segments** -- real motion only: screen recording
   (Playwright, deviceScaleFactor 2, 1920x1080@30fps for demos),
   B-roll, or animation. Ken Burns on stills: at most ONE segment
   of <=4 s per Short, never the whole video.
6. **Assemble** -- normalize every scene to the locked frame
   (scale + pad, never stretch), join with the concat demuxer, master
   the audio (Pro: `pro-bundle/scripts/assemble_multiscene.py`).
7. **Sound** -- neural VO only (edge-tts / studio TTS; gTTS banned).
   Music: a real licensed track (Mixkit / Pixabay / YouTube Audio
   Library), ducked -20 dB (Shorts) or -22 dB (demos) under the VO.
   Real designed SFX synced to cuts. Synthesized beds/SFX banned.
8. **Gate + deliver** -- run `scripts/quality_gate.py` on the FINAL
   encode. All 10 gates must PASS. Save the master + .SRT in
   `renders/` and never trash them.

## Quality gates (all 10, no waivers)

| # | Gate | Rule |
| - | ---- | ---- |
| 1 | Specs | exact duration/resolution/fps; audio channels == 2 |
| 2 | Loudness | integrated -14..-16 LUFS, TP <= -1.5 dBTP, LRA >= 6 LU |
| 3 | Dead air | no silence >= 0.5 s except a trailing tail <= 1 s |
| 4 | Cut cadence | no gap between cuts > 4 s |
| 5 | VO coverage | faster-whisper transcript covers >= 80% of script words |
| 6 | Frames | 00:02 / mid / end frames pass the named frame checklist |
| 7 | Stereo | ffprobe channels == 2 on the final mix |
| 8 | Real music/SFX | human attests real licensed music + real SFX |
| 9 | No slideshow | no frozen segment > 4 s |
| 10 | Master protection | .SRT sidecar present, no *-broken / *-v1 / *-v2 siblings |

Run it:

```bash
python3 scripts/quality_gate.py final.mp4 --aspect 16:9 \
  --srt final.srt --script vo-script.txt --frames-dir checks/
```

Individual gates:

```bash
python3 scripts/audio_lufs_check.py final.mp4
python3 scripts/extract_frames_check.py final.mp4 --aspect 16:9 --frames-dir checks/
```

## Captions rule

- **16:9 demos:** separate `.SRT` sidecar ONLY. Zero burned-in
  narration captions. On-screen UI callouts are allowed -- they are
  not subtitle captions.
- **9:16 Shorts/Reels:** `.SRT` sidecar AND styled lower-third
  safe-zone captions (the Shorts player ignores sidecars; muted
  viewers need on-screen text).

## Named frame checklist (apply to 00:02, mid, end frames)

(a) nothing clipped at any edge, (b) no dead band/empty area > 25%
of frame, (c) every on-screen word readable at phone size,
(d) captions visible where the script says they should be,
(e) no placeholder/fake UI text, (f) subject fills the frame.

## $0 tooling (free tier)

- ffmpeg / ffprobe 8.x, Python 3.10+, faster-whisper (local, CPU).
- Optional external free credits only (OpusClip / Vizard / Quso /
  2short free tiers) -- never invoked by any script in this repo,
  never a paid API, never a signup, never a card.
- This repo contains NO credentials, NO API keys, NO personal data.

## Pro Edition

`pro-bundle/` adds: multi-scene FFmpeg assembly with two-pass
loudnorm mastering, VO + music auto-ducking, Whisper .SRT + burned
caption builder, 18 niche templates, and a one-command batch gate.
See `README.md` (Pro Edition section) and `pro-bundle/README.md`.
