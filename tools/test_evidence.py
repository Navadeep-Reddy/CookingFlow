"""Run: python3 -m unittest discover -s tools -p 'test_*.py' -v

Tests use a fake skill backend; real-media smoke checks use evidence.py itself.
"""
import argparse
import base64
from contextlib import redirect_stderr, redirect_stdout
from fractions import Fraction
import io
import json
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch

from evidence import (ROOT, Evidence, build_items, crop_box, dimensions,
                      frame_rate, html_report, identity, main, seek_ms, shot_samples)


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/a9sAAAAASUVORK5CYII=")


class FakeEvidence(Evidence):
    def __init__(self, root, cache, jobs=2):
        super().__init__(root, cache, jobs)
        self.look_calls = 0
        self.probe_calls = 0

    def help_once(self, name):
        pass

    def tool(self, name, args):
        if name == "probe":
            self.probe_calls += 1
            return {"duration": 12, "video": {
                "width": 2160, "height": 3840, "fps": 30,
                "r_frame_rate": "30/1", "duration": 12, "rotation": 0,
            }}
        self.look_calls += 1
        times = [args[i + 1] for i, arg in enumerate(args) if arg == "--at"]
        output = Path(args[args.index("-o") + 1])
        outputs = []
        for time in times or ["sheet"]:
            path = output.with_name(f"frame_{time}s.png") if len(times) > 1 else output
            path.write_bytes(PNG)
            outputs.append(str(path))
        return {"status": "completed", "outputs": outputs}


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT / "workdir"
        parent.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent, prefix="evidence-unittest-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "clip.mp4"
        self.source.write_bytes(b"fake source input")
        self.cache = "workdir/cache"
        self.engine = FakeEvidence(self.root, self.cache)

    def test_half_open_ranges_and_fractional_frame_rates(self):
        samples = shot_samples(1, 2, Fraction(30), True)
        self.assertEqual([s[1] for s in samples], [30, 44, 59, 60])
        self.assertEqual(shot_samples(1.01, 1.05, Fraction(30))[0][1], 31)
        rate = Fraction(30000, 1001)
        samples = shot_samples(0, 1.001, rate)
        self.assertEqual(samples[-1][1], 29)
        self.assertEqual(seek_ms(Fraction(1, 24)), 41)
        with self.assertRaises(ValueError):
            shot_samples(1.001, 1.002, Fraction(30))

    def test_rotation_vfr_and_legacy_crop_conversion(self):
        self.assertEqual(dimensions({"video": {"width": 3840, "height": 2160, "rotation": 90}}), (2160, 3840))
        self.assertEqual(crop_box({"zoom": 1.2, "center_x": .5, "center_y": .45}, 2160, 3840),
                         {"x": 180, "y": 128, "width": 1800, "height": 3200})
        box = crop_box({"zoom": 1, "center_x": .5, "center_y": .5}, 1920, 1080)
        self.assertEqual(box["width"] * 16, box["height"] * 9)
        with self.assertRaises(ValueError):
            frame_rate({"video": {"variable_frame_rate_suspected": True}})

    def test_invalid_crops_are_rejected(self):
        for box in [dict(x=1, y=0, width=1800, height=3200),
                    dict(x=0, y=0, width=1800, height=3202),
                    dict(x=500, y=0, width=1800, height=3200),
                    dict(x=0, y=0, width=1800.0, height=3200)]:
            with self.subTest(box=box), self.assertRaises(ValueError):
                crop_box({"crop": box}, 2160, 3840)

    def test_probe_and_frames_reuse_across_process_instances(self):
        source, stamp, _ = self.engine.probe(self.source)
        first = self.engine.frames(source, stamp, [1, 1, 2], 540)
        self.assertEqual(self.engine.look_calls, 1)
        self.assertEqual(self.engine.misses, 2)
        resumed = FakeEvidence(self.root, self.cache)
        resumed.probe(self.source)
        second = resumed.frames(source, stamp, [2, 1], 540)
        self.assertEqual(first, second)
        self.assertEqual(resumed.look_calls, 0)
        self.assertEqual(resumed.probe_calls, 0)
        self.assertEqual(resumed.hits, 2)

    def test_missing_or_corrupt_images_are_rebuilt_selectively(self):
        source, stamp, _ = self.engine.probe(self.source)
        paths = self.engine.frames(source, stamp, [1, 2, 3], 540)
        paths[1000].unlink()
        paths[2000].write_bytes(b"corrupt cached output")
        resumed = FakeEvidence(self.root, self.cache)
        resumed.frames(source, stamp, [1, 2, 3], 540)
        self.assertEqual((resumed.hits, resumed.misses, resumed.look_calls), (1, 2, 1))
        self.assertEqual(paths[1000].read_bytes(), PNG)
        self.assertEqual(paths[2000].read_bytes(), PNG)

    def test_corrupt_probe_cache_is_rebuilt(self):
        self.engine.probe(self.source)
        probe = next((self.root / self.cache).glob("*.probe.json"))
        probe.write_text("[]")
        resumed = FakeEvidence(self.root, self.cache)
        resumed.probe(self.source)
        self.assertEqual(resumed.probe_calls, 1)

    def test_skill_failure_does_not_publish_an_image(self):
        source, stamp, _ = self.engine.probe(self.source)
        with patch.object(self.engine, "tool", return_value={"outputs": []}):
            with self.assertRaises(ValueError):
                self.engine.frames(source, stamp, [1], 540)
        self.assertEqual(list((self.root / self.cache).glob("*.image.json")), [])

    def test_existing_foreign_reports_are_not_overwritten(self):
        out = self.root / "workdir/report"
        out.mkdir()
        existing = out / "report.html"
        existing.write_text("user-owned report")
        with patch("evidence.Evidence", FakeEvidence), redirect_stderr(io.StringIO()):
            result = main(["frames", "clip.mp4", "--at", "1", "--root", str(self.root),
                           "--out", "workdir/report"])
        self.assertEqual(result, 1)
        self.assertEqual(existing.read_text(), "user-owned report")

    def test_source_parameters_and_tool_changes_invalidate(self):
        source, stamp, _ = self.engine.probe(self.source)
        original = self.engine.frames(source, stamp, [1], 540)[1000]
        wider = self.engine.frames(source, stamp, [1], 720)[1000]
        self.assertNotEqual(original, wider)
        self.source.write_bytes(b"changed source with different content")
        changed = self.engine.frames(source, identity(source), [1], 540)[1000]
        self.assertNotEqual(original, changed)
        self.engine.version = "another-skill-version"
        versioned = self.engine.frames(source, identity(source), [1], 540)[1000]
        self.assertNotEqual(changed, versioned)

    def test_crop_changes_reuse_frames_and_html_escapes_labels(self):
        plan = self.root / "plan.json"
        plan.write_text(json.dumps({"shots": [{"id": "<shot>", "clip": "clip.mp4", "src_in": 1, "src_out": 2}]}))
        framing = self.root / "framing.json"
        def settings(x):
            framing.write_text(json.dumps({"shots": [{"id": "<shot>", "crop": {
                "x": x, "y": 0, "width": 1800, "height": 3200}}]}))
        args = argparse.Namespace(mode="shots", input=str(plan), framing=str(framing),
                                  include_outside=False, width=540)
        settings(100)
        first = build_items(args, self.engine)
        settings(200)
        second = build_items(args, self.engine)
        self.assertEqual(self.engine.look_calls, 1)
        self.assertEqual([x["image"] for x in first], [x["image"] for x in second])
        self.assertNotEqual(first[0]["crop"], second[0]["crop"])
        page = html_report(second, self.root)
        self.assertIn("&lt;shot&gt;", page)
        self.assertNotIn("<shot>", page)
        self.assertIn("left:-11.111111111%", page)

    def test_invalid_requests_fail_before_extraction(self):
        plan = self.root / "plan.json"
        plan.write_text(json.dumps({"shots": [{"id": "s1", "clip": "clip.mp4", "src_in": 11, "src_out": 13}]}))
        args = argparse.Namespace(mode="shots", input=str(plan), framing=None,
                                  include_outside=False, width=540)
        with self.assertRaises(ValueError):
            build_items(args, self.engine)
        self.assertEqual(self.engine.look_calls, 0)
        with self.assertRaises(ValueError):
            self.engine.generated("Clips/generated")
        with self.assertRaises(ValueError):
            self.engine.generated("workdir/../../escape")

    def test_cuts_sample_immediately_adjacent_frames(self):
        plan = self.root / "plan.json"
        plan.write_text(json.dumps({"shots": [{"id": "s1", "out_start": 0}, {"id": "s2", "out_start": 2}]}))
        args = argparse.Namespace(mode="cuts", input=str(self.source), plan=str(plan), width=540)
        items = build_items(args, self.engine)
        self.assertEqual([x["frame_index"] for x in items], [59, 60])

    def test_survey_defaults_to_readable_tiles_and_retains_explicit_width(self):
        for extra, expected in (([], 2160), (["--tile-width", "480"], 2880), (["--width", "540"], 540)):
            with patch("evidence.Evidence", FakeEvidence), redirect_stdout(io.StringIO()):
                code = main(["survey", "clip.mp4", "--tiles", "6x4", "--root", str(self.root), *extra])
            self.assertEqual(code, 0)
            manifest = json.loads((self.root / "workdir/evidence/survey/manifest.json").read_text())
            self.assertEqual(manifest["parameters"]["width"], expected)
            self.assertEqual(manifest["items"][0]["tile_width"], expected // 6)
            self.assertEqual(manifest["items"][0]["sample_interval_seconds"], .5)

    def test_failed_evidence_attempt_is_preserved(self):
        for _ in range(2):
            with patch("evidence.Evidence", FakeEvidence), redirect_stderr(io.StringIO()):
                code = main(["frames", "clip.mp4", "--at", "99", "--root", str(self.root)])
            self.assertEqual(code, 1)
        runs = (self.root / "workdir/evidence/frames/runs.jsonl").read_text().splitlines()
        self.assertEqual(len(runs), 2)
        self.assertTrue(all(json.loads(line)["status"] == "failed" for line in runs))

    def test_short_survey_reports_effective_grid(self):
        class ShortEvidence(FakeEvidence):
            def tool(self, name, args):
                result = super().tool(name, args)
                if name == "probe":
                    result["duration"] = .1
                return result
        with patch("evidence.Evidence", ShortEvidence), redirect_stdout(io.StringIO()):
            self.assertEqual(main(["survey", "clip.mp4", "--tiles", "6x4", "--root", str(self.root)]), 0)
        manifest = json.loads((self.root / "workdir/evidence/survey/manifest.json").read_text())
        self.assertEqual(manifest["items"][0]["label"], "3x1")
        self.assertEqual(manifest["parameters"]["width"], 1080)

    def test_timeout_keeps_command_and_elapsed_record(self):
        engine = Evidence(self.root, self.cache)
        with patch("evidence.subprocess.run", side_effect=subprocess.TimeoutExpired("look", 600)):
            with self.assertRaises(subprocess.TimeoutExpired):
                engine.tool("look", [self.source, "--at", 1, "--json"])
        self.assertEqual(engine.commands[-1]["exit_code"], None)
        self.assertIn("timed out", engine.commands[-1]["error"])
        self.assertGreaterEqual(engine.commands[-1]["seconds"], 0)

    def test_nonfinite_cli_timestamp_cannot_break_failure_logging(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            main(["frames", "clip.mp4", "--at", "nan", "--root", str(self.root)])
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
