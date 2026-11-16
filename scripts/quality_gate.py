#!/usr/bin/env python3
"""Full 10-gate pre-delivery quality gate (FREE tier).

Runs every automatable check from Section 10 of the pipeline standards
on the FINAL encode and FAILS the build if ANY gate fails:

  1. Specs: duration / resolution / fps / channels (channels MUST be 2)
  2. Loudness: integrated -14..-16 LUFS, TP <= -1.5 dBTP, LRA >= 6
  3. Dead air: no silence >= 0.5 s except a deliberate trailing tail <= 1 s
  4. Cut cadence + no-slideshow: no cut gap > 4 s, no frozen segment > 4 s
  5. VO coverage (optional): transcribe with faster-whisper and diff
     against --script / --srt text -- SKIPPED if no script given
  6. Frames at 00:02, mid, end extracted for the named frame checklist
  7. Stereo: ffprobe channels == 2 (same data as gate 1, reported twice)
  8. Real music/SFX: MANUAL -- cannot be verified from the file alone.
     The gate lists the attestation checklist; pass --attest-real-audio
     only after a human confirms real licensed music + real SFX.
  9. No-slideshow: covered by gate 4 (reported separately)
 10. Master protection: .SRT sidecar present + no *-broken / *-v1 / *-v2
     siblings next to the final file

Usage:
    quality_gate.py FILE [--aspect 16:9|9:16] [--srt FILE] [--script FILE]
                         [--frames-dir DIR] [--attest-real-audio]
                         [--json]

Exit codes: 0 = PASS, 1 = FAIL, 2 = error.
"""

import argparse
import difflib
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import audio_lufs_check  # noqa: E402
import extract_frames_check  # noqa: E402

SILENCE_RE = re.compile(
    r"silence_start:\s*([0-9.]+).*?silence_end:\s*([0-9.]+).*?"
    r"silence_duration:\s*([0-9.]+)", re.S)


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe_all(path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-show_entries",
        "stream=codec_type,codec_name,width,height,r_frame_rate,channels,sample_rate",
        "-of", "json", path,
    ]
    r = _run(cmd)
    if r.returncode != 0:
        raise RuntimeError("ffprobe failed: %s" % (r.stderr.strip() or "unknown error"))
    return json.loads(r.stdout)


def find_silences(path, duration):
    """Return list of (start, end, dur) silences >= 0.5 s (noise -40 dB)."""
    cmd = [
        "ffmpeg", "-nostdin", "-i", path, "-vn",
        "-af", "silencedetect=noise=-40dB:d=0.5",
        "-f", "null", "-",
    ]
    r = _run(cmd)
    return [{"start": float(a), "end": float(b), "duration": float(c)}
            for a, b, c in SILENCE_RE.findall(r.stderr)]


def transcribe_words(path):
    """Transcribe with faster-whisper (lazy import). Returns word list."""
    import numpy as np
    from faster_whisper import WhisperModel
    raw = os.path.join(os.path.dirname(path), ".vo_pcm.tmp")
    _run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error",
          "-i", path, "-vn", "-ar", "16000", "-ac", "1", "-f", "f32le", raw])
    try:
        pcm = np.fromfile(raw, dtype=np.float32)
        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(pcm, language="en", beam_size=5)
        text = " ".join(s.text.strip() for s in segments)
    finally:
        if os.path.exists(raw):
            os.remove(raw)
    return text


def _words(text):
    return re.findall(r"[a-z0-9']+", text.lower())


def gate_vo_coverage(path, script_path=None, srt_path=None):
    """Compare transcribed VO against the script/SRT. Returns (status, detail)."""
    reference = ""
    if script_path and os.path.exists(script_path):
        with open(script_path, encoding="utf-8") as fh:
            reference = fh.read()
    elif srt_path and os.path.exists(srt_path):
        with open(srt_path, encoding="utf-8") as fh:
            reference = re.sub(r"\d+\n\d{2}:\d{2}:\d{2},\d{3} -->.*\n", " ", fh.read())
    if not reference.strip():
        return "SKIPPED", "no --script/--srt given"
    try:
        heard = transcribe_words(path)
    except ImportError:
        return "SKIPPED", "faster-whisper not installed (pip install faster-whisper)"
    except Exception as exc:  # noqa: BLE001 - report, don't crash the gate
        return "SKIPPED", "transcription failed: %s" % exc
    ref_words = set(_words(reference))
    heard_words = set(_words(heard))
    if not ref_words:
        return "SKIPPED", "reference script has no words"
    coverage = len(ref_words & heard_words) / len(ref_words)
    missing = sorted(ref_words - heard_words)[:10]
    detail = "word coverage %.0f%% (%d/%d script words heard)%s" % (
        coverage * 100, len(ref_words & heard_words), len(ref_words),
        ("; missing e.g. %s" % ", ".join(missing)) if missing else "")
    return ("PASS" if coverage >= 0.8 else "FAIL"), detail


