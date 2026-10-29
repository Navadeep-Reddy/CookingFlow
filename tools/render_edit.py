#!/usr/bin/env python3
"""Render saved editorial decisions with installed skill scripts and validated reuse.

  python3 tools/render_edit.py workdir/plan.json --framing workdir/framing.json \
      --grade workdir/grade.json --audio-policy workdir/audio-policy.json

--validate-only compiles/checks decisions without rendering. --mode baseline
reproduces the old cut/crop/fit-per-shot structure for controlled benchmarks;
optimized defers normal-speed resizing to join, preserves planned speed, and uses max source 9:16 resolution without upscaling.
This is NOT a fused trim/crop/resize encoder: the installed skill exposes no such
operation. No raw FFmpeg, skill modifications, implicit beat snapping, or source
cut detection. Default report: workdir/render-edit/manifest.json; output paths
are content-addressed beneath workdir/render-cache. A repeat validates hashes and
saved probes before reuse. Linux/macOS locks. Optional --audio-evidence requires
NumPy/SciPy (tools/requirements-music.txt); signal evidence is not listening.

Audio policy: {"shots": {"s01": {"gain_db": -5, "mute": false,
"fade_in": 0.02, "fade_out": 0.025}, ...}, "music_gain_db": -3,
"mix_fade_in": 0.025}. Every shot must have an explicit policy. Ending music/mix
fades are refused by channel policy. Sources must be prepared SDR/CFR; technical
conversions/corrections must already be resolved in grade.json. Per-shot LUT
overrides support lut_path/strength and inherit the default. No editorial choice
is made by this runner. A passing mechanical check leaves editorial review pending.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time

try:
    from . import evidence
except ImportError:
    import evidence

E = evidence
PRODUCER = "reel-render"


def frame_index(value, rate=30):
    exact = E.number(value, "frame timestamp") * rate
    n = round(exact)
    if n < 0 or abs(exact - n) > 1e-5:
        raise ValueError(f"Timestamp is not on the {rate}-fps frame grid: {value}")
    return n


def validate_probe(meta, expected):
    if not isinstance(meta, dict) or not meta.get("video"):
        raise ValueError("No verified video probe")
    v = meta["video"]
    for k in ("width", "height", "nb_frames"):
        if k in expected and v.get(k) != expected[k]:
            raise ValueError(f"Output {k}: expected {expected[k]}, got {v.get(k)}")
    if "fps" in expected and abs(float(v.get("fps") or 0) - expected["fps"]) > 1e-5:
        raise ValueError("Output frame rate does not match plan")
    if expected.get("delivery"):
        a = meta.get("audio") or {}
        if (float(meta["duration"]) >= 30 or v.get("codec") != "h264" or
                a.get("codec") != "aac" or a.get("channels") != 2):
            raise ValueError("Output does not meet channel delivery contract")


def compile_plan(plan, framing, policy, probes, footage=None):
    shots = plan["shots"]
    if not shots:
        raise ValueError("Plan has no shots")
    ids = [s["id"] for s in shots]
    if any(not isinstance(i, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", i) for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("Shot IDs must be unique simple identifiers")
    framed = {s["id"]: s for s in framing["shots"]}
    if len(framed) != len(framing["shots"]) or set(framed) != set(ids):
        raise ValueError("Framing shot IDs must match the plan exactly")
    if set(policy.get("shots", {})) != set(ids):
        raise ValueError("Audio policy must explicitly cover every shot")
    if policy.get("music_fade_out", 0) or policy.get("mix_fade_out", 0):
        raise ValueError("Ending music/mix fades conflict with channel style")
    E.number(policy["music_gain_db"], "music gain")
    if not 0 <= E.number(policy.get("mix_fade_in", 0), "mix fade") <= .1:
        raise ValueError("Mix entry fade must be 0..0.1 s")
    moments = {}
    if footage:
        for stage in footage["stages"]:
            for moment in stage["moments"]:
                if moment["id"] in moments:
                    raise ValueError("Footage moment IDs are not unique")
                moments[moment["id"]] = (stage["name"], moment)
    result, cursor, used_stages = [], 0, set()
    beats = [E.number(t, "beat") for t in plan.get("beats_relative", [])]
    if beats != sorted(set(beats)):
        raise ValueError("Relative beats must be chronological and unique")
    for shot in shots:
        meta = probes[shot["clip"]]
        w, h = E.dimensions(meta)
        rate = E.frame_rate(meta)
        if meta["video"].get("bt2020_or_hdr"):
            raise ValueError("Prepare HDR/wide-gamut sources to SDR before this runner")
        start, end = (E.number(shot[k], k) for k in ("src_in", "src_out"))
        source_first, source_stop = frame_index(start, rate), frame_index(end, rate)
        if end <= start or end > float(meta["video"].get("duration") or meta["duration"]) + 1e-6:
            raise ValueError(f"Invalid source range for {shot['id']}")
        speed = E.number(shot["speed"], "speed")
        if not 1 <= speed <= 2:
            raise ValueError("Planned speed must be in [1, 2]")
        a, b = frame_index(shot["out_start"]), frame_index(shot["out_end"])
        if a != cursor or b <= a or abs((end - start) / speed - (b - a) / 30) > 1e-6:
            raise ValueError(f"Nonconsecutive or inconsistent timing for {shot['id']}")
        audio = policy["shots"][shot["id"]]
        if not isinstance(audio.get("mute"), bool) or not isinstance(shot.get("keep_original_audio"), bool):
            raise ValueError("Audio retention and mute policy must be explicit booleans")
        E.number(audio["gain_db"], "shot gain")
        for k in ("fade_in", "fade_out"):
            if not 0 <= E.number(audio[k], k) <= (b - a) / 60:
                raise ValueError("Source-edge fades must not cover more than half the shot")
        if not audio["mute"] and shot["keep_original_audio"] and not meta.get("audio"):
            raise ValueError("Retained cooking audio requested from a silent source")
        if footage:
            stage, moment = moments[shot["moment_id"]]
            if (moment["clip"] != shot["clip"] or start < moment["start"] - 1e-6 or
                    end > moment["end"] + 1e-6):
                raise ValueError("Shot is outside its selected footage moment")
            used_stages.add(stage)
        row = dict(shot, crop=E.crop_box(framed[shot["id"]], w, h),
                   output_frames=b - a, source_frames=source_stop - source_first,
                   source_fps=float(rate), audio=audio)
        if a and beats:
            beat = min(beats, key=lambda t: abs(t - a / 30))
            row["nearest_beat"] = dict(time=beat, difference_ms=(a / 30 - beat) * 1000,
                                       snapped=False)
        result.append(row)
        cursor = b
    if cursor >= 900 or abs(E.number(plan["duration"], "duration") - cursor / 30) > 1e-6:
        raise ValueError("Plan must be frame-exact and strictly under 30 seconds")
    if any(t < 0 or t > cursor / 30 for t in beats):
        raise ValueError("Beat timestamps outside the output timeline")
    if footage and used_stages != {s["name"] for s in footage["stages"]}:
        raise ValueError("The plan does not cover every cooking stage")
    return dict(shots=result, music=plan["music"], duration=cursor / 30,
                total_frames=cursor, source_dependencies=list(probes), frame={k: min(s["crop"][k] for s in result) for k in ("width", "height")})


def lut_flag(strength, commands):
    """Inspect the installed script's dry-run graph; never blindly invert versions."""
    strength = E.number(strength, "intended LUT strength")
    if not 0 <= strength <= 1:
        raise ValueError("LUT contribution must be in [0, 1]")
    if strength in (0, 1):
        return strength
    text = "\n".join(commands)
    if re.search(r"\[o\]\[g2\]blend=all_mode=normal:all_opacity=", text):
        return 1 - strength
    if re.search(r"\[g2\]\[o\]blend=all_mode=normal:all_opacity=", text):
        return strength
    raise ValueError("Unrecognized LUT blend semantics; inspect this skill version before grading")


