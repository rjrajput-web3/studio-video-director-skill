#!/usr/bin/env bash
# Test runner for studio-video-director-skill.
# Generates small synthetic test media with ffmpeg (testsrc + sine tones),
# runs EVERY script against it, and asserts the expected PASS/FAIL.
# No network, no paid tools, no real footage needed.
#
# Usage: bash tests/run_tests.sh   (from the repo root)
# Exit code: 0 = all tests green, 1 = any test failed.

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$ROOT/tests/tmp"
PY=python3
STT="$HOME/workspace/tmp/venv-stt/bin/python"
PASS=0
FAIL=0

ok()   { PASS=$((PASS+1)); echo "  PASS: $1"; }
bad()  { FAIL=$((FAIL+1)); echo "  FAIL: $1"; }

# expect_exit <wanted> <label> <cmd...>
expect_exit() {
  local wanted="$1"; shift
  local label="$1"; shift
  "$@" >/dev/null 2>&1
  local got=$?
  if [ "$got" = "$wanted" ]; then ok "$label (exit $got)"; else bad "$label (want $wanted, got $got)"; fi
}

# expect_ok <label> <cmd...>  (exit 0)
expect_ok() { local label="$1"; shift; expect_exit 0 "$label" "$@"; }

rm -rf "$TMP" && mkdir -p "$TMP"
cd "$TMP" || exit 1
echo "== test media =="
export TMPDIR="$HOME/workspace/tmp"

# --- 1. Stereo tone, mastered to -15 LUFS (two-pass loudnorm) -> PASS audio
# NOTE: a pure sine has LRA 0 (no dynamics), so the level alternates in
# 4 s blocks (full / -20 dB) -- short-term loudness (3 s windows) needs
# whole windows loud and whole windows quiet for a real LRA. A real
# voiceover/music mix has dynamics; the test tone must too, or the
# LRA >= 6 gate can never pass.
ffmpeg -nostdin -y -loglevel error -f lavfi -i "sine=frequency=440:duration=16" \
  -f lavfi -i "sine=frequency=660:duration=16" \
  -filter_complex "[0:a][1:a]amerge=inputs=2,volume='if(lt(mod(t,8),4),1,0.1)':eval=frame[a]" -map "[a]" -ac 2 raw_stereo.wav
# NOTE: no -loglevel error here -- loudnorm prints its JSON at info level.
ffmpeg -nostdin -y -i raw_stereo.wav -vn \
  -af loudnorm=I=-15:TP=-1.5:LRA=11:print_format=json -f null - 2> loud1.json
# parse measured values with python (robust to ffmpeg's text framing)
python3 - "$TMP" <<'EOF'
import json, re, sys
s = open(sys.argv[1] + '/loud1.json').read()
d = json.loads(s[s.find('{'):s.rfind('}')+1])
# ffmpeg 8.x JSON key is "target_offset"; older ffmpeg used "offset".
open(sys.argv[1] + '/loud1_vals.txt','w').write(
    '%s %s %s %s %s' % (d['input_i'], d['input_tp'], d['input_lra'], d['input_thresh'], d.get('target_offset', d.get('offset', '0'))))
EOF
read MI MTP MLRA MTH MOFF < loud1_vals.txt
ffmpeg -nostdin -y -loglevel error -i raw_stereo.wav -vn \
  -af "loudnorm=I=-15:TP=-1.5:LRA=11:measured_I=$MI:measured_TP=$MTP:measured_LRA=$MLRA:measured_thresh=$MTH:offset=$MOFF:linear=true" \
  good_stereo.wav
echo "  made good_stereo.wav (measured $MI LUFS -> -15 target)"

# --- 2. Mono tone -> FAIL audio (channels != 2)
ffmpeg -nostdin -y -loglevel error -f lavfi -i "sine=frequency=440:duration=8" -ac 1 mono.wav

# --- 3. Hot stereo (normalized to -5 LUFS) -> FAIL loudness
ffmpeg -nostdin -y -loglevel error -i raw_stereo.wav -vn -af "loudnorm=I=-5:TP=-0.5:LRA=11" hot.wav 2>/dev/null || \
ffmpeg -nostdin -y -loglevel error -i raw_stereo.wav -vn -af "volume=12dB" hot.wav

# --- 4. Good 16:9 video: 4 x 3s color segments (cuts at 3s, no freeze >= 4s)
# NOTE: colors must differ in LUMA -- the scene detector is luma-based,
# and pure red vs pure green have nearly identical luma (76 vs 75).
for c in black white red blue; do
  ffmpeg -nostdin -y -loglevel error -f lavfi -i "color=c=$c:s=640x360:d=3:r=30" -an "seg_$c.mp4"
