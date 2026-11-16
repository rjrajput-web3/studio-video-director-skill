# Quality Gates — Reference Card

Condensed from the pipeline standards. The scripts in `scripts/` are
the executable version of this card; this file is the human-readable
one. Print it, pin it, run it.

## Hard rules (any violation = failed build)

- **Stereo:** final mix MUST be 2 channels. Mono input? Upmix
  explicitly (`-ac 2` / `aformat=channel_layouts=stereo`) BEFORE mixing.
- **Loudness:** two-pass loudnorm to **-15 LUFS**; integrated must land
  **-14 to -16 LUFS**; true peak **<= -1.5 dBTP** (hard fail);
  LRA **>= 6 LU** (under 4 LU = over-compressed, back off the limiter).
- **Cuts:** a visual/camera cut at least every **3-4 s**; NO gap > 4 s.
  45 s video = 12+ cuts; 20 s Short = 5+ cuts.
- **Hook:** title/question + motion in the **first 3 s**. Never a slow
  setup, never a static cover opener.
- **Zero slideshows:** real motion everywhere (screen recording,
  B-roll, animation). Ken Burns on stills: at most ONE segment of
  <= 4 s per Short.
- **Captions:** 16:9 demos = separate `.SRT` sidecar ONLY, zero
  burned-in narration captions. 9:16 Shorts = `.SRT` sidecar AND
  styled lower-third safe-zone captions.
- **Aspect lock:** pick ONE ratio per project and lock it --
  16:9 = 1920x1080, 9:16 = 1080x1920. Scale + pad, never stretch.
- **Music/SFX:** real licensed track (Mixkit / Pixabay / YouTube
  Audio Library) + real designed SFX synced to cuts. Synthesized
  beds/SFX banned. VO: neural TTS only (gTTS banned).
- **Voice:** <= 30 words per shot, ~150 words/minute, one idea per shot.

## The 10 gates (run `scripts/quality_gate.py`)

| # | Gate | Check | Tool |
| - | ---- | ----- | ---- |
| 1 | Specs | duration / resolution / fps / channels | ffprobe |
| 2 | Loudness | -14..-16 LUFS, TP <= -1.5, LRA >= 6 | `audio_lufs_check.py` |
| 3 | Dead air | no silence >= 0.5 s (trailing tail <= 1 s OK) | silencedetect |
| 4 | Cut cadence | max cut gap <= 4 s | `extract_frames_check.py` |
| 5 | VO coverage | >= 80% of script words in transcript | faster-whisper |
| 6 | Frames | 00:02 / mid / end pass the named checklist | `extract_frames_check.py --frames-dir` |
| 7 | Stereo | channels == 2 | ffprobe |
| 8 | Real music/SFX | human attestation | `--attest-real-audio` |
| 9 | No slideshow | no frozen segment > 4 s | freezedetect |
| 10 | Master protection | .SRT present, no *-broken / *-v1 / *-v2 | file check |

## Named frame checklist (00:02, mid, end frames)

(a) nothing clipped at any edge · (b) no dead band/empty area > 25%
of frame · (c) every on-screen word readable at phone size ·
(d) captions visible where the script says they should be ·
(e) no placeholder/fake UI text · (f) subject fills the frame.

## Quick commands

```bash
# Full gate
python3 scripts/quality_gate.py final.mp4 --aspect 16:9 \
  --srt final.srt --script vo-script.txt --frames-dir checks/

# Audio only
python3 scripts/audio_lufs_check.py final.mp4

# Motion / aspect / frames only
python3 scripts/extract_frames_check.py final.mp4 --aspect 9:16 --frames-dir checks/

# Loudness measurement (manual, same numbers the gate uses)
ffmpeg -nostdin -i final.mp4 -vn -af \
  loudnorm=I=-15:TP=-1.5:LRA=11:print_format=json -f null -
```