class Runner(E.Evidence):
    def __init__(self, root=E.ROOT, cache="workdir/render-cache"):
        super().__init__(root, cache)
        self.version = E.digest([self.version, E.file_hash(__file__)])
        self.steps = []

    def step(self, label, tool, args, inputs, suffix=".mp4", expected=None, target=None):
        stamps = [E.identity(p) for p in inputs]
        key = E.digest([self.version, tool, list(map(str, args)), stamps, expected, suffix,
                        str(target) if target else None])
        target = Path(target) if target else self.cache / f"{key}{suffix}"
        record = self.cache / f"{key}.result.json"
        started = time.monotonic()
        with E.lock(self.cache / f"{key}.lock"):
            hit = False
            try:
                saved = E.read_json(record)
                if saved["key"] != key or E.file_hash(target) != saved["sha256"]:
                    raise ValueError("Artifact changed")
                if expected:
                    validate_probe(saved["result"]["probe"], expected)
                result = saved["result"]
                hit = True
            except (OSError, ValueError, KeyError, TypeError):
                self.help_once(tool)
                argv = [*args, "-o", target, "--json"]
                if target.exists():
                    argv.append("--overwrite")  # this content-addressed cache artifact is owned
                dry = self.tool(tool, [*argv, "--dry-run"])
                E.atomic_json(self.cache / f"{key}.dry.json", dry)
                result = self.tool(tool, argv)
                if suffix in (".mp4", ".wav") and not result.get("verified"):
                    raise ValueError(f"{label} did not produce a verified media artifact")
                if expected:
                    validate_probe(result["probe"], expected)
                if [E.identity(p) for p in inputs] != stamps:
                    raise ValueError("Stage input changed during execution")
                saved = dict(key=key, sha256=E.file_hash(target), result=result)
                E.atomic_json(record, saved)
            self.steps.append(dict(label=label, tool=tool, key=key, output=str(target),
                                   cache="hit" if hit else "miss", seconds=time.monotonic() - started,
                                   commands=result.get("commands", []), expected=expected,
                                   sha256=saved["sha256"]))
        return target, result

    def project(self, value):
        path = self.cache / f"{E.digest(value)}.project.json"
        if not path.exists():
            E.atomic_json(path, value)
        elif E.read_json(path) != value:
            raise ValueError("Project cache content changed")
        return path

    def render_project(self, label, project, inputs, expected):
        # Content-address the skill's own project/output/work; dependencies are
        # explicit because a project JSON alone does not fingerprint its media.
        key = E.digest([project, [E.identity(p) for p in inputs], self.version])
        project = dict(project, output=str(self.cache / f"{key}.mp4"))
        path = self.project(project)
        return self.step(label, "render", [path, "--work", self.cache / f"{key}-work",
                         "--cache", self.cache / f"{key}-skill-cache"], [path, *inputs], expected=expected,
                         target=Path(project["output"]))

    def audio_probe(self, source):
        stamp = E.identity(source)
        path = self.cache / f"{E.digest([self.version, stamp, 'audio-probe'])}.json"
        try:
            saved = E.read_json(path)
            if E.digest(saved["probe"]) != saved["sha256"] or not saved["probe"].get("audio"):
                raise ValueError("Invalid audio probe cache")
            return saved["probe"]
        except (OSError, ValueError, KeyError, TypeError):
            self.help_once("probe")
            probe = self.tool("probe", [source, "--json"])
            if not probe.get("audio") or E.identity(source) != stamp:
                raise ValueError("Invalid/changed audio source")
            E.atomic_json(path, dict(probe=probe, sha256=E.digest(probe)))
            return probe

    def check(self, video):
        key = E.digest([self.version, E.identity(video), "reels-under30-content"])
        path = self.cache / f"{key}.check.json"
        with E.lock(self.cache / f"{key}.lock"):
            try:
                saved = E.read_json(path)
                if saved["input_sha256"] != E.file_hash(video) or not saved["result"]["ok"]:
                    raise ValueError("Invalid cached check")
                result, hit = saved["result"], True
            except (OSError, ValueError, KeyError, TypeError):
                self.help_once("check")
                result = self.tool("check", [video, "--platform", "reels", "--max-duration",
                                             "29.999", "--content", "--json"])
                if not result.get("ok"):
                    raise ValueError("Final compliance/content check failed")
                E.atomic_json(path, dict(result=result, input_sha256=E.file_hash(video)))
                hit = False
        self.steps.append(dict(label="final-qc", cache="hit" if hit else "miss", output=str(path)))
        return result


