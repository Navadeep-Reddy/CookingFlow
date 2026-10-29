import copy
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest

try:
    from . import render_edit as r
except ImportError:
    import render_edit as r


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.plan = dict(shots=[dict(id="a", clip="source.mp4", src_in=10., src_out=12.,
                                    speed=1.25, out_start=0., out_end=1.6,
                                    keep_original_audio=True, moment_id="m")],
                         music=dict(file="song.mp3", start=3.), duration=1.6)
        self.framing = dict(shots=[dict(id="a", crop=dict(x=0, y=0, width=2160, height=3840))])
        self.policy = dict(shots=dict(a=dict(gain_db=-5, mute=False, fade_in=.02, fade_out=.025)),
                           music_gain_db=-3)
        self.probes = {"source.mp4": dict(duration=100, video=dict(width=2160, height=3840,
            fps=30, r_frame_rate="30/1", duration=100), audio=dict(channels=2))}

    def compile(self):
        return r.compile_plan(self.plan, self.framing, self.policy, self.probes)

    def test_frame_arithmetic_and_crop_compilation(self):
        result = self.compile()
        self.assertEqual((result["total_frames"], result["frame"]), (48, dict(width=2160, height=3840)))
        self.assertEqual(result["shots"][0]["source_frames"], 60)
        self.assertEqual(result["shots"][0]["crop"], self.framing["shots"][0]["crop"])
        self.assertEqual(r.frame_index(1001 / 30000, Fraction(30000, 1001)), 1)
        with self.assertRaises(ValueError):
            r.frame_index(.017)

    def test_rejects_inconsistent_timing_and_nonfinite_values(self):
        for key, value in (("speed", 2.5), ("src_out", 101), ("src_in", float("nan")),
                           ("out_start", .2), ("out_end", 1.61)):
            with self.subTest(key=key):
                saved = copy.deepcopy(self.plan)
                self.plan["shots"][0][key] = value
                with self.assertRaises(ValueError):
                    self.compile()
                self.plan = saved

    def test_under30_audio_and_framing_contract(self):
        self.plan["duration"] = 30
        with self.assertRaises(ValueError):
            self.compile()
        self.plan["duration"] = 1.6
        self.policy["music_fade_out"] = .5
        with self.assertRaises(ValueError):
            self.compile()
        self.policy["music_fade_out"] = 0
        self.framing["shots"][0]["id"] = "unknown"
        with self.assertRaises(ValueError):
            self.compile()

    def test_selected_window_containment(self):
        footage = dict(stages=[dict(name="stage", moments=[dict(id="m", clip="source.mp4", start=10, end=12)])])
        r.compile_plan(self.plan, self.framing, self.policy, self.probes, footage)
        footage["stages"][0]["moments"][0]["end"] = 11
        with self.assertRaises(ValueError):
            r.compile_plan(self.plan, self.framing, self.policy, self.probes, footage)

    def test_version_specific_lut_semantics_and_endpoints(self):
        original_first = ["[o][g2]blend=all_mode=normal:all_opacity=0.5"]
        graded_first = ["[g2][o]blend=all_mode=normal:all_opacity=0.5"]
        self.assertAlmostEqual(r.lut_flag(.12, original_first), .88)
        self.assertAlmostEqual(r.lut_flag(.12, graded_first), .12)
        self.assertEqual(r.lut_flag(0, original_first), 0)
        self.assertEqual(r.lut_flag(1, original_first), 1)
        with self.assertRaises(ValueError):
            r.lut_flag(.2, ["unknown graph"])


class FakeRunner(r.Runner):
    def help_once(self, name):
        pass

    def tool(self, name, args):
        self.commands.append(dict(tool=name, args=list(map(str, args))))
        if "--dry-run" not in args:
            Path(args[args.index("-o") + 1]).write_bytes(b"owned media output")
        return dict(verified=True, commands=["fake skill command"],
                    probe=dict(video=dict(width=2160, height=3840, nb_frames=30, fps=30)))


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "source.mp4").write_bytes(b"fake source")

    def stage(self, engine, gain=0):
        src = self.root / "source.mp4"
        return engine.step("shot", "audio", [src, "--gain", gain], [src],
                           expected=dict(nb_frames=30))

    def test_missing_corrupt_artifacts_and_parameter_changes(self):
        first = FakeRunner(self.root)
        output, _ = self.stage(first)
        self.assertEqual(len(first.commands), 2)
        again = FakeRunner(self.root)
        self.stage(again)
        self.assertEqual(again.commands, [])
        output.write_bytes(b"corrupt")
        rebuilt = FakeRunner(self.root)
        self.stage(rebuilt)
        self.assertEqual(len(rebuilt.commands), 2)
        output.unlink()
        missing = FakeRunner(self.root)
        self.stage(missing)
        self.assertEqual(len(missing.commands), 2)
        changed = FakeRunner(self.root)
        self.stage(changed, gain=-4)
        self.assertEqual(len(changed.commands), 2)

    def test_source_change_and_invalid_output_probe(self):
        self.stage(FakeRunner(self.root))
        (self.root / "source.mp4").write_bytes(b"changed source")
        e = FakeRunner(self.root)
        self.stage(e)
        self.assertEqual(len(e.commands), 2)
        with self.assertRaises(ValueError):
            r.validate_probe(dict(video=dict(nb_frames=31)), dict(nb_frames=30))


if __name__ == "__main__":
    unittest.main()
