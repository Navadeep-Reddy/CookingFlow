#!/usr/bin/env python3
"""Time a saved edit with isolated baseline/optimized caches, then a warm repeat.

python3 tools/benchmark_render.py workdir/plan.json --framing workdir/framing.json \
    --grade workdir/grade.json --audio-policy workdir/audio-policy.json

Uses the same sources, editorial decisions, grade, mix, CRFs, and presets. Baseline
always fits every shot (the previous structure); optimized defers normal-speed
resize to join and corrects AAC-tail speed inference. Both honor the current
no-ending-music-fade policy. This measures mechanical execution of saved choices,
not the time a person/agent spends making new editorial decisions. Wall times
include subprocess/Python startup. Runs are sequential to avoid contention.
Each invocation gets a fresh workdir job; partial results remain resumable through
the recorded render commands. JSON/Markdown reports and visual evidence are kept.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

try:
    from . import evidence as E
except ImportError:
    import evidence as E


def call(command, root, report):
    start = time.monotonic()
    p = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=3600)
    record = dict(command=list(map(str, command)), wall_seconds=time.monotonic() - start,
                  returncode=p.returncode, stdout=p.stdout, stderr=p.stderr)
    E.atomic_json(report, record)
    if p.returncode:
        raise ValueError(f"Command failed; details saved in {report}: {p.stdout}\n{p.stderr}")
    return json.loads(p.stdout), record["wall_seconds"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plan")
    parser.add_argument("--framing", required=True)
    parser.add_argument("--grade", required=True)
    parser.add_argument("--audio-policy", required=True)
    parser.add_argument("--footage")
    parser.add_argument("--root", type=Path, default=E.ROOT)
    parser.add_argument("--out", default="workdir/render-benchmark")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        base = (root / args.out).resolve()
        if not base.is_relative_to((root / "workdir").resolve()) or base == (root / "workdir").resolve():
            raise ValueError("Benchmark outputs must be inside workdir")
        job = base / str(time.time_ns())
        job.mkdir(parents=True)
        common = [args.plan, "--root", str(root), "--framing", args.framing, "--grade", args.grade,
                  "--audio-policy", args.audio_policy, "--audio-evidence"]
        if args.footage:
            common += ["--footage", args.footage]
        results = {}
        for name, mode in (("baseline", "baseline"), ("optimized", "optimized"), ("warm", "optimized")):
            group = "optimized" if name == "warm" else name
            command = [sys.executable, str(root / "tools/render_edit.py"), *common,
                       "--mode", mode, "--cache", str(job / f"cache-{group}"),
                       "--out", str(job / group)]
            print(f"Running {name} render + compliance/audio verification…", file=sys.stderr, flush=True)
            summary, wall = call(command, root, job / f"{name}-execution.json")
            manifest = E.read_json(summary["manifest"])
            E.atomic_json(job / f"{name}-manifest.json", manifest)
            steps = manifest["steps"]
            encoded = sum(any("libx264" in cmd or "libx265" in cmd for cmd in s.get("commands", []))
                          for s in steps if s.get("tool") in ("cut", "crop", "fit") and s["cache"] == "miss")
            results[name] = dict(wall_seconds=wall, final=manifest["result"]["final"],
                                 manifest=str(job / f"{name}-manifest.json"),
                                 per_shot_video_encodes=encoded,
                                 cache_hits=summary["hits"], cache_misses=summary["misses"],
                                 media_skill_calls=len(manifest["commands"]))
            E.atomic_json(job / "results.json", results)
        # Refresh music/evidence using reusable tools; these are reported separately
        # because the previous session did not time a comparable analysis phase.
        plan = E.read_json((root / args.plan).resolve())
        music, music_wall = call([sys.executable, str(root / "tools/music.py"), plan["music"]["file"],
                                  "--root", str(root), "--out", str(job / "music")],
                                 root, job / "music-execution.json")
        pictures = {}
        final = results["optimized"]["final"]
        for mode, extra in (("survey", ["--tiles", "6x3", "--width", "1620"]),
                            ("cuts", ["--plan", args.plan, "--width", "360"])):
            report, wall = call([sys.executable, str(root / "tools/evidence.py"), mode, final,
                                 "--root", str(root), "--out", str(job / mode), *extra],
                                root, job / f"{mode}-execution.json")
            pictures[mode] = dict(report=report["report"], manifest=report["manifest"], wall_seconds=wall)
        results["analysis_and_picture_evidence"] = dict(music_wall_seconds=music_wall,
                                                        music=music, pictures=pictures)
        base_s, optimized_s = results["baseline"]["wall_seconds"], results["optimized"]["wall_seconds"]
        results["comparison"] = dict(cold_time_reduction_percent=(1 - optimized_s / base_s) * 100,
                                     warm_speedup=base_s / results["warm"]["wall_seconds"],
                                     saved_editorial_decisions=True, picture_review="pending")
        E.atomic_json(job / "results.json", results)
        lines = ["# Saved-edit rendering benchmark", "", "| Execution | Wall time | Per-shot cut/crop/fit encodes | Cache hits / misses |",
                 "|---|---:|---:|---:|"]
        for name in ("baseline", "optimized", "warm"):
            r = results[name]
            lines.append(f'| {name} | {r["wall_seconds"]:.2f} s | {r["per_shot_video_encodes"]} | '
                         f'{r["cache_hits"]}/{r["cache_misses"]} |')
        lines += ["", f'Cold render + QC time reduction: {results["comparison"]["cold_time_reduction_percent"]:.1f}%.',
                  "", "## Scope", "",
                  "- Baseline and optimized runs use isolated empty caches and execute sequentially.",
                  "- Counts are per-shot cut/crop/fit stages containing a video encoder; join, grade, export are additional shared stages.",
                  "- Encode counts include only cache misses; cached artifact command records are not newly executed commands.",
                  "- Both use the current no-ending-music-fade policy. Optimized also corrects planned speed inference.",
                  "- These are measured render-through-technical-QC wall times from saved creative decisions, not a remeasurement of the former ~40-minute editorial session.",
                  "- Music and picture-evidence wall times are reported separately in results.json; source analysis/editorial selection is not repeated.",
                  "- Output picture review remains pending until an agent views the PNGs and transition evidence.",
                  "- All media operations use unchanged installed skill scripts; full trim/crop/resize fusion remains unsupported.",
                  "- Source-cut detection is a separate follow-up; this benchmark's cuts mode inspects planned output transitions only.", ""]
        E.atomic_text(job / "results.md", "\n".join(lines))
        print(json.dumps(dict(status="completed", report=str(job / "results.md"), results=results), indent=2))
        return 0
    except (ValueError, KeyError, OSError, subprocess.TimeoutExpired) as exc:
        print(json.dumps(dict(status="failed", error=str(exc))), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
