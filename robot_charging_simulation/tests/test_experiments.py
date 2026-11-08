"""Grid validation, reproducibility, and downloadable archive contents."""

from io import BytesIO
import json
from pathlib import Path
import sys
import unittest
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments import build_scenarios, parse_values, run_experiments, summarize_experiments
from exports import result_archive
from models import SimulationConfig
from simulation import simulate


class ExperimentTests(unittest.TestCase):
    def test_grid_and_repetition_counts(self):
        scenarios, skipped = build_scenarios(SimulationConfig(duration=600), [1, 2], arrival_rates_per_hour=[2, 4])
        self.assertEqual(len(scenarios), 8)
        self.assertEqual(skipped, [])
        raw = run_experiments(scenarios, 2)
        summary = summarize_experiments(raw)
        self.assertEqual(len(raw), 16)
        self.assertEqual(len(summary), 8)
        self.assertTrue(summary["repetitions"].eq(2).all())
        self.assertTrue(summary["mean_system_size_std"].notna().all())
        self.assertEqual(raw["seed"].tolist(), [42, 43] * 8)

    def test_invalid_closed_combinations_are_reported(self):
        configs, skipped = build_scenarios(SimulationConfig(model="closed"), [1, 3], fleet_sizes=[2, 4])
        self.assertEqual(len(configs), 3)
        self.assertEqual(len(skipped), 1)
        self.assertEqual(configs[0].fleet_size, 2)

    def test_numeric_grid_rejects_invalid_input(self):
        self.assertEqual(parse_values("1,2;3,2", integer=True), [1, 2, 3])
        for text in ("", "nan", "inf", "0", "1+2"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_values(text)
        with self.assertRaises(ValueError):
            parse_values("1.5", integer=True)

    def test_archive_records_settings_and_pending_visits(self):
        result = simulate(SimulationConfig(duration=100))
        with ZipFile(BytesIO(result_archive([result], {}))) as archive:
            self.assertIn("poisson/config.json", archive.namelist())
            self.assertIn("poisson/history.csv", archive.namelist())
            self.assertIn("poisson/visits.csv", archive.namelist())
            self.assertIn("poisson/first_500_events.csv", archive.namelist())

    def test_closed_exports_keep_availability_without_threshold(self):
        config = SimulationConfig(model="closed", fleet_size=2, chargers=1, duration=100)
        result = simulate(config)
        with ZipFile(BytesIO(result_archive([result], {}))) as archive:
            settings = json.loads(archive.read("closed/config.json"))
            self.assertNotIn("min_available", settings)
            history_columns = archive.read("closed/history.csv").decode().splitlines()[0].split(",")
            self.assertNotIn("shortage_probability", history_columns)
            self.assertIn("mean_available_robots", history_columns)
            self.assertIn("availability", history_columns)
        raw = run_experiments([config], 2)
        summary = summarize_experiments(raw)
        for frame in (raw, summary):
            self.assertNotIn("min_available", frame.columns)
            self.assertFalse(any("shortage" in name for name in frame.columns))
            self.assertIn("availability", frame.columns)


if __name__ == "__main__":
    unittest.main()
