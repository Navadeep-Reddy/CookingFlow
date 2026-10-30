#!/usr/bin/env python3
"""Render source-sample LUT trials using the exact final-render grading path.

python3 tools/grade_preview.py Clips/example.mp4 --start 12 --duration 2 \
    --lut assets/luts/look.cube --strength 0 --strength .05 --strength .15

Strength means intended LUT contribution, not the installed script's raw flag.
The manifest records both, actual commands, source/LUT identities and output
hashes. Outputs use the shared render cache; changing strength reuses the cut.
Inspect the output PNGs before choosing a look. This helper makes no aesthetic
decision, changes no grade handoff, and never overwrites source media.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
from pathlib import Path
import subprocess
import sys
import time

try:
    from . import render_edit as R
except ImportError:
    import render_edit as R

E = R.E
PRODUCER = "reel-grade-preview"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source")
    parser.add_argument("--lut", required=True)
    parser.add_argument("--strength", type=float, action="append", required=True)
    parser.add_argument("--start", type=float, default=0)
    parser.add_argument("--duration", type=float, default=2.5)
    parser.add_argument("--root", type=Path, default=E.ROOT)
    parser.add_argument("--cache", default="workdir/render-cache")
    parser.add_argument("--out", default="workdir/grade-preview")
    args = parser.parse_args(argv)
    started, out = time.monotonic(), None
    try:
        engine = R.Runner(args.root, args.cache)
        destination = engine.generated(args.out)
        destination.mkdir(parents=True, exist_ok=True)
        with E.lock(destination / ".lock"):
            owner = destination / ".owner"
            if (owner.exists() and owner.read_text() != PRODUCER or not owner.exists() and
                    any(p.name != ".lock" for p in destination.iterdir())):
                raise ValueError("Refusing to replace a non-owned report directory")
            E.atomic_text(owner, PRODUCER)
            out = destination
            grade = dict(status="complete", lut_path=args.lut, strength=0)
            for strength in args.strength:
                R.validate_grade(grade | {"strength": strength}, [], engine)
            source, stamp, meta = engine.probe(args.source)
            lut_stamp = E.identity(engine.source(args.lut))
            rate = E.frame_rate(meta)
            if meta["video"].get("bt2020_or_hdr"):
                raise ValueError("Prepare HDR/wide-gamut sources to SDR before LUT previews")
            start, stop = args.start, args.start + args.duration
            first, end = R.frame_index(start, rate), R.frame_index(stop, rate)
            if end <= first or stop > float(meta["video"].get("duration") or meta["duration"]):
                raise ValueError("Preview range must be nonempty and within source picture duration")
            expected = dict(nb_frames=end - first, fps=float(rate))
            sample, _ = engine.step("preview-cut", "cut", [source, "--start", start, "--end", stop,
                                    "--accurate", "--quality", 18, "--preset", "ultrafast"],
                                    [source], expected=expected)
            previews = []
            for strength in dict.fromkeys(args.strength):
                output = engine.apply_grade(f"preview-{strength:g}", sample,
                                             grade | {"strength": strength}, expected)
                _, output_stamp, output_meta = engine.probe(output)
                middle = float(Fraction((end - first - 1) // 2, 1) / rate)
                image = engine.frames(output, output_stamp, [middle], 540)[E.seek_ms(middle)]
                step = next((s for s in reversed(engine.steps) if s.get("output") == str(output)
                             and s.get("tool") == "color"), {})
                previews.append(dict(strength=strength, executed_lut_flag=step.get("executed_lut_flag"),
                                     output=str(output), sha256=E.file_hash(output), image=str(image),
                                     image_sha256=E.file_hash(image), probe=output_meta,
                                     sample_time_seconds=middle, unchanged=strength == 0))
            if E.identity(source) != stamp or E.identity(engine.source(args.lut)) != lut_stamp:
                raise ValueError("Source or LUT changed during preview generation")
            manifest = dict(producer=PRODUCER, status="completed", source=stamp, lut=lut_stamp,
                            source_range=dict(start=start, end=stop), previews=previews,
                            lut_compatibility=engine.lut_compatibility, tool_fingerprint=engine.version,
                            steps=engine.steps, commands=engine.commands,
                            elapsed_seconds=time.monotonic() - started, visual_review="pending")
            E.publish_run(out, manifest)
            print(json.dumps(dict(status="completed", manifest=str(out / "manifest.json"),
                                  previews=[{k: p[k] for k in ("strength", "executed_lut_flag", "output", "image")}
                                            for p in previews], visual_review="pending"), indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, subprocess.TimeoutExpired) as exc:
        if out:
            E.publish_run(out, dict(producer=PRODUCER, status="failed", error=str(exc),
                                   steps=engine.steps, commands=engine.commands,
                                   elapsed_seconds=time.monotonic() - started))
        print(json.dumps(dict(status="failed", error=str(exc))), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
