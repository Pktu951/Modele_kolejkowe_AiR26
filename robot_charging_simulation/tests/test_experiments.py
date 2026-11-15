"""Grid validation, reproducibility, and downloadable archive contents."""

from io import BytesIO
import json
from pathlib import Path
import sys
import unittest
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments import build_scenarios, parse_charger_times, parse_values, run_experiments, summarize_experiments
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
        for frame in (raw, summary):
            self.assertTrue(frame["service_type"].eq("shared_deterministic").all())
            self.assertTrue(frame["fixed_charge_time"].eq(20.0).all())
            self.assertTrue(frame["mean_charge_time"].isna().all())

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
            restored = SimulationConfig(**json.loads(archive.read("poisson/config.json")))
            self.assertEqual(simulate(restored).visits, result.visits)

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
            self.assertTrue(frame["service_type"].eq("shared_deterministic").all())
            self.assertTrue(frame["fixed_charge_time"].eq(20.0).all())
            self.assertTrue(frame["mean_charge_time"].isna().all())

    def test_individual_service_grid_prefixes_and_exports(self):
        config = SimulationConfig(model="closed", charger_times=(30.0, 10.0), duration=600)
        scenarios, skipped = build_scenarios(
            config, [1, 2, 3], fleet_sizes=[2, 4], charger_times=(30.0, 10.0, 20.0),
        )
        self.assertEqual(len(scenarios), 5)
        self.assertEqual(skipped, ["N=2, c=3"])
        self.assertEqual([scenario.charger_times for scenario in scenarios], [
            (30.0,), (30.0, 10.0), (30.0,), (30.0, 10.0), (30.0, 10.0, 20.0),
        ])
        raw = run_experiments(scenarios, 2)
        summary = summarize_experiments(raw)
        self.assertEqual(len(raw), 10)
        self.assertEqual(len(summary), 5)
        self.assertTrue(summary["service_type"].eq("individual_deterministic").all())
        self.assertTrue(raw["mean_charge_time"].isna().all())
        self.assertEqual(json.loads(summary.iloc[-1]["charger_times"]), [30.0, 10.0, 20.0])
        result = simulate(scenarios[-1])
        with ZipFile(BytesIO(result_archive([result], {}))) as archive:
            settings = json.loads(archive.read("closed_individual/config.json"))
            self.assertEqual(settings["charger_times"], [30.0, 10.0, 20.0])
            self.assertNotIn("mean_charge_time", settings)
            restored = SimulationConfig(**settings)
            self.assertEqual(simulate(restored).visits, result.visits)

    def test_individual_service_time_parser_and_missing_chargers(self):
        self.assertEqual(parse_charger_times("30, 10; 30"), (30.0, 10.0, 30.0))
        for text in ("", "0,20", "-1,20", "nan,20", "inf,20", "10,", "a,20", ",".join(["10"] * 65)):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_charger_times(text)
        config = SimulationConfig(model="closed", charger_times=(30.0, 10.0))
        with self.assertRaisesRegex(ValueError, "co najmniej 3"):
            build_scenarios(config, [3], fleet_sizes=[4])


if __name__ == "__main__":
    unittest.main()