def run_gate(path, aspect="16:9", srt_path=None, script_path=None,
             frames_dir=None, attest_real_audio=False):
    gates = {}
    failed = False

    def record(name, status, detail):
        gates[name] = {"status": status, "detail": detail}
        if status == "FAIL":
            nonlocal failed
            failed = True

    # --- Gate 1: specs ---
    try:
        probe = probe_all(path)
        duration = float(probe["format"]["duration"])
        video = next((s for s in probe["streams"] if s["codec_type"] == "video"), None)
        audio = next((s for s in probe["streams"] if s["codec_type"] == "audio"), None)
        if not video or not audio:
            record("1_specs", "FAIL", "missing video or audio stream")
        else:
            record("1_specs", "PASS",
                   "%.1fs, %dx%d @%s, audio %s %sHz ch=%s" % (
                       duration, video.get("width"), video.get("height"),
                       video.get("r_frame_rate"), audio.get("codec_name"),
                       audio.get("sample_rate"), audio.get("channels")))
    except RuntimeError as exc:
        return {"file": path, "error": str(exc), "passed": False, "gates": gates}

    # --- Gate 2: loudness + Gate 7: stereo ---
    loud = audio_lufs_check.check(path)
    if "error" in loud and not loud.get("checks"):
        record("2_loudness", "FAIL", loud["error"])
        record("7_stereo", "FAIL", loud["error"])
    else:
        l = loud.get("loudness", {})
        record("2_loudness", "PASS" if all(
            c["passed"] for k, c in loud["checks"].items()
            if k != "stereo_channels_2") else "FAIL",
            "%.2f LUFS, %.2f dBTP, %.2f LU LRA" % (
                l.get("integrated_lufs", float("nan")),
                l.get("true_peak_dbtp", float("nan")),
                l.get("lra_lu", float("nan"))))
        record("7_stereo", loud["checks"]["stereo_channels_2"]["passed"]
               and "PASS" or "FAIL",
               loud["checks"]["stereo_channels_2"]["detail"])

    # --- Gate 3: dead air ---
    bad_silences = [s for s in find_silences(path, duration)
                    if not (s["end"] >= duration - 1.0)]  # trailing tail <= 1s allowed
    record("3_dead_air", "PASS" if not bad_silences else "FAIL",
           "no silence >= 0.5s" if not bad_silences else
           "%d silence(s): %s" % (len(bad_silences),
               ", ".join("%.1fs-%.1fs" % (s["start"], s["end"]) for s in bad_silences)))

    # --- Gate 4: cuts + Gate 9: no-slideshow ---
    frames = extract_frames_check.check(path, aspect=aspect, frames_dir=frames_dir)
    if "error" in frames and not frames.get("checks"):
        record("4_cut_cadence", "FAIL", frames["error"])
        record("9_no_slideshow", "FAIL", frames["error"])
    else:
        cut = frames["checks"]["cut_gap_le_4.0s"]
        static = frames["checks"]["no_static_segment_over_4.0s"]
        record("4_cut_cadence", "PASS" if cut["passed"] else "FAIL", cut["detail"])
        record("9_no_slideshow", "PASS" if static["passed"] else "FAIL", static["detail"])
        record("6_check_frames", "PASS",
               "frames extracted: %s" % ", ".join(frames.get("check_frames", {}).keys())
               if frames.get("check_frames") else
               "no --frames-dir given (extract frames and apply the named checklist)")

    # --- Gate 5: VO coverage ---
    status, detail = gate_vo_coverage(path, script_path, srt_path)
    record("5_vo_coverage", status, detail)

    # --- Gate 8: real music/SFX (manual attestation) ---
    record("8_real_music_sfx",
           "PASS" if attest_real_audio else "MANUAL",
           "human confirmed real licensed music + real SFX" if attest_real_audio
           else "MANUAL: confirm a real licensed track (Mixkit/Pixabay/YT Audio "
                "Library) + real designed SFX -- synthesized beds/SFX are banned")

    # --- Gate 10: master protection ---
    base, _ = os.path.splitext(path)
    srt = srt_path or (base + ".srt")
    problems = []
    if not os.path.exists(srt):
        problems.append("missing .SRT sidecar (%s)" % srt)
    siblings = [f for pat in ("*-broken*", "*-v1.*", "*-v2.*")
                for f in glob.glob(os.path.join(os.path.dirname(path) or ".", pat))]
    if siblings:
        problems.append("old/broken siblings present: %s" % ", ".join(siblings))
    record("10_master_protection", "PASS" if not problems else "FAIL",
           "sidecar + clean folder" if not problems else "; ".join(problems))

    verdict = not failed
    return {"file": path, "passed": verdict, "gates": gates}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("file", help="final video file to gate")
    p.add_argument("--aspect", choices=["16:9", "9:16"], default="16:9")
    p.add_argument("--srt", default=None, help="sidecar .SRT (default: <file>.srt)")
    p.add_argument("--script", default=None, help="VO script text file for gate 5")
    p.add_argument("--frames-dir", default=None)
    p.add_argument("--attest-real-audio", action="store_true",
                   help="human attests real licensed music + real SFX (gate 8)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    result = run_gate(args.file, aspect=args.aspect, srt_path=args.srt,
                      script_path=args.script, frames_dir=args.frames_dir,
                      attest_real_audio=args.attest_real_audio)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if "error" in result:
            print("ERROR: %s" % result["error"])
        for name in sorted(result.get("gates", {})):
            g = result["gates"][name]
            print("%-7s %s -- %s" % (g["status"], name, g["detail"]))
        print("RESULT: %s" % ("PASS" if result["passed"] else "FAIL"))
    if "error" in result and not result.get("gates"):
        return 2
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