def run_edit(engine, compiled, grade, policy, mode):
    parts = []
    override_map = grade.get("per_shot_overrides", {})
    if set(override_map) - {s["id"] for s in compiled["shots"]}:
        raise ValueError("Grade overrides reference unknown shots")
    if grade.get("status") != "complete":
        raise ValueError("Grade decisions must be complete before rendering")
    for prep in grade.get("input_preparation", {}).values():
        if prep.get("corrections") or prep.get("operations"):
            raise ValueError("Apply technical input conversions/corrections before this runner")
    compat = {}

    def apply_grade(label, source, settings, expected):
        if set(settings) - {"lut_path", "strength"}:
            raise ValueError("Only lut_path/strength per-shot grade overrides are supported")
        lut = engine.source(settings["lut_path"])
        strength = E.number(settings["strength"], "LUT strength")
        if not 0 <= strength <= 1:
            raise ValueError("LUT strength must be in [0,1]")
        if not strength:
            return source
        if str(lut) not in compat:
            path = engine.cache / f"{E.digest([engine.version, E.identity(lut), 'lut-compat'])}.json"
            try:
                dry = E.read_json(path)
                lut_flag(.5, dry["commands"])
            except (OSError, ValueError, KeyError, TypeError):
                engine.help_once("color")
                dry = engine.tool("color", [source, "--lut", lut, "--lut-strength", .5,
                                            "-o", engine.cache / "compatibility-unused.mp4", "--dry-run", "--json"])
                lut_flag(.5, dry["commands"])
                E.atomic_json(path, dry)
            compat[str(lut)] = dict(partial_flag_for_half=lut_flag(.5, dry["commands"]),
                                   commands=dry["commands"], tool_fingerprint=engine.version)
        flag = lut_flag(strength, compat[str(lut)]["commands"])
        return engine.step(label, "color", [source, "--lut", lut, "--lut-strength", flag,
                           "--quality", 18, "--preset", "superfast"], [source, lut], expected=expected)[0]

    frame, global_grade = compiled["frame"], {k: grade[k] for k in ("lut_path", "strength")}
    for shot in compiled["shots"]:
        sid = shot["id"]
        source = engine.source(shot["clip"])
        source_expected = dict(nb_frames=shot["source_frames"], fps=shot["source_fps"])
        cut, _ = engine.step(f"{sid}-cut", "cut", [source, "--start", shot["src_in"],
                              "--end", shot["src_out"], "--accurate", "--quality", 18,
                              "--preset", "ultrafast"], [source], expected=source_expected)
        c = shot["crop"]
        crop, doc = engine.step(f"{sid}-crop", "crop", [cut, "--x", c["x"], "--y", c["y"],
                                "--width", c["width"], "--height", c["height"], "--quality", 18,
                                "--preset", "ultrafast"], [cut], expected=source_expected | {
                                    "width": c["width"], "height": c["height"]})
        part = crop
        expected = dict(nb_frames=shot["output_frames"], fps=30)
        if mode == "baseline" or abs(shot["speed"] - 1) > 1e-8 or abs(shot["source_fps"] - 30) > 1e-8:
            # fit.py computes factor from CONTAINER duration. Compensate its target
            # so setpts/atempo use the planned speed, not an AAC-tail-derived speed.
            duration = ((shot["out_end"] - shot["out_start"]) if mode == "baseline"
                        else float(doc["probe"]["duration"]) / shot["speed"])
            part, fit = engine.step(f"{sid}-fit", "fit", [crop, "--width", frame["width"], "--height", frame["height"],
                                     "--fps", 30, "--duration", duration, "--quality", 18,
                                     "--preset", "superfast"], [crop], expected=expected | {
                                         **frame})
            if mode != "baseline" and shot["keep_original_audio"] and not shot["audio"]["mute"]:
                match = re.search(r"atempo=([\d.]+)", "\n".join(fit["commands"]))
                if match and abs(float(match[1]) - shot["speed"]) > 1e-6:
                    raise ValueError("Executed audio speed differs from planned picture speed")
        audio = shot["audio"]
        gain = audio["gain_db"] if shot["keep_original_audio"] and not audio["mute"] else -120
        part, _ = engine.step(f"{sid}-audio", "audio", [part, "--gain", gain, "--fade-in", audio["fade_in"],
                               "--fade-out", audio["fade_out"]], [part], expected=expected)
        if override_map:
            part = apply_grade(f"{sid}-grade", part, global_grade | override_map.get(sid, {}), expected)
        parts.append(part)
    total = dict(**frame, fps=30, nb_frames=compiled["total_frames"])
    assembled, _ = engine.render_project("assembly", dict(clips=[dict(src=str(p)) for p in parts],
                                          frame=dict(**frame, fps=30),
                                          transition=dict(type="none", duration=0)), parts, total)
    graded = assembled if override_map else apply_grade("grade", assembled, global_grade, total)
    song = engine.source(compiled["music"]["file"])
    bed, _ = engine.step("music-section", "cut", [song, "--start", compiled["music"]["start"],
                         "--duration", compiled["duration"], "--accurate"], [song], suffix=".wav")
    mixed, _ = engine.render_project("mix", dict(clips=[dict(src=str(graded))],
        audio=dict(music=str(bed), music_volume=policy["music_gain_db"],
                   music_fade_out=0, fade_in=policy.get("mix_fade_in", 0), fade_out=0, stereo=True)), [graded, bed], total)
    final, final_doc = engine.step("delivery", "export", [mixed, "--preset", "reels", "--no-scale", "--normalize"], [mixed], expected=total | {"delivery": True})
    check = engine.check(final)
    return dict(final=str(final), probe=final_doc["probe"], cooking_stem=str(assembled),
                music_stem=str(bed), check=check, lut_compatibility=compat)


