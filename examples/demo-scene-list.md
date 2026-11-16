# Worked Example — 30 s Short: "The 30-Second Rule"

A complete storyboard + cut list for a 9:16 Short, built with the
8-step workflow. Copy the structure, replace the subject.

- **Aspect lock:** 9:16, 1080x1920, 30 fps
- **Length:** 30 s (10 segments of 3 s = 10 cuts, max gap 3 s)
- **VO:** ~75 words total (~150 wpm), <= 30 words per shot
- **Music:** real licensed track, ducked -20 dB under VO
- **Captions:** .SRT sidecar + lower-third burned captions

## Cut list

| # | Time | Shot | VO (words) | Motion / SFX |
| - | ---- | ---- | ---------- | ------------ |
| 1 | 0-3s | HOOK: extreme close-up, timer hits 00:30 | "Thirty seconds. That's all you get." (7) | Hard cut in, tick SFX |
| 2 | 3-6s | Medium shot, creator at desk, phone timer | "Most videos lose you by second four." (8) | Slow push-in |
| 3 | 6-9s | Screen recording, retention graph dropping | "See this cliff? That's a boring opening." (8) | Real scroll, click SFX |
| 4 | 9-12s | B-roll: street, fast walk, motion blur | "So I cut every three seconds." (6) | Whip pan transition |
| 5 | 12-15s | Close-up, hands clapping on each cut | "Cut. Cut. Cut. Your brain stays awake." (7) | Clap SFX on each cut |
| 6 | 15-18s | Screen recording, timeline with 10 cuts marked | "Ten cuts in thirty seconds. That's the rule." (8) | Cursor moves, click SFX |
| 7 | 18-21s | Medium shot, creator points at camera | "Try it on your next video." (6) | Zoom punch-in |
| 8 | 21-24s | B-roll: editing timeline, playhead moving | "Watch the retention graph flatten out." (7) | Smooth tracking |
| 9 | 24-27s | Close-up, creator smiles, timer hits zero | "Thirty seconds. Done." (3) | Ding SFX |
| 10 | 27-30s | End card: channel name + subscribe | "Follow for the next rule." (5) | Slow zoom-out, music swell |

**Total VO: 65 words. Cuts: 10 (max gap 3.0 s). Hook: 0-3 s.**

## Six-part prompt for segment 1 (example)

```
[3 seconds, 9:16 vertical, 1080x1920, 30fps] Extreme close-up of a phone
timer hitting 00:30.
Subject: Hands only, clean nails, dark hoodie sleeve visible at frame edge.
Scene: Desk at night, warm desk lamp from the left, shallow depth of field.
Beats (with timestamps):
  0-1s: Timer digits flip to 00:30, sharp and legible.
  1-3s: Finger taps start, timer begins counting down.
Camera: Locked-off macro, no movement, no zoom.
Sound: Single timer tick, then silence under the VO line.
Dialogue language: English.
Constraints: never blur the timer digits; never warp fingers; never add text overlays.
```

## Gate run for this video

```bash
python3 scripts/quality_gate.py the-30-second-rule.mp4 --aspect 9:16 \
  --srt the-30-second-rule.srt --script vo-script.txt --frames-dir checks/
# Expect: 10 gates PASS. Cut gap max 3.0 s, no frozen segment, stereo, -15 LUFS.
```