done
printf "file 'seg_black.mp4'\nfile 'seg_white.mp4'\nfile 'seg_red.mp4'\nfile 'seg_blue.mp4'\n" > concat_good.txt
ffmpeg -nostdin -y -loglevel error -f concat -safe 0 -i concat_good.txt -i good_stereo.wav \
  -map 0:v -map 1:a -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k \
  -shortest good_16x9.mp4
printf '1\n00:00:00,000 --> 00:00:04,000\nTest voiceover line one\n\n2\n00:00:04,000 --> 00:00:08,000\nTest voiceover line two\n' > good_16x9.srt

# --- 5. Bad videos
ffmpeg -nostdin -y -loglevel error -f lavfi -i "color=c=red:s=640x360:d=10:r=30" -i mono.wav \
  -map 0:v -map 1:a -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest bad_static_mono.mp4
ffmpeg -nostdin -y -loglevel error -f lavfi -i "color=c=red:s=640x480:d=6:r=30" -i good_stereo.wav \
  -map 0:v -map 1:a -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest bad_aspect.mp4
ffmpeg -nostdin -y -loglevel error -f lavfi -i "color=c=blue:s=640x360:d=6:r=30" -i hot.wav \
  -map 0:v -map 1:a -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest bad_hot.mp4

# --- 6. Scene clips for assembly + VO/bed for ducking
# scene1 audio = loud block (0-3 s), scene2 audio = quiet block (4-7 s):
# the assembled file must then carry REAL dynamics (LRA >= 6).
ffmpeg -nostdin -y -loglevel error -f lavfi -i "testsrc=duration=3:size=640x360:rate=30" -i good_stereo.wav \
  -map 0:v -map 1:a -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest scene1.mp4
ffmpeg -nostdin -y -loglevel error -f lavfi -i "testsrc=duration=3:size=640x360:rate=30" -ss 4 -i good_stereo.wav \
  -map 0:v -map 1:a -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest scene2.mp4
ffmpeg -nostdin -y -loglevel error -f lavfi -i "sine=frequency=660:duration=6" -ac 2 vo.wav
ffmpeg -nostdin -y -loglevel error -f lavfi -i "sine=frequency=220:duration=10" -ac 2 bed.wav
printf '1\n00:00:00,000 --> 00:00:02,000\nHello world test\n\n2\n00:00:02,000 --> 00:00:04,000\nSecond caption line\n' > sample.srt

echo "== free scripts =="
expect_ok "audio_lufs_check PASS on mastered stereo" \
  $PY "$ROOT/scripts/audio_lufs_check.py" good_stereo.wav
expect_exit 1 "audio_lufs_check FAIL on mono" \
  $PY "$ROOT/scripts/audio_lufs_check.py" mono.wav
expect_exit 1 "audio_lufs_check FAIL on hot (-5 LUFS)" \
  $PY "$ROOT/scripts/audio_lufs_check.py" hot.wav
expect_ok "extract_frames_check PASS on good 16:9 (cuts 3s)" \
  $PY "$ROOT/scripts/extract_frames_check.py" good_16x9.mp4 --aspect 16:9 --frames-dir frames_out
[ -f frames_out/frame_00_02.png ] && [ -f frames_out/frame_mid.png ] && [ -f frames_out/frame_end.png ] \
  && ok "check frames extracted (00:02/mid/end)" || bad "check frames extracted (00:02/mid/end)"
expect_exit 1 "extract_frames_check FAIL on static 10s video" \
  $PY "$ROOT/scripts/extract_frames_check.py" bad_static_mono.mp4 --aspect 16:9
expect_exit 1 "extract_frames_check FAIL on 4:3 video vs 16:9 lock" \
  $PY "$ROOT/scripts/extract_frames_check.py" bad_aspect.mp4 --aspect 16:9
expect_ok "quality_gate PASS on good file" \
  $PY "$ROOT/scripts/quality_gate.py" good_16x9.mp4 --aspect 16:9 --attest-real-audio --frames-dir gate_frames
expect_exit 1 "quality_gate FAIL on mono+static file" \
  $PY "$ROOT/scripts/quality_gate.py" bad_static_mono.mp4 --aspect 16:9 --attest-real-audio
expect_exit 1 "quality_gate FAIL on hot-loudness file" \
  $PY "$ROOT/scripts/quality_gate.py" bad_hot.mp4 --aspect 16:9 --attest-real-audio

echo "== pro scripts =="
expect_ok "assemble_multiscene joins 2 scenes" \
  $PY "$ROOT/pro-bundle/scripts/assemble_multiscene.py" scene1.mp4 scene2.mp4 \
  --aspect 16:9 --width 640 --height 360 --out assembled.mp4
