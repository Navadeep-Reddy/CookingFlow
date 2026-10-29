#!/usr/bin/env python3
"""Reusable visual evidence; all media decoding/extraction stays in the installed skill.

Examples (paths in plans are relative to --root, default: this repository):
  python3 tools/evidence.py frames Clips/example.mp4 --at 12 --at 14.5
  python3 tools/evidence.py shots workdir/plan.json
  python3 tools/evidence.py shots workdir/plan.json --framing workdir/framing.json
  python3 tools/evidence.py cuts workdir/final.mp4 --plan workdir/plan.json
  python3 tools/evidence.py survey Clips/example.mp4 --tiles 6x4

Shots/cuts/frames write report.html + manifest.json, with reusable PNGs in the
shared cache. HTML uses browser layout/clipping, not image re-encoding. Models
can inspect the listed PNGs individually; HTML is not a pixel-inspected crop.
Survey writes a native skill PNG contact sheet. No video intermediates, Pillow,
raw ffmpeg commands, or installed-skill changes. Repeating a request validates
cached artifact hashes. Changing crops/layout reuses the unmodified frames.
Input identities use resolved path, size, mtime and ctime; outputs use SHA-256.
Each report keeps a runs.jsonl timing/command ledger. Linux/macOS (fcntl locks).
"""
from __future__ import annotations

import argparse
import concurrent.futures
from contextlib import contextmanager
from fractions import Fraction
import hashlib
import html
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 1
PRODUCER = "reel-evidence"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def identity(path):
    """Cheap local input identity; ctime also catches ordinary mtime-preserving edits."""
    p = Path(path).resolve(strict=True)
    s = p.stat()
    if not p.is_file() or not s.st_size:
        raise ValueError(f"Missing or empty input: {p}")
    return dict(path=str(p), size=s.st_size, mtime_ns=s.st_mtime_ns, ctime_ns=s.st_ctime_ns)


def read_json(path):
    return json.loads(Path(path).read_text())


def atomic_json(path, value):
    atomic_text(path, json.dumps(value, indent=2, allow_nan=False) + "\n")


def atomic_text(path, text):
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".write-")
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(text)
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


@contextmanager
def lock(path):
    # Separate processes (e.g. framing and grading agents) share the same cache.
    import fcntl
    with Path(path).open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def number(value, name):
    n = float(value)
    if not math.isfinite(n):
        raise ValueError(f"{name} must be finite")
    return n


def dimensions(meta):
    v = meta.get("video") if isinstance(meta, dict) else None
    if not isinstance(v, dict) or not v:
        raise ValueError("Input has no video stream")
    w, h = int(v["width"]), int(v["height"])
    if v.get("rotation", 0) % 180:
        w, h = h, w
    return w, h


def frame_rate(meta):
    v = meta["video"]
    if v.get("variable_frame_rate_suspected"):
        raise ValueError("Frame-grid sampling requires CFR; use frames --at for time-based VFR inspection")
    rate = Fraction(v.get("r_frame_rate") or str(v["fps"]))
    if rate <= 0:
        raise ValueError("Input has no usable frame rate")
    return rate


def seek_ms(seconds):
    # look.py serializes --at to milliseconds. Floor instead of rounding forward.
    return math.floor(number(seconds, "timestamp") * 1000 + 1e-7)


