# Studio Video Director Skill

**Turn rough footage and a script into a studio-grade video — with a quality gate that refuses to ship amateur work.**

A battle-tested AI video & Shorts production pipeline, packaged as an
open-core agent skill. It plans like a 6-person film crew, generates
with a strict six-part prompt system, assembles multi-scene videos
with FFmpeg, and — most importantly — **fails the build** when the
audio is mono, the loudness is wrong, the video is a slideshow, or a
caption is clipped. Every rule here was paid for with real failed
builds, measured and fixed, not theorized.

- ✅ **True stereo audio** (2 channels, verified — never mono)
- ✅ **-14 to -16 LUFS loudness**, true peak ≤ -1.5 dBTP, LRA ≥ 6 LU
- ✅ **A visual cut every 3–4 seconds** — zero static slideshows
- ✅ **Strict aspect-ratio lock** — 16:9 demos or 9:16 Shorts, never mixed
- ✅ **Captions done right** — .SRT sidecar for demos, lower-third burned captions for Shorts
- ✅ **$0 total spend** — local FFmpeg + Whisper only. No paid APIs, no signups, no cards.

## Install

```bash
# Clone into your agent skills directory (Claude Code shown)
git clone https://github.com/rjrajput-web3/studio-video-director-skill.git ~/.claude/skills/studio-video-director

# Or use it standalone from anywhere
git clone https://github.com/rjrajput-web3/studio-video-director-skill.git
cd studio-video-director-skill
```

**Requirements:** ffmpeg / ffprobe 8.x, Python 3.10+. Optional:
`pip install faster-whisper` (local CPU transcription for the VO-coverage gate).

## Quickstart

```bash
# 1. Plan with the six-part prompt template
#    See references/prompt-template.md — one prompt per segment, <=10 s each.

# 2. Check a finished video's audio
python3 scripts/audio_lufs_check.py final.mp4

# 3. Check motion, cuts and aspect ratio (extracts 00:02 / mid / end frames)
python3 scripts/extract_frames_check.py final.mp4 --aspect 16:9 --frames-dir checks/

# 4. Run the full 10-gate pre-delivery check
python3 scripts/quality_gate.py final.mp4 --aspect 16:9 \
  --srt final.srt --script vo-script.txt --frames-dir checks/
# RESULT: PASS  -> ship it.   RESULT: FAIL -> fix the named gate, re-check.
```

## Before / After

**Before — the typical AI-video failure mode this skill kills:**

| Problem | What it looked like |
| ------- | ------------------- |
| Slideshow Short | 4 still images, Ken Burns pans, zero real motion |
| Mono audio | Voiceover recorded in mono, collapsed mix, flat sound |
| Hot / crushed loudness | -8 LUFS with clipping, or -22 LUFS you can't hear |
| Dead air | 2 s of silence mid-video while a static frame sits there |
| No captions | Shorts muted viewers see nothing, retention dies |
| Mixed aspect ratios | 16:9 clip pasted into a 9:16 Short, black bars + stretch |

**After — the same video through this pipeline:**

| Fix | What changed |
| --- | ------------ |
| Cut cadence gate | A cut or camera move every 3–4 s, max gap enforced by script |
| Stereo + loudness gate | Verified 2 channels, -15 LUFS, TP -1.5 dBTP, LRA ≥ 6 |
| Dead-air gate | No silence ≥ 0.5 s except a ≤ 1 s trailing tail |
| Frame checklist | 00:02 / mid / end frames checked at 100% zoom for clipping, dead space, readability |
| Caption rule | .SRT sidecar + lower-third burned captions on Shorts |
| Aspect lock | Every scene normalized to the locked frame before joining |

Real numbers from the audit that built these gates: 4 shipped Shorts
were slideshows, 3 of 5 deliverables were mono, loudness range was as
low as 1.9 LU (over-compressed). All of it is now caught automatically
before anything ships.

## What's inside

```
studio-video-director-skill/
├── SKILL.md                        # Agent skill entry point (Claude Code / universal)
├── scripts/
│   ├── audio_lufs_check.py         # stereo + LUFS + true-peak + LRA gate
│   ├── extract_frames_check.py     # aspect lock + freeze + cut-gap + frame extraction
│   └── quality_gate.py             # the full 10-gate pre-delivery check
├── references/
│   ├── prompt-template.md          # six-part vertical & landscape prompt template
│   └── quality-gates.md            # condensed gate reference card
├── examples/
│   └── demo-scene-list.md          # worked 30 s Short storyboard + cut list
└── pro-bundle/                     # Pro Edition (see below)
```

## Pro Edition

The free tier gates your video. **Pro builds it.**

| Pro feature | What it does |
| ----------- | ------------ |
| Multi-scene assembly | Normalizes every scene to the locked frame and joins them with the concat demuxer, then masters audio with two-pass loudnorm |
| Auto-ducking mix | Sidechain-compresses the music bed under the VO (-20 dB Shorts / -22 dB demos), stereo-safe |
| Whisper .SRT + burned captions | Local faster-whisper transcription to .SRT, plus styled burned captions (lower-third safe zone for Shorts) |
| 18 niche templates | Product commercials, movie breakdowns, viral clipping hooks, hackathon demos, SaaS demos, testimonials, explainers, unboxings, tutorials, trailers, podcast clips, fitness, food, travel, finance, education, gaming, real estate |
| Batch gate | One command gates a whole folder of renders and writes a Markdown + JSON report |

**Pro Edition is available on Whop / Gumroad** (listing link added at
publish time). It ships as `pro-bundle.zip` — same $0 tooling, no paid
APIs, no subscriptions inside the scripts themselves.

## The 10 quality gates (no waivers)

1. Specs (resolution / fps / channels == 2) · 2. Loudness (-14..-16 LUFS,
TP ≤ -1.5 dBTP, LRA ≥ 6) · 3. Dead air · 4. Cut cadence (gap ≤ 4 s) ·
5. VO coverage (≥ 80% of script words heard) · 6. Frames (00:02 / mid /
end checklist) · 7. Stereo · 8. Real music/SFX (human attestation) ·
9. No slideshow · 10. Master protection (.SRT present, no broken/old
siblings).

Any gate failing = failed build. Fix first, ship second.

## License

MIT. Free for personal and commercial use. The Pro bundle is a
separate paid pack; the free tier stays free forever.
