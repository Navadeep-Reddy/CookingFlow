"""Numerical beat tests and fake-skill cache/publication regression tests."""
import contextlib
import importlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

try:
    from . import music
except ImportError:
    import music


def pulse_features(duration=100., period=.8, offset=.32, jitter=0.):
    times = np.arange(.05, duration, .01)
    beats = np.arange(offset, duration - .05, period)
    if jitter:
        beats = beats + np.random.default_rng(42).uniform(-jitter, jitter, len(beats))
    peaks = np.unique(np.searchsorted(times, beats).clip(0, len(times) - 1))
    flux = np.zeros(len(times))
    flux[peaks] = 10
    energy_t = np.arange(0, duration + .001, .01)
    powers = np.where(energy_t[:-1] < 20, .001, .05)
    return dict(times=times, flux=flux, peaks=peaks, energy_t=energy_t,
                energy_sum=np.r_[0., np.cumsum(powers * .01)])


class FakeMusic(music.Music):
    calls = []

    def help_once(self, name):
        pass

    def tool(self, name, args):
        self.calls.append(name)
        self.commands.append(dict(tool=name))
        if name == "probe":
            return dict(duration=100.04, audio=dict(sample_rate=44100, channels=2))
        Path(args[args.index("-o") + 1]).write_bytes(b"fake skill PCM" * 10)
        return dict(status="completed")


