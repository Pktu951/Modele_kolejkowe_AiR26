"""Validate closed-model rate meanings, units, endpoint states, and export."""

from dataclasses import replace
from io import BytesIO
from math import isnan, nextafter
from pathlib import Path
import sys
import unittest
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from exports import result_archive
from metrics import closed_arrival_summary
from models import SimulationConfig
from simulation import ChargingSimulation, simulate


class ClosedArrivalIntensityTests(unittest.TestCase):
    def test_seed_41_rates_and_endpoint_export(self):
        result = simulate(SimulationConfig(model="closed", seed=41, duration=100))
        summary = closed_arrival_summary(result)
        self.assertEqual(summary, {
            "time": 100, "arrivals": 11, "queue_length": 1,
            "busy_chargers": 2, "working_robots": 7,
            "alpha_per_hour": 0.5, "state_arrival_rate_per_hour": 3.5,
            "observed_arrival_rate_per_hour": 6.6,
        })
        with ZipFile(BytesIO(result_archive([result], {}))) as archive:
            frame = pd.read_csv(BytesIO(archive.read("closed/arrival_intensity.csv")))
            self.assertEqual(frame.iloc[0].to_dict(), summary)

    def test_no_arrivals_keep_source_and_state_rates_positive(self):
        config = SimulationConfig(model="closed", fleet_size=2, chargers=1, duration=1)
        engine = ChargingSimulation(config)
        engine.work_duration = lambda: 120.0
        result = engine.run()
        summary = closed_arrival_summary(result)
        self.assertEqual(summary["alpha_per_hour"], 0.5)
        self.assertEqual(summary["state_arrival_rate_per_hour"], 1.0)
        self.assertEqual(summary["observed_arrival_rate_per_hour"], 0.0)
        self.assertEqual(summary["working_robots"], 2)
        initial = closed_arrival_summary(replace(result, history=[result.history[0]]))
        self.assertTrue(isnan(initial["observed_arrival_rate_per_hour"]))

    def test_all_robots_at_station_give_zero_state_rate_in_both_closed_variants(self):
        for times in (None, (20.0,)):
            with self.subTest(charger_times=times):
                config = SimulationConfig(
                    model="closed", fleet_size=2, chargers=1, duration=2,
                    mean_work_time=1, charger_times=times,
                )
                engine = ChargingSimulation(config)
                engine.work_duration = lambda: 1.0
                engine.charge_duration = lambda: 20.0
                result = engine.run()
                summary = closed_arrival_summary(result)
                self.assertEqual(summary["alpha_per_hour"], 60.0)
                self.assertEqual(summary["state_arrival_rate_per_hour"], 0.0)
                self.assertEqual(summary["observed_arrival_rate_per_hour"], 60.0)
                self.assertEqual(summary["working_robots"], 0)
                self.assertEqual(summary["queue_length"], 1)
                self.assertEqual(summary["busy_chargers"], 1)
                if config.individual_service:
                    with ZipFile(BytesIO(result_archive([result], {}))) as archive:
                        self.assertIn("closed_individual/arrival_intensity.csv", archive.namelist())

    def test_open_results_do_not_report_closed_source_rates(self):
        result = simulate(SimulationConfig(duration=10))
        with self.assertRaises(ValueError):
            closed_arrival_summary(result)
        with ZipFile(BytesIO(result_archive([result], {}))) as archive:
            self.assertNotIn("poisson/arrival_intensity.csv", archive.namelist())

    def test_selected_times_use_the_original_full_trajectory(self):
        result = simulate(SimulationConfig(model="closed", seed=41, duration=120, sample_count=2))
        at_100 = closed_arrival_summary(result, 100.0)
        self.assertEqual(at_100["time"], 100.0)
        self.assertEqual(at_100["arrivals"], 11)
        self.assertEqual(at_100["state_arrival_rate_per_hour"], 3.5)
        self.assertEqual(at_100["observed_arrival_rate_per_hour"], 6.6)
        at_50 = closed_arrival_summary(result, 50.0)
        self.assertEqual(at_50["queue_length"], 0)
        self.assertEqual(at_50["busy_chargers"], 2)
        self.assertEqual(at_50["working_robots"], 8)
        self.assertEqual(at_50["arrivals"], 6)
        self.assertEqual(at_50["alpha_per_hour"], 0.5)
        self.assertEqual(at_50["state_arrival_rate_per_hour"], 4.0)
        self.assertEqual(at_50["observed_arrival_rate_per_hour"], 7.2)
        self.assertEqual(result.summary["time"], 120)
        self.assertEqual(result.summary["arrivals"], 12)
        self.assertEqual(closed_arrival_summary(result, 120.0), closed_arrival_summary(result))

    def test_exact_event_boundaries_and_simultaneous_service_completions(self):
        config = SimulationConfig(
            model="closed", fleet_size=3, chargers=2, charger_times=(4.0, 2.0),
            mean_work_time=1, duration=5, sample_count=2,
        )
        engine = ChargingSimulation(config)
        engine.work_duration = lambda: 1.0
        result = engine.run()
        before_first = closed_arrival_summary(result, nextafter(1.0, 0.0))
        self.assertEqual(before_first["arrivals"], 0)
        at_first = closed_arrival_summary(result, 1.0)
        self.assertEqual(at_first["arrivals"], 3)
        self.assertEqual(at_first["queue_length"], 1)
        before_completion = closed_arrival_summary(result, nextafter(3.0, 0.0))
        self.assertEqual(before_completion["working_robots"], 0)
        at_completion = closed_arrival_summary(result, 3.0)
        self.assertEqual(at_completion["queue_length"], 0)
        self.assertEqual(at_completion["busy_chargers"], 2)
        self.assertEqual(at_completion["working_robots"], 1)
        at_both = closed_arrival_summary(result, 5.0)
        self.assertEqual(at_both["queue_length"], 0)
        self.assertEqual(at_both["busy_chargers"], 1)
        self.assertEqual(at_both["working_robots"], 2)

    def test_selected_time_zero_and_invalid_time_bounds(self):
        result = simulate(SimulationConfig(model="closed", duration=120))
        initial = closed_arrival_summary(result, 0.0)
        self.assertEqual(initial["arrivals"], 0)
        self.assertEqual(initial["queue_length"], 0)
        self.assertEqual(initial["busy_chargers"], 0)
        self.assertEqual(initial["working_robots"], 10)
        self.assertEqual(initial["state_arrival_rate_per_hour"], 5.0)
        self.assertTrue(isnan(initial["observed_arrival_rate_per_hour"]))
        for time in (-1.0, 120.001, float("nan"), float("inf")):
            with self.subTest(time=time), self.assertRaises(ValueError):
                closed_arrival_summary(result, time)

    def test_export_uses_selected_time_and_keeps_full_history(self):
        result = simulate(SimulationConfig(model="closed", seed=41, duration=120))
        with ZipFile(BytesIO(result_archive([result], {}, {"closed": 50.0}))) as archive:
            intensity = pd.read_csv(BytesIO(archive.read("closed/arrival_intensity.csv")))
            self.assertEqual(intensity.iloc[0].to_dict(), closed_arrival_summary(result, 50.0))
            history = pd.read_csv(BytesIO(archive.read("closed/history.csv")))
            self.assertEqual(history.iloc[-1]["time"], 120)
            self.assertEqual(history.iloc[-1]["arrivals"], 12)