def shot_samples(start, end, rate, outside=False):
    a = math.ceil(number(start, "src_in") * rate - 1e-7)
    b = math.ceil(number(end, "src_out") * rate - 1e-7)
    if start < 0 or end <= start or b <= a:
        raise ValueError(f"Range contains no frames: [{start}, {end})")
    samples = [("start", a), ("middle", (a + b - 1) // 2), ("end", b - 1)]
    if outside:
        samples.append(("out_excluded", b))
    return [(label, frame, float(Fraction(frame, 1) / rate)) for label, frame in samples]


def crop_box(settings, w, h):
    if "crop" in settings:
        box = settings["crop"]
        vals = [box[k] for k in ("x", "y", "width", "height")]
        if any(isinstance(x, bool) or not isinstance(x, int) for x in vals):
            raise ValueError("Crop coordinates must be integer source pixels")
        x, y, cw, ch = vals
    else:
        zoom = number(settings["zoom"], "zoom")
        cx = number(settings["center_x"], "center_x")
        cy = number(settings["center_y"], "center_y")
        if zoom < 1 or not (0 <= cx <= 1 and 0 <= cy <= 1):
            raise ValueError("Zoom must be >= 1 and centers must lie in [0, 1]")
        # Multiples of 18x32 preserve exact 9:16 and even chroma geometry.
        units = min(math.floor(min(w / 18, h / 32)),
                    round(min(w, h * 9 / 16) / zoom / 18))
        cw, ch = units * 18, units * 32
        x = round((cx * w - cw / 2) / 2) * 2
        y = round((cy * h - ch / 2) / 2) * 2
    if (min(x, y) < 0 or min(cw, ch) <= 0 or x + cw > w or y + ch > h
            or any(v % 2 for v in (x, y, cw, ch)) or cw * 16 != ch * 9):
        raise ValueError(f"Invalid even, in-bounds 9:16 crop: {(x, y, cw, ch)} in {w}x{h}")
    return dict(x=x, y=y, width=cw, height=ch)


def relative_url(path, directory):
    return quote(os.path.relpath(path, directory).replace(os.sep, "/"))


def html_report(items, directory):
    cards = []
    for item in items:
        src = relative_url(item["image"], directory)
        title = f'{item["id"]} / {item["label"]}'
        title += (" — times shown on sheet" if item["id"] == "survey"
                  else f' — {item["source_time"]:.6f} s')
        label = html.escape(title)
        original = f'<img loading="lazy" src="{src}" alt="{label}">'
        crop = item.get("crop")
        preview = ""
        if crop:
            w, h = item["source_width"], item["source_height"]
            x, y, cw, ch = (crop[k] for k in ("x", "y", "width", "height"))
            style = (f"width:{w / cw * 100:.9f}%;height:{h / ch * 100:.9f}%;"
                     f"left:{-x / cw * 100:.9f}%;top:{-y / ch * 100:.9f}%;")
            preview = (f'<div class="crop" style="aspect-ratio:{cw}/{ch}">'
                       f'<img loading="lazy" src="{src}" style="{style}" alt="Crop: {label}"></div>')
        cards.append(f'<figure><figcaption>{label}</figcaption><div class="views">'
                     f'<div class="original">{original}</div>{preview}</div></figure>')
    return """<!doctype html><html lang="en"><meta charset="utf-8">
<title>Reel visual evidence</title><style>
body{background:#181818;color:#eee;font:14px system-ui;margin:20px}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
figure{margin:0;padding:10px;background:#292929}figcaption{margin-bottom:8px}
.views{display:flex;gap:8px;align-items:flex-start}.views>div{flex:1;min-width:0}
.original img{width:100%;height:auto;display:block}.crop{position:relative;overflow:hidden}
.crop img{position:absolute;max-width:none}a{color:#9bd}
</style><h1>Visual evidence</h1><p>Original frames; crop views on the right when supplied.
Labels are source times. Crops are browser views, not newly encoded images.
Review the pixels before approving. <a href="manifest.json">Manifest</a></p><main>""" + "".join(cards) + "</main></html>\n"


class Evidence:
    def __init__(self, root, cache, jobs=2):
        self.root = Path(root).resolve()
        self.workdir = self.root / "workdir"
        self.cache = self.generated(cache)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.scripts = self.root / ".claude/skills/ffmpeg-skill/scripts"
        skill_files = sorted(self.scripts.rglob("*.py"))
        self.version = digest({
            "schema": SCHEMA, "python": sys.version, "wrapper": file_hash(__file__),
            "skill": [(str(p.relative_to(self.scripts)), file_hash(p)) for p in skill_files],
            "executables": {n: identity(shutil.which(n)) if shutil.which(n) else None
                            for n in ("ffmpeg", "ffprobe")},
        })
        self.jobs = jobs
        self.commands = []
        self.hits = self.misses = 0

    def generated(self, value):
        path = Path(value)
        path = (self.root / path).resolve() if not path.is_absolute() else path.resolve()
        if not path.is_relative_to(self.workdir.resolve()) or path == self.workdir.resolve():
            raise ValueError(f"Generated paths must be inside {self.workdir}: {path}")
        return path

    def source(self, value):
        path = Path(value)
        return (self.root / path).resolve() if not path.is_absolute() else path.resolve()

    def tool(self, name, args):
        command = [sys.executable, str(self.scripts / f"{name}.py"), *map(str, args)]
        start = time.monotonic()
        p = subprocess.run(command, capture_output=True, text=True, timeout=600, cwd=self.root)
        entry = dict(command=command, seconds=round(time.monotonic() - start, 4), exit_code=p.returncode)
        self.commands.append(entry)
        if p.returncode:
            raise ValueError(f"Skill {name}.py failed: {p.stdout}\n{p.stderr}")
        try:
            result = json.loads(p.stdout)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Skill {name}.py returned invalid JSON: {p.stdout}") from exc
        if not isinstance(result, dict):
            raise ValueError(f"Skill {name}.py returned an unexpected JSON structure")
        if result.get("status") == "failed":
            raise ValueError(f"Skill {name}.py failed: {result}")
        return result

    def help_once(self, name):
        path = self.cache / f"help-{self.version}-{name}.txt"
        if not path.exists():
            cmd = [sys.executable, str(self.scripts / f"{name}.py"), "--help"]
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=self.root)
            if p.returncode:
                raise ValueError(p.stderr)
            atomic_text(path, p.stdout)

    def probe(self, source):
        source = self.source(source)
        stamp = identity(source)
        key = digest([self.version, stamp, "probe"])
        path = self.cache / f"{key}.probe.json"
        with lock(self.cache / f"{key}.lock"):
            try:
                meta = read_json(path)
                dimensions(meta)
                return source, stamp, meta
            except (OSError, ValueError, KeyError, TypeError):
                pass
            self.help_once("probe")
            meta = self.tool("probe", [source, "--json"])
            dimensions(meta)
            if identity(source) != stamp:
                raise ValueError(f"Input changed during probe: {source}")
            atomic_json(path, meta)
        return source, stamp, meta

    def valid_image(self, key):
        image, record = self.cache / f"{key}.png", self.cache / f"{key}.image.json"
        try:
            data = read_json(record)
            if data["key"] == key and image.stat().st_size > 8 and file_hash(image) == data["sha256"]:
                return image
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return None

    def store_image(self, key, image):
        if not image.is_file() or image.stat().st_size <= 8:
            raise ValueError(f"Skill produced no image: {image}")
        target = self.cache / f"{key}.png"
        checksum = file_hash(image)
        os.replace(image, target)
        atomic_json(self.cache / f"{key}.image.json", dict(key=key, sha256=checksum))
        return target

    def frames(self, source, stamp, times, width):
        # Cache seek requests, not shot IDs: repeated hero shots share extracted pixels.
        requests = {seek_ms(t): digest([self.version, stamp, width, seek_ms(t), "frame"])
                    for t in times}
        paths = {}
        with lock(self.cache / f"{digest([stamp, width])}.frames.lock"):
            missing = []
            for ms, key in requests.items():
                image = self.valid_image(key)
                if image:
                    self.hits += 1
                    paths[ms] = image
                else:
                    missing.append(ms)
                    self.misses += 1
            if missing:
                self.help_once("look")
                batches = [sorted(missing)[i:i + 12] for i in range(0, len(missing), 12)]
                def extract(batch):
                    with tempfile.TemporaryDirectory(dir=self.cache, prefix="extract-") as tmp:
                        args = [source, "--width", width, "--no-timecode", "-o", Path(tmp) / "frame.png", "--json"]
                        for ms in batch:
                            args += ["--at", f"{ms / 1000:.3f}"]
                        result = self.tool("look", args)
                        outputs = result.get("outputs", [])
                        if len(outputs) != len(batch):
                            raise ValueError("Skill frame output count does not match request")
                        # Do not publish partially rendered or concurrently changed inputs.
                        if identity(source) != stamp:
                            raise ValueError(f"Input changed during extraction: {source}")
                        return [(ms, self.store_image(requests[ms], Path(p))) for ms, p in zip(batch, outputs)]
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.jobs) as pool:
                    for batch_paths in pool.map(extract, batches):
                        paths.update(batch_paths)
        return paths


