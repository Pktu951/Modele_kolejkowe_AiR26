"""Grid validation, reproducibility, and downloadable archive contents."""

from io import BytesIO
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
        configs, skipped = build_scenarios(SimulationConfig(model="closed", min_available=1), [1, 3], fleet_sizes=[2, 4])
        self.assertEqual(len(configs), 3)
        self.assertEqual(len(skipped), 1)
        self.assertEqual(configs[0].min_available, 1)

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


if __name__ == "__main__":
    unittest.main()