[ -f assembled.mp4 ] && ok "assembled.mp4 exists" || bad "assembled.mp4 exists"
DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 assembled.mp4)
python3 -c "import sys; sys.exit(0 if 5.5 <= float('$DUR') <= 6.5 else 1)" \
  && ok "assembled duration ~6s ($DUR)" || bad "assembled duration ~6s ($DUR)"
expect_ok "assembled output passes full audio gate (stereo + -15 LUFS + LRA)" \
  $PY "$ROOT/scripts/audio_lufs_check.py" assembled.mp4
expect_ok "auto_duck_mix VO + bed" \
  $PY "$ROOT/pro-bundle/scripts/auto_duck_mix.py" --vo vo.wav --bed bed.wav --out mix.wav
CH=$(ffprobe -v error -select_streams a:0 -show_entries stream=channels -of default=noprint_wrappers=1:nokey=1 mix.wav)
[ "$CH" = "2" ] && ok "ducked mix is stereo" || bad "ducked mix is stereo (got $CH)"
# Ducking proof: gapped VO (2s on / 2s off / 2s on) + bed.
# The 220 Hz bed must be MUCH quieter while the 660 Hz VO speaks than
# in the gap. FFT magnitudes per 1 s window, via the faster-whisper venv.
ffmpeg -nostdin -y -loglevel error -i vo.wav -af "volume='if(lt(mod(t,4),2),1,0)':eval=frame" -ac 2 vo_gap.wav
expect_ok "auto_duck_mix with gapped VO" \
  $PY "$ROOT/pro-bundle/scripts/auto_duck_mix.py" --vo vo_gap.wav --bed bed.wav --out duck_gap.wav
ffmpeg -nostdin -y -loglevel error -i duck_gap.wav -ac 1 -ar 48000 -f f32le duck_gap.raw
"$STT" - "$TMP" <<'EOF'
import numpy as np, sys
pcm = np.fromfile(sys.argv[1] + '/duck_gap.raw', dtype=np.float32)
sr = 48000
def mag_at(t0, freq):
    seg = pcm[int(t0*sr):int((t0+1)*sr)]
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    freqs = np.fft.rfftfreq(len(seg), 1/sr)
    return spec[np.argmin(np.abs(freqs - freq))]
bed_on  = mag_at(1.0, 220)   # VO speaking -> bed must be ducked
bed_off = mag_at(3.0, 220)   # VO gap -> bed at full -20 dB
vo_on   = mag_at(1.0, 660)   # VO present (sanity)
print('bed@220Hz VO-on=%.1f VO-off=%.1f ratio=%.2f vo@660Hz=%.1f' % (bed_on, bed_off, bed_on/max(bed_off,1e-9), vo_on))
sys.exit(0 if bed_on < 0.5 * bed_off and vo_on > 10 * bed_on else 1)
EOF
[ $? = 0 ] && ok "sidechain ducking verified (bed drops under VO)" || bad "sidechain ducking verified (bed drops under VO)"
expect_ok "auto_duck_mix mux into video" \
  $PY "$ROOT/pro-bundle/scripts/auto_duck_mix.py" --vo vo.wav --bed bed.wav --video assembled.mp4 --out mixed.mp4
expect_ok "caption_builder burn from provided SRT" \
  $PY "$ROOT/pro-bundle/scripts/caption_builder.py" --srt sample.srt \
  --burn assembled.mp4 --burn-out captioned.mp4 --style shorts
[ -f captioned.mp4 ] && ok "captioned.mp4 exists" || bad "captioned.mp4 exists"
expect_ok "caption_builder transcribe tone audio (faster-whisper, no crash)" \
  $STT "$ROOT/pro-bundle/scripts/caption_builder.py" --audio vo.wav --out transcribed.srt --model tiny
[ -f transcribed.srt ] && ok "transcribed.srt exists" || bad "transcribed.srt exists"
mkdir -p batch_in && cp good_16x9.mp4 batch_in/good.mp4 && cp good_16x9.srt batch_in/good.srt && cp bad_static_mono.mp4 batch_in/bad.mp4
expect_exit 1 "batch_gate reports 1/2 FAIL (exit 1)" \
  $PY "$ROOT/pro-bundle/scripts/batch_gate.py" batch_in --aspect 16:9 \
  --report batch_report.md --json batch_report.json
[ -f batch_report.md ] && grep -q "1/2 PASSED" batch_report.md \
  && ok "batch report written (1/2 PASSED)" || bad "batch report written (1/2 PASSED)"

echo ""
echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" = 0 ]