def build_items(args, engine):
    if args.mode == "frames":
        entries = [dict(id="frame", label=f"sample-{i + 1}", source=args.input,
                        source_time=number(t, "timestamp")) for i, t in enumerate(args.at)]
    else:
        plan = read_json(engine.source(args.input if args.mode == "shots" else args.plan))
        shots = plan["shots"]
        ids = [s["id"] for s in shots]
        if not shots or len(ids) != len(set(ids)):
            raise ValueError("Plan must contain shots with unique IDs")
        frames = {}
        if args.mode == "shots" and args.framing:
            settings = read_json(engine.source(args.framing))["shots"]
            frames = {s["id"]: s for s in settings}
            if len(frames) != len(settings) or set(frames) != set(ids):
                raise ValueError("Framing IDs must match plan IDs exactly")
        entries = []
        for index, shot in enumerate(shots):
            src = shot["clip"] if args.mode == "shots" else args.input
            _, _, meta = engine.probe(src)
            rate = frame_rate(meta)
            if args.mode == "shots":
                start, end = (number(shot[k], k) for k in ("src_in", "src_out"))
                samples = shot_samples(start, end, rate, args.include_outside)
            else:
                if not index:
                    continue
                cut = number(shot["out_start"], "out_start") * rate
                frame = round(cut)
                if abs(cut - frame) > 1e-5:
                    raise ValueError("Cut does not lie on the rendered video's frame grid")
                samples = [("before", frame - 1, float(Fraction(frame - 1, 1) / rate)),
                           ("after", frame, float(Fraction(frame, 1) / rate))]
            for label, frame, seconds in samples:
                entry = dict(id=shot["id"], label=label, source=src, source_time=seconds, frame_index=frame)
                if shot["id"] in frames:
                    entry["crop"] = crop_box(frames[shot["id"]], *dimensions(meta))
                entries.append(entry)
    if not entries:
        raise ValueError("No samples requested")
    groups = {}
    for entry in entries:
        source, stamp, meta = engine.probe(entry["source"])
        v = meta["video"]
        duration = v.get("duration") or meta["duration"]
        if not 0 <= entry["source_time"] < float(duration):
            raise ValueError(f"Sample outside picture duration: {entry}")
        entry.update(source=str(source), source_identity=stamp, source_width=dimensions(meta)[0],
                     source_height=dimensions(meta)[1], seek_seconds=seek_ms(entry["source_time"]) / 1000,
                     timing="CFR frame grid" if "frame_index" in entry else "requested time (millisecond seek)")
        groups.setdefault(str(source), (stamp, []))[1].append(entry)
    for source, (stamp, members) in groups.items():
        paths = engine.frames(source, stamp, [e["source_time"] for e in members], args.width)
        for entry in members:
            entry["image"] = str(paths[seek_ms(entry["source_time"])])
    return entries


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=("frames", "shots", "cuts", "survey"))
    parser.add_argument("input", help="video, or plan.json for shots")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--cache", default="workdir/evidence-cache")
    parser.add_argument("--out", help="owned report directory under workdir (default workdir/evidence/MODE)")
    parser.add_argument("--at", action="append", type=float, help="seconds; repeatable for frames")
    parser.add_argument("--framing", help="framing.json for shots (exact crop or legacy zoom/center)")
    parser.add_argument("--plan", help="plan.json for cuts")
    parser.add_argument("--include-outside", action="store_true", help="shots: add first excluded frame; must be before EOF")
    parser.add_argument("--width", type=int, default=540, help="frame preview width; survey uses total sheet width")
    parser.add_argument("--tiles", default="4x3", help="survey grid")
    parser.add_argument("--jobs", type=int, default=2, help="parallel skill batches (1..4)")
    args = parser.parse_args(argv)
    if args.width < 2 or not 1 <= args.jobs <= 4:
        parser.error("--width must be >= 2; --jobs must be 1..4")
    if args.mode == "frames" and not args.at or args.mode == "cuts" and not args.plan:
        parser.error("frames requires --at; cuts requires --plan")
    started = time.monotonic()
    try:
        engine = Evidence(args.root, args.cache, args.jobs)
        out = engine.generated(args.out or f"workdir/evidence/{args.mode}")
        out.mkdir(parents=True, exist_ok=True)
        with lock(out / ".lock"):
            owner = out / ".owner"
            if owner.exists() and owner.read_text() != PRODUCER:
                raise ValueError(f"Report directory belongs to another tool: {out}")
            if not owner.exists() and any(p.name != ".lock" for p in out.iterdir()):
                raise ValueError(f"Refusing to replace an existing non-owned report: {out}")
            atomic_text(owner, PRODUCER)
            if args.mode == "survey":
                source, stamp, meta = engine.probe(args.input)
                cols, rows = map(int, args.tiles.lower().split("x"))
                if min(cols, rows) < 1 or cols * rows > 256 or args.width < 2 * cols:
                    raise ValueError("Survey requires 1..256 tiles and at least 2 pixels per column")
                key = digest([engine.version, stamp, args.width, cols, rows, "survey"])
                with lock(engine.cache / f"{key}.lock"):
                    image = engine.valid_image(key)
                    if image:
                        engine.hits += 1
                    else:
                        engine.misses += 1
                        engine.help_once("look")
                        with tempfile.TemporaryDirectory(dir=engine.cache) as tmp:
                            png = Path(tmp) / "survey.png"
                            engine.tool("look", [source, "--tiles", args.tiles, "--width", args.width, "-o", png, "--json"])
                            if identity(source) != stamp:
                                raise ValueError("Input changed during survey")
                            image = engine.store_image(key, png)
                items = [dict(id="survey", label=args.tiles, source=str(source), source_identity=stamp,
                              source_time=0, image=str(image), source_width=dimensions(meta)[0],
                              source_height=dimensions(meta)[1])]
            else:
                items = build_items(args, engine)
            for item in items:
                if identity(item["source"]) != item["source_identity"]:
                    raise ValueError(f'Input changed while building evidence: {item["source"]}')
            manifest = dict(producer=PRODUCER, schema=SCHEMA, tool_fingerprint=engine.version,
                            parameters=vars(args) | {"root": str(args.root)}, items=items,
                            cache=dict(hits=engine.hits, misses=engine.misses), commands=engine.commands,
                            elapsed_seconds=round(time.monotonic() - started, 4), visual_review="pending")
            atomic_text(out / "report.html", html_report(items, out))
            atomic_json(out / "manifest.json", manifest)
            with (out / "runs.jsonl").open("a") as log:
                log.write(json.dumps(dict(time_ns=time.time_ns(), cache=manifest["cache"],
                                          elapsed_seconds=manifest["elapsed_seconds"],
                                          tool_fingerprint=engine.version,
                                          commands=engine.commands)) + "\n")
        print(json.dumps(dict(status="completed", report=str(out / "report.html"),
                              manifest=str(out / "manifest.json"), samples=len(items),
                              cache=manifest["cache"], skill_calls=len(engine.commands),
                              elapsed_seconds=manifest["elapsed_seconds"]), indent=2))
        return 0
    except (ValueError, KeyError, TypeError, ZeroDivisionError, OSError, subprocess.TimeoutExpired) as exc:
        print(json.dumps(dict(status="failed", error=str(exc))), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
