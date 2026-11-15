"""Check exact event-time counts independently of cumulative chart samples."""

from bisect import bisect_right
from dataclasses import replace
from io import BytesIO
from pathlib import Path
import sys
import unittest
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from exports import result_archive
from metrics import instantaneous_history
from models import SimulationConfig
from simulation import ChargingSimulation, simulate


class InstantaneousHistoryTests(unittest.TestCase):
    def test_exact_steps_include_events_between_samples_and_merge_ties(self):
        config = SimulationConfig(
            chargers=1, duration=5, arrival_rate=1,
            arrival_distribution="deterministic", sample_count=2,
        )
        engine = ChargingSimulation(config)
        engine.charge_duration = lambda: 2.0
        result = engine.run()
        states = instantaneous_history(result)
        self.assertEqual(states, [
            {"time": 0, "queue_length": 0, "busy_chargers": 0, "system_size": 0},
            {"time": 1, "queue_length": 0, "busy_chargers": 1, "system_size": 1},
            {"time": 2, "queue_length": 1, "busy_chargers": 1, "system_size": 2},
            {"time": 3, "queue_length": 1, "busy_chargers": 1, "system_size": 2},
            {"time": 4, "queue_length": 2, "busy_chargers": 1, "system_size": 3},
            {"time": 5, "queue_length": 2, "busy_chargers": 1, "system_size": 3},
        ])
        for metric, mean in (("queue_length", "mean_queue_length"), ("system_size", "mean_system_size")):
            area = sum(
                row[metric] * (next_row["time"] - row["time"])
                for row, next_row in zip(states, states[1:])
            )
            self.assertAlmostEqual(area / config.duration, result.summary[mean])

    def test_all_models_match_samples_and_keep_the_same_trace_when_sampling_changes(self):
        for config in (
            SimulationConfig(duration=600, sample_count=2),
            SimulationConfig(duration=600, arrival_distribution="deterministic", sample_count=2),
            SimulationConfig(model="closed", duration=600, sample_count=2),
            SimulationConfig(model="closed", charger_times=(30.0, 10.0), duration=600, sample_count=2),
        ):
            with self.subTest(variant=config.variant_key):
                result = simulate(config)
                dense = simulate(replace(config, sample_count=301))
                states = instantaneous_history(result)
                self.assertEqual(states, instantaneous_history(dense))
                self.assertEqual(states[0]["time"], 0)
                self.assertEqual(states[-1]["time"], config.duration)
                times = [row["time"] for row in states]
                for sample in dense.history:
                    state = states[bisect_right(times, sample["time"]) - 1]
                    for metric in ("queue_length", "busy_chargers", "system_size"):
                        self.assertEqual(state[metric], sample[metric])
                for state in states:
                    self.assertGreaterEqual(state["queue_length"], 0)
                    self.assertTrue(0 <= state["busy_chargers"] <= config.chargers)
                    self.assertEqual(state["system_size"], state["queue_length"] + state["busy_chargers"])
                    if config.model == "closed":
                        self.assertLessEqual(state["system_size"], config.fleet_size)

    def test_empty_station_keeps_both_window_endpoints(self):
        result = simulate(SimulationConfig(duration=0.5, arrival_rate=1, arrival_distribution="deterministic"))
        self.assertEqual(instantaneous_history(result), [
            {"time": 0, "queue_length": 0, "busy_chargers": 0, "system_size": 0},
            {"time": 0.5, "queue_length": 0, "busy_chargers": 0, "system_size": 0},
        ])

    def test_steps_continue_after_the_event_log_limit(self):
        engine = ChargingSimulation(SimulationConfig(
            chargers=1, duration=600, arrival_rate=1,
            arrival_distribution="deterministic", sample_count=2,
        ))
        engine.charge_duration = lambda: 0.5
        result = engine.run()
        self.assertEqual(len(result.event_log), 500)
        states = instantaneous_history(result)
        self.assertGreater(len(states), 500)
        self.assertEqual(states[-2], {"time": 599.5, "queue_length": 0, "busy_chargers": 0, "system_size": 0})
        self.assertEqual(states[-1], {"time": 600, "queue_length": 0, "busy_chargers": 1, "system_size": 1})

    def test_seed_41_at_100_minutes_and_export(self):
        result = simulate(SimulationConfig(model="closed", seed=41, duration=100))
        states = instantaneous_history(result)
        self.assertEqual(states[-1], {"time": 100, "queue_length": 2, "busy_chargers": 2, "system_size": 4})
        with ZipFile(BytesIO(result_archive([result], {}))) as archive:
            frame = pd.read_csv(BytesIO(archive.read("closed/instantaneous_history.csv")))
            pd.testing.assert_frame_equal(frame, pd.DataFrame(states))


if __name__ == "__main__":
    unittest.main()
