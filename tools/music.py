#!/usr/bin/env python3
"""Cached music measurements and section/beat analysis (NumPy and SciPy required).

  python3 tools/music.py "Sounds/song.mp3"
  python3 tools/music.py "Sounds/song.mp3" --high-point 25.3
  python3 tools/music.py "Sounds/song.mp3" --publish workdir/music.json

Default output: workdir/music-analysis/{music.json,analysis.json,manifest.json}.
music.json contains only start_song_t and detected, grid-supported beats_song_t.
It is written only after numerical alignment checks pass. Energy rises are
editorial candidates, not a judgement of musical meaning; inspect analysis.json.
--high-point overrides automatic selection without decoding/measuring again.
--publish explicitly copies a validated handoff; existing destinations require
--overwrite. Reports/cache stay under workdir; input files are never replaced.

All probing/decoding uses installed skill scripts (no raw FFmpeg). Full-channel
PCM is decoded once; pooled power and spectral magnitudes avoid anti-phase stereo
cancellation. Cached artifacts use SHA-256; input identity uses resolved path,
size, mtime/ctime. Tool/dependency versions invalidate cached measurements.
Timestamps follow decoded playable audio, not container padding. Spectral peaks
are ~10-ms-hop measurements, not sample-exact attacks or verified downbeats.
Importing this module performs no analysis or media operations. Linux/macOS locks.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import numpy as np
import scipy
from scipy import signal
from scipy.io import wavfile

try:
    from .evidence import (Evidence, ROOT, atomic_json, atomic_text, digest,
                           file_hash, identity, lock, number, read_json)
except ImportError:
    from evidence import (Evidence, ROOT, atomic_json, atomic_text, digest,
                          file_hash, identity, lock, number, read_json)


PRODUCER = "reel-music"
FEATURE_SCHEMA = 1


def extract_features(sr, raw):
    """Numerical measurements of skill-decoded s16 PCM; no media decoding here."""
    raw = np.asarray(raw)
    if raw.ndim == 1:
        raw = raw[:, None]
    if (raw.ndim != 2 or raw.dtype != np.int16 or not len(raw)
            or raw.shape[1] < 1 or sr < 8000):
        raise ValueError("Expected nonempty s16 PCM, >=8000 Hz, with audio channels")
    n, channels = raw.shape
    duration = n / sr
    # 10-ms cumulative pooled power; interpolate only within these small bins.
    step = max(1, round(sr / 100))
    edges = np.r_[np.arange(0, n, step), n]
    energy = np.zeros(len(edges) - 1)
    magnitude = None
    ratio = Fraction(11025, int(sr))
    for channel in range(channels):
        x = raw[:, channel].astype(np.float64) / 32768
        energy += np.add.reduceat(x * x, edges[:-1]) / (sr * channels)
        y = signal.resample_poly(x, ratio.numerator, ratio.denominator)
        if len(y) < 1024:
            raise ValueError("Audio is too short for onset measurements")
        _, times, z = signal.stft(y, fs=11025, nperseg=1024, noverlap=914,
                                  boundary=None)
        channel_mag = np.abs(z) / channels
        magnitude = channel_mag if magnitude is None else magnitude + channel_mag
    logmag = np.log1p(100 * magnitude)
    flux = np.r_[0., np.maximum(np.diff(logmag, axis=1), 0).sum(axis=0)]
    flux = np.maximum(flux - signal.medfilt(flux, 21), 0)
    times, flux = times[times < duration], flux[times < duration]
    threshold = max(float(np.percentile(flux, 70)) * .5, float(flux.max()) * .01, 1e-10)
    peaks, _ = signal.find_peaks(flux, distance=8, prominence=threshold)
    return dict(energy_t=edges / sr, energy_sum=np.r_[0., np.cumsum(energy)],
                times=times, flux=flux, peaks=peaks), dict(
                    duration_s=duration, sample_rate=int(sr), channels=channels,
                    energy_resolution_s=step / sr, onset_hop_s=110 / 11025,
                    onset_window_s=1024 / 11025)


def measure_wav(path):
    sr, raw = wavfile.read(path, mmap=True)
    return extract_features(sr, raw)


def mean_power(features, start, end):
    if start < 0 or end <= start or end > features["energy_t"][-1] + 1e-8:
        raise ValueError("Power interval outside decoded audio")
    a, b = np.interp([start, end], features["energy_t"], features["energy_sum"])
    return max(0., float((b - a) / (end - start)))


def db(value):
    return 10 * math.log10(max(value, 1e-15))


def rise_at(features, t):
    before, after = mean_power(features, t - 4, t), mean_power(features, t, t + 4)
    return dict(high_point_song_t=float(t), rise_db=db(after) - db(before),
                before_rms_dbfs=db(before), after_rms_dbfs=db(after))


def candidates(features, duration, section, build, count):
    """Rank actual onset peaks, refined beyond the coarse energy-rise timeline."""
    times = features["times"][features["peaks"]]
    times = times[(times >= max(4, build)) & (times <= duration - max(4, section))]
    ranked = sorted((rise_at(features, t) for t in times),
                    key=lambda r: r["rise_db"], reverse=True)
    selected = []
    for row in ranked:
        if all(abs(row["high_point_song_t"] - r["high_point_song_t"]) >= 5 for r in selected):
            selected.append(row)
        if len(selected) >= count:
            break
    return selected


def nearest_onsets(grid, onset_t, tolerance):
    if not len(onset_t) or not len(grid):
        return np.array([], dtype=int), np.array([], dtype=int)
    right = np.searchsorted(onset_t, grid).clip(0, len(onset_t) - 1)
    left = (right - 1).clip(0)
    nearest = np.where(abs(onset_t[left] - grid) <= abs(onset_t[right] - grid), left, right)
    keep = np.flatnonzero(abs(onset_t[nearest] - grid) <= tolerance)
    # One detected onset must never be counted as two supported beats.
    _, unique = np.unique(nearest[keep], return_index=True)
    keep = keep[np.sort(unique)]
    return keep, nearest[keep]


def beat_grid(phase, period, start, end):
    indices = np.arange(math.ceil((start - phase) / period),
                        math.ceil((end - phase) / period))
    return indices, phase + indices * period


def fit_beats(features, start, section, min_bpm=60., max_bpm=200.):
    end = start + section
    t, f = features["times"], features["flux"]
    onset_t = t[features["peaks"]]
    onset_t = onset_t[(onset_t >= start) & (onset_t < end)]
    empty = dict(valid=False, reasons=["Insufficient detected onsets"], beats_song_t=[])
    if len(onset_t) < 6:
        return empty
    dt = float(np.median(np.diff(t)))
    part = f[(t >= start) & (t < end)]
    centered = part - part.mean()
    ac = signal.correlate(centered, centered, mode="full", method="fft")[len(part) - 1:]
    if ac[0] <= 1e-12:
        return empty
    lo, hi = 60 / max_bpm, 60 / min_bpm
    local, _ = signal.find_peaks(ac)
    local = local[(local * dt >= lo - dt) & (local * dt <= hi + dt)]
    best_lags = sorted(local, key=lambda i: ac[i], reverse=True)[:8]
    if not best_lags:
        return dict(empty, reasons=["No periodic onset evidence in requested tempo range"])
    smooth = signal.convolve(f, signal.windows.gaussian(9, 1.4), mode="same")
    choices = []
    periods = np.unique(np.round(np.concatenate([
        np.arange(max(lo, lag * dt - dt), min(hi, lag * dt + dt) + .00025, .0005)
        for lag in best_lags]), 6))
    for period in periods:
        if period < lo or period > hi:
            continue
        phases = np.arange(start, start + period, dt / 2)
        grids = phases[:, None] + period * np.arange(math.ceil(section / period) + 1)
        mask = grids < end
        values = np.interp(grids, t, smooth, left=0, right=0)
        scores = (values * mask).sum(axis=1) / mask.sum(axis=1)
        j = int(np.argmax(scores))
        choices.append(dict(period_s=float(period), phase_song_t=float(phases[j]),
                            score=float(scores[j])))
    # Exact metronomic ties can differ only by floating-point roundoff. Prefer
    # the denser supported pulse in a tie; retain half-time alternatives below.
    choices.sort(key=lambda c: (round(c["score"], 9), -c["period_s"]), reverse=True)
    if not choices:
        return dict(empty, reasons=["No period in requested tempo range"])
    # Keep auditable alternatives (including half/double-time ambiguity).
    alternatives = []
    for row in choices:
        if all(abs(row["period_s"] - r["period_s"]) > .015 for r in alternatives):
            alternatives.append(row)
        if len(alternatives) == 5:
            break
    best = choices[0]
    phase, period = best["phase_song_t"], best["period_s"]
    tolerance = min(.060, lo / 4)
    for _ in range(2):
        indices, grid = beat_grid(phase, period, start, end)
        kept, found = nearest_onsets(grid, onset_t, tolerance)
        if len(kept) < 6:
            return dict(empty, alternatives=alternatives)
        period, phase = np.polyfit(indices[kept], onset_t[found], 1)
    indices, grid = beat_grid(phase, period, start, end)
    kept, found = nearest_onsets(grid, onset_t, tolerance)
    if len(kept) < 6:
        return dict(empty, alternatives=alternatives)
    residual = onset_t[found] - grid[kept]
    p95 = float(np.percentile(abs(residual), 95) * 1000)
    support = len(kept) / len(grid)
    blocks = []
    for a, b in zip(np.linspace(start, end, 4)[:-1], np.linspace(start, end, 4)[1:]):
        predicted = int(((grid >= a) & (grid < b)).sum())
        supported = int(((grid[kept] >= a) & (grid[kept] < b)).sum())
        blocks.append(dict(start_song_t=float(a), end_song_t=float(b),
                           predicted=predicted, supported=supported,
                           support_fraction=supported / predicted if predicted else 0.))
    reasons = []
    if support < .9:
        reasons.append("Fewer than 90% of predicted beats have detected onset support")
    if p95 > 40:
        reasons.append("95th-percentile beat alignment error exceeds 40 ms")
    if not lo - 1e-6 <= period <= hi + 1e-6:
        reasons.append("Refined tempo outside requested range")
    if any(b["supported"] < 3 or b["support_fraction"] < .75 for b in blocks):
        reasons.append("Insufficient beat support across beginning/middle/end")
    rows = [dict(beat_index=int(indices[k]), grid_song_t=float(grid[k]),
                 detected_song_t=float(onset_t[p]), residual_ms=float(r * 1000))
            for k, p, r in zip(kept, found, residual)]
    return dict(valid=not reasons, reasons=reasons, period_s=float(period),
                bpm=float(60 / period), phase_song_t=float(phase),
                predicted_beats=len(grid), supported_beats=len(kept), support_fraction=support,
                median_abs_error_ms=float(np.median(abs(residual)) * 1000),
                p95_abs_error_ms=p95, max_abs_error_ms=float(max(abs(residual)) * 1000),
                blocks=blocks, alignment=rows, alternatives=alternatives,
                beats_song_t=[round(float(v), 6) for v in onset_t[found]])


def analyze(features, meta, section=30., build=1., high_point=None,
            count=8, min_bpm=60., max_bpm=200.):
    duration = meta["duration_s"]
    if section < 9 or not 0 <= build <= 3 or not 30 <= min_bpm < max_bpm <= 300:
        raise ValueError("Need section >=9 s, build 0..3 s, and 30 <= min BPM < max BPM <=300")
    if not 1 <= count <= 20:
        raise ValueError("Candidate count must be 1..20")
    if duration < section + build:
        raise ValueError("Not enough decoded music for the section and build")
    ranked = candidates(features, duration, section, build, count)
    if high_point is not None:
        if high_point < build or high_point + section > duration:
            raise ValueError("High point needs build before it and a full section remaining")
        row = dict(high_point_song_t=high_point, selection="explicit high point")
        if 4 <= high_point <= duration - 4:
            row.update(rise_at(features, high_point))
        trials = [row]
    else:
        trials = ranked
    attempts, selected = [], None
    for row in trials:
        start = row["high_point_song_t"] - build
        fit = fit_beats(features, start, section, min_bpm, max_bpm)
        attempts.append(dict(candidate=row, beat_analysis=fit))
        if fit["valid"]:
            selected = dict(start_song_t=round(start, 6), high_point_song_t=row["high_point_song_t"],
                            section_end_song_t=start + section, build_s=build,
                            candidate=row, beat_analysis=fit)
            break
    seconds = np.arange(0, duration, 1.)
    rms = [dict(start_s=float(a), end_s=float(min(a + 1, duration)),
                rms_dbfs=db(mean_power(features, a, min(a + 1, duration)))) for a in seconds]
    coarse = [dict(time_s=float(t), rise_db=rise_at(features, t)["rise_db"])
              for t in np.arange(4., duration - 4 + 1e-8, 1.)]
    # Fine 100-ms energy measurements around all ranked candidates.
    fine_candidates = ranked + ([trials[0]] if high_point is not None and
                                 all(abs(r["high_point_song_t"] - high_point) > .001
                                     for r in ranked) else [])
    fine = [dict(candidate_song_t=row["high_point_song_t"], start_s=float(t),
                 rms_dbfs=db(mean_power(features, t, min(t + .1, duration))))
            for row in fine_candidates
            for t in np.arange(max(0, row["high_point_song_t"] - 1),
                               min(duration - .1, row["high_point_song_t"] + 1), .1)]
    accents = []
    if selected:
        peaks = features["peaks"]
        t, f = features["times"], features["flux"]
        peaks = peaks[(t[peaks] >= selected["start_song_t"]) &
                      (t[peaks] < selected["section_end_song_t"])]
        if len(peaks):
            threshold = np.percentile(f[peaks], 75)
            accents = [round(float(t[p]), 6) for p in peaks if f[p] >= threshold]
    return dict(status="validated" if selected else "needs_review", selected=selected,
                candidates=ranked, attempts=attempts, prominent_accents_song_t=accents,
                rms_1s=rms, energy_rises_4s=coarse, fine_energy_100ms=fine,
                selection_method="Highest pooled 4-second energy rise at a detected onset, with "
                                 "a full section after the high point, passing beat validation; "
                                 "an editorial candidate, not a musical judgement.",
                timing_precision="~9.98-ms onset hop, 92.88-ms STFT window; spectral-change "
                                 "maxima, not sample-exact attack edges or inferred downbeats.",
                accent_method="Upper quartile of detected onset strengths in selected section")


class Music(Evidence):
    def __init__(self, root=ROOT, cache="workdir/music-cache"):
        super().__init__(root, cache)
        self.version = digest([self.version, file_hash(__file__), FEATURE_SCHEMA,
                               np.__version__, scipy.__version__])
        self.stats = {}

    def valid_artifact(self, path, key):
        try:
            record = read_json(path.with_suffix(path.suffix + ".sha.json"))
            return record["key"] == key and file_hash(path) == record["sha256"]
        except (OSError, ValueError, KeyError, TypeError):
            return False

    def seal(self, path, key):
        atomic_json(path.with_suffix(path.suffix + ".sha.json"),
                    dict(key=key, sha256=file_hash(path)))

    def measurements(self, input_path):
        source = self.source(input_path)
        stamp = identity(source)
        key = digest([self.version, stamp])
        probe = self.cache / f"{key}.probe.json"
        pcm = self.cache / f"{key}.wav"
        packed = self.cache / f"{key}.npz"
        details = self.cache / f"{key}.features.json"
        with lock(self.cache / f"{key}.lock"):
            if self.valid_artifact(probe, key):
                original = read_json(probe)
            else:
                self.help_once("probe")
                original = self.tool("probe", [source, "--json"])
                if not original.get("audio"):
                    raise ValueError("Input has no audio stream")
                atomic_json(probe, original)
                self.seal(probe, key)
            if self.valid_artifact(packed, key) and self.valid_artifact(details, key):
                with np.load(packed, allow_pickle=False) as data:
                    features = {name: data[name] for name in data.files}
                meta = read_json(details)
                self.stats["features"] = "hit"
            else:
                self.stats["features"] = "miss"
                self.stats["decode"] = "hit" if self.valid_artifact(pcm, key) else "miss"
                if self.stats["decode"] == "miss":
                    self.help_once("audio")
                    with tempfile.TemporaryDirectory(dir=self.cache) as tmp:
                        wav = Path(tmp) / "decoded.wav"
                        self.tool("audio", [source, "-o", wav, "--json"])
                        if not wav.is_file() or wav.stat().st_size < 44:
                            raise ValueError("Skill produced no decoded WAV")
                        if identity(source) != stamp:
                            raise ValueError("Input changed during decode")
                        os.replace(wav, pcm)
                    self.seal(pcm, key)
                features, meta = measure_wav(pcm)
                for name in ("sample_rate", "channels"):
                    expected = original["audio"].get(name)
                    if expected and meta[name] != expected:
                        raise ValueError(f"Decoded {name} differs from source probe")
                with tempfile.TemporaryDirectory(dir=self.cache) as tmp:
                    archive = Path(tmp) / "features.npz"
                    np.savez_compressed(archive, **features)
                    os.replace(archive, packed)
                atomic_json(details, meta)
                self.seal(packed, key)
                self.seal(details, key)
            if identity(source) != stamp:
                raise ValueError("Input changed during measurement")
        return features, meta | dict(source_identity=stamp, source_probe=original,
                                    container_minus_playable_s=float(original.get("duration") or 0)
                                    - meta["duration_s"], feature_key=key)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", help="local song or other media with an audio stream")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--cache", default="workdir/music-cache")
    parser.add_argument("--out", default="workdir/music-analysis", help="owned report directory")
    parser.add_argument("--high-point", type=float, help="explicit high point, in playable-song seconds")
    parser.add_argument("--section-seconds", type=float, default=30.)
    parser.add_argument("--build-seconds", type=float, default=1.)
    parser.add_argument("--candidates", type=int, default=8)
    parser.add_argument("--min-bpm", type=float, default=60.)
    parser.add_argument("--max-bpm", type=float, default=200.)
    parser.add_argument("--publish", help="write validated handoff here, e.g. workdir/music.json")
    parser.add_argument("--overwrite", action="store_true", help="allow replacement of --publish destination")
    args = parser.parse_args(argv)
    started = time.monotonic()
    owned_out = None
    try:
        for name in ("high_point", "section_seconds", "build_seconds", "min_bpm", "max_bpm"):
            if getattr(args, name) is not None:
                number(getattr(args, name), name)
        engine = Music(args.root, args.cache)
        out = engine.generated(args.out)
        publish = engine.generated(args.publish) if args.publish else None
        if publish and publish.exists() and not args.overwrite:
            raise ValueError("Publish destination already exists; use --overwrite to replace it")
        source = engine.source(args.input)
        if publish == source:
            raise ValueError("Cannot replace the input source")
        if publish and (publish.is_relative_to(engine.cache) or
                        publish.is_relative_to(out) and publish != out / "music.json"):
            raise ValueError("Publish destination cannot replace cache/report internals")
        out.mkdir(parents=True, exist_ok=True)
        with lock(out / ".lock"):
            owner = out / ".owner"
            if (owner.exists() and owner.read_text() != PRODUCER or
                    not owner.exists() and any(p.name != ".lock" for p in out.iterdir())):
                raise ValueError("Refusing to replace a non-owned report directory")
            atomic_text(owner, PRODUCER)
            # Clear only this tool's previous owned handoff, so failures cannot leave
            # a stale music.json masquerading as a newly validated selection.
            handoff_path = out / "music.json"
            if source.is_relative_to(out) or source.is_relative_to(engine.cache):
                raise ValueError("Input must be outside generated report/cache directories")
            handoff_path.unlink(missing_ok=True)
            owned_out = out
            atomic_json(out / "manifest.json", dict(producer=PRODUCER, status="running"))
            features, meta = engine.measurements(source)
            analysis = analyze(features, meta, args.section_seconds, args.build_seconds,
                               args.high_point, args.candidates, args.min_bpm, args.max_bpm)
            analysis["measurements"] = meta
            if identity(source) != meta["source_identity"]:
                raise ValueError("Input changed before report publication")
            atomic_json(out / "analysis.json", analysis)
            handoff = None
            if analysis["selected"]:
                selected = analysis["selected"]
                handoff = dict(start_song_t=selected["start_song_t"],
                               beats_song_t=selected["beat_analysis"]["beats_song_t"])
                atomic_json(handoff_path, handoff)
                if publish:
                    publish.parent.mkdir(parents=True, exist_ok=True)
                    with lock(publish.with_suffix(publish.suffix + ".lock")):
                        if publish.exists() and not args.overwrite and publish != handoff_path:
                            raise ValueError("Publish destination appeared while analyzing")
                        atomic_json(publish, handoff)
            manifest = dict(producer=PRODUCER, status=analysis["status"],
                            tool_fingerprint=engine.version, source_identity=meta["source_identity"],
                            feature_key=meta["feature_key"], parameters=vars(args) | {"root": str(args.root)},
                            cache=engine.stats, commands=engine.commands,
                            elapsed_seconds=round(time.monotonic() - started, 4),
                            handoff_sha256=file_hash(handoff_path) if handoff else None,
                            editorial_review="pending")
            atomic_json(out / "manifest.json", manifest)
            with (out / "runs.jsonl").open("a") as stream:
                stream.write(json.dumps(manifest) + "\n")
        print(json.dumps(dict(status=analysis["status"], analysis=str(out / "analysis.json"),
                              music=str(handoff_path) if handoff else None,
                              published=str(publish) if publish and handoff else None,
                              cache=engine.stats, skill_calls=len(engine.commands),
                              elapsed_seconds=manifest["elapsed_seconds"]), indent=2))
        return 0 if handoff else 2
    except (ValueError, KeyError, TypeError, OSError, subprocess.TimeoutExpired) as exc:
        if owned_out:
            atomic_json(owned_out / "manifest.json",
                        dict(producer=PRODUCER, status="failed", error=str(exc)))
        print(json.dumps(dict(status="failed", error=str(exc))), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