def audio_evidence(engine, result):
    """Both-channel, rate-aware two-stem regression with a bounded offset search."""
    import numpy as np
    from scipy.io import wavfile
    from scipy.signal import resample_poly
    arrays = []
    for label, path in (("final", result["final"]), ("cooking", result["cooking_stem"]),
                        ("music", result["music_stem"])):
        if Path(path).suffix != ".wav":
            path, _ = engine.step(f"decode-{label}", "audio", [path], [path], suffix=".wav")
        sr, raw = wavfile.read(path)
        x = raw.astype(float) / 32768
        if x.ndim != 2 or x.shape[1] != 2:
            raise ValueError("Two-stem verification currently requires stereo stems")
        rate = Fraction(48000, int(sr))
        arrays.append(resample_poly(x, rate.numerator, rate.denominator, axis=0))
    y, c, m = arrays
    length = min(map(len, arrays))
    a, b = 48000, length - 12000
    if b <= a:
        raise ValueError("Insufficient overlap for audio evidence")
    best = None
    for shift in range(-960, 961, 48):
        target = y[a:b:8].reshape(-1)
        matrix = np.column_stack([c[a + shift:b + shift:8].reshape(-1),
                                  m[a + shift:b + shift:8].reshape(-1)])
        if np.linalg.cond(matrix) > 1e6:
            raise ValueError("Stems are silent or too correlated for presence verification")
        coefficients, _, _, _ = np.linalg.lstsq(matrix, target, rcond=None)
        explained = 1 - float(np.sum((target - matrix @ coefficients) ** 2) / np.sum(target ** 2))
        if best is None or explained > best["explained_energy_fraction"]:
            best = dict(explained_energy_fraction=explained, cooking_coefficient=float(coefficients[0]),
                        music_coefficient=float(coefficients[1]), shift_ms=shift / 48)
    best.update(method="Both-channel two-stem regression; resampled to 48 kHz; 1 s to end-0.25 s; "
                       "shared offset search +/-20 ms in 1-ms steps", listening="not performed")
    best["passed"] = (best["explained_energy_fraction"] > .9 and
                      best["cooking_coefficient"] > .02 and best["music_coefficient"] > .02)
    return best


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plan")
    parser.add_argument("--framing", required=True)
    parser.add_argument("--grade", required=True)
    parser.add_argument("--audio-policy", required=True)
    parser.add_argument("--footage", help="optional selected-moment containment/stage checks")
    parser.add_argument("--root", type=Path, default=E.ROOT)
    parser.add_argument("--cache", default="workdir/render-cache")
    parser.add_argument("--out", default="workdir/render-edit")
    parser.add_argument("--mode", choices=("optimized", "baseline"), default="optimized")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--audio-evidence", action="store_true")
    args = parser.parse_args(argv)
    started = time.monotonic()
    out = None
    try:
        engine = Runner(args.root, args.cache)
        destination = engine.generated(args.out)
        destination.mkdir(parents=True, exist_ok=True)
        with E.lock(destination / ".lock"):
            owner = destination / ".owner"
            if (owner.exists() and owner.read_text() != PRODUCER or not owner.exists() and
                    any(p.name != ".lock" for p in destination.iterdir())):
                raise ValueError("Refusing to replace a non-owned report directory")
            source_paths = [engine.source(getattr(args, k)) for k in ("plan", "framing", "grade", "audio_policy")]
            if args.footage:
                source_paths.append(engine.source(args.footage))
            stamps = [E.identity(p) for p in source_paths]
            if any(p.is_relative_to(destination) or p.is_relative_to(engine.cache) for p in source_paths):
                raise ValueError("Decisions must live outside generated cache/report directories")
            E.atomic_text(owner, PRODUCER)
            out = destination
            E.atomic_json(out / "manifest.json", dict(producer=PRODUCER, status="running"))
            plan, framing, grade, policy = [E.read_json(p) for p in source_paths[:4]]
            probes = {}
            for source in dict.fromkeys(s["clip"] for s in plan["shots"]):
                _, _, probes[source] = engine.probe(source)
            compiled = compile_plan(plan, framing, policy, probes,
                                    E.read_json(source_paths[4]) if args.footage else None)
            song = engine.source(compiled["music"]["file"])
            media_paths = [engine.source(p) for p in probes] + [song]
            media_stamps = [E.identity(p) for p in media_paths]
            music_probe = engine.audio_probe(song)
            if not music_probe.get("audio") or not 0 <= E.number(compiled["music"]["start"], "music start"):
                raise ValueError("Invalid music source/start")
            if compiled["music"]["start"] + compiled["duration"] > music_probe["duration"]:
                raise ValueError("Selected music section exceeds song duration")
            E.atomic_json(out / "compiled.json", compiled)
            result = {} if args.validate_only else run_edit(engine, compiled, grade, policy, args.mode)
            if args.audio_evidence and not args.validate_only:
                result["audio_evidence"] = audio_evidence(engine, result)
                if not result["audio_evidence"]["passed"]:
                    raise ValueError("Two-stem audio evidence failed")
            if [E.identity(p) for p in source_paths] != stamps:
                raise ValueError("Editorial decisions changed during execution")
            if [E.identity(p) for p in media_paths] != media_stamps:
                raise ValueError("Source media changed during execution")
            manifest = dict(producer=PRODUCER, status="validated" if args.validate_only else "completed",
                            mode=args.mode, tool_fingerprint=engine.version, inputs=stamps,
                            source_media=media_stamps,
                            result=result, steps=engine.steps, commands=engine.commands,
                            elapsed_seconds=time.monotonic() - started, editorial_review="pending")
            E.atomic_json(out / "manifest.json", manifest)
            with (out / "runs.jsonl").open("a") as stream:
                stream.write(json.dumps(manifest) + "\n")
            print(json.dumps(dict(status=manifest["status"], manifest=str(out / "manifest.json"),
                                  final=result.get("final"), elapsed_seconds=manifest["elapsed_seconds"],
                                  hits=sum(s["cache"] == "hit" for s in engine.steps),
                                  misses=sum(s["cache"] == "miss" for s in engine.steps)), indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, subprocess.TimeoutExpired) as exc:
        if out:
            E.atomic_json(out / "manifest.json", dict(producer=PRODUCER, status="failed", error=str(exc),
                                                     steps=engine.steps, commands=engine.commands))
        print(json.dumps(dict(status="failed", error=str(exc))), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