class MusicTests(unittest.TestCase):
    def test_recovers_known_tempo_at_arbitrary_song_offsets(self):
        for period, start in ((.5, 8.), (.8, 43.17), (.63, 61.03)):
            with self.subTest(period=period, start=start):
                result = music.fit_beats(pulse_features(period=period), start, 30)
                self.assertTrue(result["valid"], result["reasons"])
                self.assertAlmostEqual(result["period_s"], period, delta=.003)
                self.assertGreater(result["support_fraction"], .97)
                self.assertLess(result["p95_abs_error_ms"], 11)
                self.assertTrue(all(start <= t < start + 30 for t in result["beats_song_t"]))

    def test_irregular_onsets_and_silence_do_not_create_valid_handoffs(self):
        f = pulse_features(jitter=.19)
        self.assertFalse(music.fit_beats(f, 35, 30)["valid"])
        f["flux"][:] = 0
        f["peaks"] = np.array([], dtype=int)
        result = music.analyze(f, dict(duration_s=100.))
        self.assertEqual(result["status"], "needs_review")
        self.assertIsNone(result["selected"])

    def test_missing_beat_block_fails_validation(self):
        f = pulse_features()
        f["peaks"] = f["peaks"][~((f["times"][f["peaks"]] >= 40) &
                                  (f["times"][f["peaks"]] < 50))]
        f["flux"][ (f["times"] >= 40) & (f["times"] < 50)] = 0
        result = music.fit_beats(f, 30, 30)
        self.assertFalse(result["valid"])
        self.assertTrue(any("beginning/middle/end" in r for r in result["reasons"]))

    def test_antiphase_stereo_power_and_onsets_do_not_cancel(self):
        sr = 11025
        t = np.arange(sr * 12) / sr
        x = (.3 * np.sin(2 * np.pi * 400 * t) * ((t % .8) < .08) * 32767).astype(np.int16)
        mono, _ = music.extract_features(sr, x)
        stereo, meta = music.extract_features(sr, np.column_stack([x, -x]))
        self.assertEqual(meta["channels"], 2)
        np.testing.assert_allclose(mono["energy_sum"], stereo["energy_sum"])
        np.testing.assert_allclose(mono["flux"], stereo["flux"])
        self.assertGreater(len(stereo["peaks"]), 10)
        self.assertGreater(music.mean_power(stereo, 0, 12), .001)
        # STFT-derived attacks remain close to the independently known waveform edges.
        onset_t = stereo["times"][stereo["peaks"]]
        attacks = np.arange(.8, 11.9, .8)
        errors = [min(abs(onset_t - a)) for a in attacks]
        self.assertLess(max(errors), .04)

    def test_high_point_bounds_and_no_synthetic_beats(self):
        f = pulse_features()
        result = music.analyze(f, dict(duration_s=100.), high_point=58.)
        selected = result["selected"]
        self.assertEqual(selected["start_song_t"], 57.)
        self.assertEqual(selected["build_s"], 1.)
        actual = set(np.round(f["times"][f["peaks"]], 6))
        self.assertTrue(set(selected["beat_analysis"]["beats_song_t"]).issubset(actual))
        for high in (-1., .1, 71.):
            with self.assertRaises(ValueError):
                music.analyze(f, dict(duration_s=100.), high_point=high)

    def test_one_onset_cannot_support_multiple_beats(self):
        grid = np.array([1., 1.03, 2.])
        kept, found = music.nearest_onsets(grid, np.array([1.01, 2.01]), .06)
        self.assertEqual(len(found), len(set(found)))
        self.assertEqual(len(kept), 2)

    def test_import_has_no_media_or_numerical_side_effects(self):
        with patch.object(music.Evidence, "tool", side_effect=AssertionError("media on import")), \
                patch("scipy.io.wavfile.read", side_effect=AssertionError("WAV on import")):
            importlib.reload(music)


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "song.mp3").write_bytes(b"synthetic source identity")
        (self.root / "workdir").mkdir()
        FakeMusic.calls = []
        self.measured = patch.object(music, "measure_wav", return_value=(
            pulse_features(), dict(duration_s=100., sample_rate=44100, channels=2)))
        self.measure = self.measured.start()
        self.addCleanup(self.measured.stop)

    def engine(self):
        return FakeMusic(self.root)

    def test_reuses_measurements_and_rebuilds_features_without_decoding(self):
        first = self.engine()
        _, meta = first.measurements("song.mp3")
        self.assertEqual(FakeMusic.calls, ["probe", "audio"])
        again = self.engine()
        again.measurements("song.mp3")
        self.assertEqual(again.stats, dict(features="hit"))
        self.assertEqual(self.measure.call_count, 1)
        packed = first.cache / (meta["feature_key"] + ".npz")
        packed.write_bytes(b"corrupt feature cache")
        rebuilt = self.engine()
        rebuilt.measurements("song.mp3")
        self.assertEqual(rebuilt.stats, dict(features="miss", decode="hit"))
        self.assertEqual(FakeMusic.calls, ["probe", "audio"])
        self.assertEqual(self.measure.call_count, 2)

    def test_source_change_invalidates_measurements(self):
        self.engine().measurements("song.mp3")
        (self.root / "song.mp3").write_bytes(b"changed source")
        self.engine().measurements("song.mp3")
        self.assertEqual(FakeMusic.calls, ["probe", "audio", "probe", "audio"])

    def test_tool_version_change_invalidates_measurements(self):
        self.engine().measurements("song.mp3")
        changed = self.engine()
        changed.version = "changed-tool-version"
        changed.measurements("song.mp3")
        self.assertEqual(FakeMusic.calls, ["probe", "audio", "probe", "audio"])

    def test_failed_skill_decode_publishes_no_features(self):
        e = self.engine()
        original = e.tool
        def failing(name, args):
            if name == "audio":
                raise ValueError("fake skill decode failed")
            return original(name, args)
        with patch.object(e, "tool", side_effect=failing):
            with self.assertRaisesRegex(ValueError, "decode failed"):
                e.measurements("song.mp3")
        self.assertEqual(list(e.cache.glob("*.npz")), [])
        self.assertEqual(list(e.cache.glob("*.wav")), [])

    def test_corrupt_pcm_redecoded_when_features_need_rebuilding(self):
        e = self.engine()
        _, meta = e.measurements("song.mp3")
        (e.cache / (meta["feature_key"] + ".npz")).unlink()
        (e.cache / (meta["feature_key"] + ".wav")).write_bytes(b"bad PCM")
        self.engine().measurements("song.mp3")
        self.assertEqual(FakeMusic.calls, ["probe", "audio", "audio"])

    def run_main(self, *extra):
        factory = lambda root, cache: FakeMusic(root, cache)
        with patch.object(music, "Music", side_effect=factory), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return music.main(["song.mp3", "--root", str(self.root), *extra])

    def test_publication_schema_and_explicit_replacement(self):
        args = ("--high-point", "58", "--publish", "workdir/music.json")
        self.assertEqual(self.run_main(*args), 0)
        handoff = json.loads((self.root / "workdir/music.json").read_text())
        self.assertEqual(set(handoff), {"start_song_t", "beats_song_t"})
        self.assertEqual(handoff["start_song_t"], 57.)
        self.assertEqual(self.run_main(*args), 1)
        self.assertEqual(self.run_main(*args, "--overwrite"), 0)
        self.assertEqual(FakeMusic.calls, ["probe", "audio"])

    def test_failed_validation_removes_only_owned_stale_handoff(self):
        self.assertEqual(self.run_main("--high-point", "58"), 0)
        out = self.root / "workdir/music-analysis"
        with patch.object(music, "analyze", return_value=dict(status="needs_review", selected=None)):
            self.assertEqual(self.run_main(), 2)
        self.assertFalse((out / "music.json").exists())
        self.assertEqual(json.loads((out / "manifest.json").read_text())["status"], "needs_review")

    def test_protects_sources_and_foreign_report_directories(self):
        self.assertEqual(self.run_main("--out", "."), 1)
        foreign = self.root / "workdir/foreign"
        foreign.mkdir()
        (foreign / "user.txt").write_text("keep")
        self.assertEqual(self.run_main("--out", "workdir/foreign"), 1)
        self.assertEqual((foreign / "user.txt").read_text(), "keep")
        self.assertEqual(self.run_main("--publish", "song.mp3", "--overwrite"), 1)
        self.assertEqual(self.run_main("--publish", "workdir/music-analysis/analysis.json"), 1)

    def test_failed_attempts_are_appended_with_timing(self):
        with patch.object(music, "analyze", side_effect=ValueError("analysis failed")):
            self.assertEqual(self.run_main(), 1)
            self.assertEqual(self.run_main(), 1)
        runs = (self.root / "workdir/music-analysis/runs.jsonl").read_text().splitlines()
        self.assertEqual(len(runs), 2)
        self.assertTrue(all(json.loads(line)["status"] == "failed" for line in runs))
        self.assertTrue(all("elapsed_seconds" in json.loads(line) for line in runs))


if __name__ == "__main__":
    unittest.main()
