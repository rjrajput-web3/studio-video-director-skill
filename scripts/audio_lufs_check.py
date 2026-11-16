#!/usr/bin/env python3
"""Audio loudness + stereo quality gate (FREE tier).

Checks a final video/audio file against the Studio Video Director
quality gates (Section 4 of the pipeline standards):

  * audio MUST be stereo (channels == 2) -- mono is a FAILED build
  * integrated loudness MUST be -14 to -16 LUFS (target -15)
  * true peak MUST be <= -1.5 dBTP (hard fail)
  * loudness range (LRA) MUST be >= 6 LU (over-compressed mixes fail)

Measurement uses ffmpeg's EBU R128 loudnorm filter in single-pass
measure mode -- no audio is written, nothing is uploaded, no network
is used. Only ffprobe/ffmpeg subprocesses run locally.

Usage:
    audio_lufs_check.py FILE [--target -15] [--min -16] [--max -14]
                             [--tp -1.5] [--lra-min 6] [--json]

Exit codes: 0 = PASS, 1 = FAIL, 2 = error (missing file, no audio, ...).
"""

import argparse
import json
import math
import subprocess
import sys


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe_audio(path):
    """Return ffprobe audio-stream info, or raise RuntimeError."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_name,sample_rate,channels,channel_layout",
        "-show_entries", "format=duration",
        "-of", "json", path,
    ]
    r = _run(cmd)
    if r.returncode != 0:
        raise RuntimeError("ffprobe failed: %s" % (r.stderr.strip() or "unknown error"))
    data = json.loads(r.stdout)
    streams = data.get("streams", [])
    if not streams:
        raise RuntimeError("no audio stream found")
    info = dict(streams[0])
    info["duration"] = float(data.get("format", {}).get("duration") or 0)
    return info


def _parse_loudnorm_json(stderr):
    """Extract the loudnorm JSON block ffmpeg prints to stderr."""
    start = stderr.find("{")
    end = stderr.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(stderr[start:end + 1])
    except json.JSONDecodeError:
        return None


def measure_loudness(path, target=-15.0, tp=-1.5, lra=11.0):
    """Run loudnorm in measure mode. Returns the parsed JSON dict."""
    cmd = [
        "ffmpeg", "-nostdin", "-i", path, "-vn",
        "-af", "loudnorm=I=%s:TP=%s:LRA=%s:print_format=json" % (target, tp, lra),
        "-f", "null", "-",
    ]
    r = _run(cmd)
    parsed = _parse_loudnorm_json(r.stderr)
    if parsed is None:
        raise RuntimeError(
            "could not measure loudness (silent, corrupt, or unsupported audio)")
    return parsed


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def check(path, target=-15.0, lo=-16.0, hi=-14.0, tp=-1.5, lra_min=6.0):
    """Run every audio check. Returns a dict with per-check results."""
    result = {"file": path, "checks": {}, "passed": True}
    try:
        info = probe_audio(path)
    except RuntimeError as exc:
        result["error"] = str(exc)
        result["passed"] = False
        return result
    result["audio"] = {
        "codec": info.get("codec_name"),
        "sample_rate": info.get("sample_rate"),
        "channels": info.get("channels"),
        "channel_layout": info.get("channel_layout"),
        "duration": info.get("duration"),
    }

    channels = info.get("channels")
    ok_stereo = channels == 2
    result["checks"]["stereo_channels_2"] = {
        "passed": bool(ok_stereo),
        "detail": "channels=%s (need 2)" % channels,
    }

    try:
        loud = measure_loudness(path, target=target, tp=tp)
    except RuntimeError as exc:
        result["error"] = str(exc)
        result["passed"] = False
        return result
    integrated = _to_float(loud.get("input_i"))
    true_peak = _to_float(loud.get("input_tp"))
    lra_val = _to_float(loud.get("input_lra"))
    result["loudness"] = {
        "integrated_lufs": integrated,
        "true_peak_dbtp": true_peak,
        "lra_lu": lra_val,
    }
    ok_lufs = (not math.isnan(integrated)) and lo <= integrated <= hi
    result["checks"]["integrated_lufs_%s_to_%s" % (lo, hi)] = {
        "passed": bool(ok_lufs),
        "detail": "measured %.2f LUFS" % integrated if not math.isnan(integrated)
                   else "unmeasurable (silent?)",
    }
    ok_tp = (not math.isnan(true_peak)) and true_peak <= tp
    result["checks"]["true_peak_le_%s_dbtp" % tp] = {
        "passed": bool(ok_tp),
        "detail": "measured %.2f dBTP" % true_peak if not math.isnan(true_peak)
                   else "unmeasurable",
    }
    ok_lra = (not math.isnan(lra_val)) and lra_val >= lra_min
    result["checks"]["lra_ge_%s_lu" % lra_min] = {
        "passed": bool(ok_lra),
        "detail": "measured %.2f LU" % lra_val if not math.isnan(lra_val)
                   else "unmeasurable",
    }
    result["passed"] = all(c["passed"] for c in result["checks"].values())
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("file", help="video or audio file to check")
    p.add_argument("--target", type=float, default=-15.0)
    p.add_argument("--min", dest="lo", type=float, default=-16.0)
    p.add_argument("--max", dest="hi", type=float, default=-14.0)
    p.add_argument("--tp", type=float, default=-1.5,
                   help="true-peak ceiling in dBTP")
    p.add_argument("--lra-min", type=float, default=6.0)
    p.add_argument("--json", action="store_true", help="print JSON report")
    args = p.parse_args(argv)

    result = check(args.file, target=args.target, lo=args.lo, hi=args.hi,
                   tp=args.tp, lra_min=args.lra_min)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if "error" in result:
            print("ERROR: %s" % result["error"])
        for name, c in result.get("checks", {}).items():
            print("%s %s -- %s" % ("PASS" if c["passed"] else "FAIL", name, c["detail"]))
        loud = result.get("loudness", {})
        if loud:
            print("measured: %.2f LUFS integrated, %.2f dBTP, %.2f LU LRA"
                  % (loud.get("integrated_lufs", float("nan")),
                     loud.get("true_peak_dbtp", float("nan")),
                     loud.get("lra_lu", float("nan"))))
        print("RESULT: %s" % ("PASS" if result["passed"] else "FAIL"))
    if "error" in result and not result.get("checks"):
        return 2
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
