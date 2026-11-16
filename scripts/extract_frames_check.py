#!/usr/bin/env python3
"""Frame / motion / aspect-ratio quality gate (FREE tier).

Checks a final video against the Studio Video Director quality gates
(Sections 1, 5 and 8 of the pipeline standards):

  * aspect ratio MUST match the locked ratio (16:9 or 9:16, within 1%)
  * NO static/frozen segment longer than --max-gap seconds
    (ffmpeg freezedetect -- a still image held on screen is a slideshow)
  * NO gap between visual cuts longer than --max-gap seconds
    (ffmpeg scene-change detection -- motion/cut at least every 3-4 s)
  * extracts verification frames at 00:02, middle and end for the
    named frame checklist (clipping, dead space, readability, captions,
    placeholders, subject fills frame)

Only ffprobe/ffmpeg subprocesses run locally. No network, no uploads.

Usage:
    extract_frames_check.py FILE [--aspect 16:9|9:16] [--max-gap 4]
                                 [--frames-dir DIR] [--json]

Exit codes: 0 = PASS, 1 = FAIL, 2 = error.
"""

import argparse
import json
import os
import re
import subprocess
import sys

SCENE_RE = re.compile(r"showinfo.*pts_time:([0-9.]+)")
FREEZE_RE = re.compile(r"freeze_duration:\s*([0-9.]+).*?freeze_start:\s*([0-9.]+)")


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe_video(path):
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height,r_frame_rate,avg_frame_rate",
        "-show_entries", "format=duration",
        "-of", "json", path,
    ]
    r = _run(cmd)
    if r.returncode != 0:
        raise RuntimeError("ffprobe failed: %s" % (r.stderr.strip() or "unknown error"))
    data = json.loads(r.stdout)
    streams = data.get("streams", [])
    if not streams:
        raise RuntimeError("no video stream found")
    info = dict(streams[0])
    info["duration"] = float(data.get("format", {}).get("duration") or 0)
    return info


def find_freezes(path, max_gap):
    """Return list of (start, duration) frozen segments >= max_gap seconds."""
    cmd = [
        "ffmpeg", "-nostdin", "-i", path,
        "-vf", "freezedetect=n=0.003:d=%s" % max_gap,
        "-f", "null", "-",
    ]
    r = _run(cmd)
    freezes = []
    for m in FREEZE_RE.finditer(r.stderr):
        freezes.append({"start": float(m.group(2)), "duration": float(m.group(1))})
    return freezes


def find_cuts(path, threshold=0.15):
    """Return sorted list of scene-cut timestamps (seconds)."""
    cmd = [
        "ffmpeg", "-nostdin", "-i", path,
        "-vf", "select='gt(scene,%s)',showinfo" % threshold,
        "-f", "null", "-",
    ]
    r = _run(cmd)
    cuts = sorted({float(m.group(1)) for m in SCENE_RE.finditer(r.stderr)})
    return cuts


def max_cut_gap(cuts, duration):
    """Largest gap between cuts, including start (0) and end (duration)."""
    points = [0.0] + [c for c in cuts if 0.0 < c < duration] + [duration]
    gaps = [(points[i + 1] - points[i], points[i], points[i + 1])
            for i in range(len(points) - 1)]
    return max(gaps) if gaps else (0.0, 0.0, 0.0)


def extract_check_frames(path, out_dir, duration):
    """Extract 00:02, middle and end frames for the named checklist."""
    os.makedirs(out_dir, exist_ok=True)
    times = {"frame_00_02": 2.0, "frame_mid": duration / 2.0,
             "frame_end": max(duration - 0.1, 0.0)}
    written = {}
    for name, t in times.items():
        out = os.path.join(out_dir, "%s.png" % name)
        r = _run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error",
                  "-ss", str(t), "-i", path, "-frames:v", "1", out])
        if r.returncode == 0 and os.path.exists(out):
            written[name] = out
    return written


def check(path, aspect="16:9", max_gap=4.0, frames_dir=None):
    result = {"file": path, "aspect_lock": aspect, "checks": {}, "passed": True}
    try:
        info = probe_video(path)
    except RuntimeError as exc:
        result["error"] = str(exc)
        result["passed"] = False
        return result
    width, height = int(info["width"]), int(info["height"])
    duration = info["duration"]
    result["video"] = {
        "codec": info.get("codec_name"),
        "width": width, "height": height,
        "duration": duration,
        "frame_rate": info.get("r_frame_rate") or info.get("avg_frame_rate"),
    }

    want = 16.0 / 9.0 if aspect == "16:9" else 9.0 / 16.0
    actual = width / height if height else 0.0
    ok_aspect = abs(actual - want) / want <= 0.01
    result["checks"]["aspect_ratio_%s" % aspect] = {
        "passed": bool(ok_aspect),
        "detail": "%dx%d = %.3f (want %.3f)" % (width, height, actual, want),
    }

    freezes = find_freezes(path, max_gap)
    result["freezes"] = freezes
    result["checks"]["no_static_segment_over_%ss" % max_gap] = {
        "passed": len(freezes) == 0,
        "detail": ("no frozen segment >= %ss" % max_gap) if not freezes
                  else "%d frozen segment(s): %s" % (
                      len(freezes),
                      ", ".join("%.1fs@%.1fs" % (f["duration"], f["start"])
                                for f in freezes)),
    }

    cuts = find_cuts(path)
    gap, gap_start, gap_end = max_cut_gap(cuts, duration)
    result["cuts"] = cuts
    result["checks"]["cut_gap_le_%ss" % max_gap] = {
        "passed": gap <= max_gap,
        "detail": "%d cuts, max gap %.2fs (%.2fs-%.2fs)" % (len(cuts), gap, gap_start, gap_end),
    }

    if frames_dir:
        result["check_frames"] = extract_check_frames(path, frames_dir, duration)
    result["passed"] = all(c["passed"] for c in result["checks"].values())
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("file", help="video file to check")
    p.add_argument("--aspect", choices=["16:9", "9:16"], default="16:9",
                   help="locked aspect ratio")
    p.add_argument("--max-gap", type=float, default=4.0,
                   help="max seconds allowed without a cut / frozen frame")
    p.add_argument("--frames-dir", default=None,
                   help="extract 00:02 / mid / end frames here for the checklist")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    result = check(args.file, aspect=args.aspect, max_gap=args.max_gap,
                   frames_dir=args.frames_dir)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if "error" in result:
            print("ERROR: %s" % result["error"])
        for name, c in result.get("checks", {}).items():
            print("%s %s -- %s" % ("PASS" if c["passed"] else "FAIL", name, c["detail"]))
        for name, f in result.get("check_frames", {}).items():
            print("frame %s -> %s (apply the named frame checklist)" % (name, f))
        print("RESULT: %s" % ("PASS" if result["passed"] else "FAIL"))
    if "error" in result and not result.get("checks"):
        return 2
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
