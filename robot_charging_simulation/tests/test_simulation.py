"""Hand-calculated paths, conservation laws, and stationary cross-checks."""

from dataclasses import replace
from math import isfinite, isnan
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models import SimulationConfig
from simulation import ChargingSimulation, SimulationLimitError, simulate
from theory import theoretical_metrics


class EventSimulationTests(unittest.TestCase):
    def test_fifo_time_integrals_and_horizon_ties(self):
        config = SimulationConfig(
            chargers=1, duration=5.0, arrival_rate=1.0,
            arrival_distribution="deterministic", sample_count=6,
        )
        engine = ChargingSimulation(config)
        engine.charge_duration = lambda: 2.0
        result = engine.run()
        row = result.summary
        # PL: Pola pod schodkami: kolejka 4, system 8, zajęta ładowarka 4.
        expected = {
            "mean_queue_length": 4 / 5, "mean_system_size": 8 / 5,
            "utilization": 4 / 5, "queue_empty_probability": 2 / 5,
            "mean_wait_time": 1.0, "mean_system_time": 2.5,
            "arrivals": 5, "service_starts": 3, "completions": 2,
            "queue_length": 2, "unfinished_visits": 3,
            "prob_busy_0": 1 / 5, "prob_busy_1": 4 / 5,
        }
        for name, value in expected.items():
            with self.subTest(metric=name):
                self.assertAlmostEqual(row[name], value)
        self.assertEqual([v.started_at for v in result.visits], [1.0, 3.0, 5.0, None, None])
        self.assertEqual([v.departed_at for v in result.visits], [3.0, 5.0, None, None, None])

    def test_no_arrivals_does_not_invent_waiting_times(self):
        result = simulate(SimulationConfig(
            duration=0.5, arrival_rate=1, arrival_distribution="deterministic",
        ))
        self.assertEqual(result.summary["arrivals"], 0)
        self.assertEqual(result.summary["mean_queue_length"], 0)
        self.assertEqual(result.summary["prob_busy_0"], 1)
        self.assertEqual(result.summary["queue_empty_probability"], 1)
        self.assertTrue(isnan(result.summary["mean_wait_time"]))
        self.assertTrue(isnan(result.summary["mean_system_time"]))
        self.assertTrue(isnan(result.history[0]["mean_queue_length"]))

    def test_closed_robot_returns_and_fleet_is_conserved(self):
        engine = ChargingSimulation(SimulationConfig(
            model="closed", fleet_size=2, chargers=1,
            duration=5, sample_count=6,
        ))
        engine.work_duration = lambda: 1.0
        engine.charge_duration = lambda: 2.0
        result = engine.run()
        self.assertEqual([(v.robot_id, v.arrived_at) for v in result.visits], [(0, 1), (1, 1), (0, 4)])
        self.assertAlmostEqual(result.summary["mean_queue_length"], 0.6)
        self.assertAlmostEqual(result.summary["mean_system_size"], 1.4)
        self.assertAlmostEqual(result.summary["availability"], 0.3)
        self.assertAlmostEqual(result.summary["mean_available_robots"], 0.6)
        for event in result.event_log:
            self.assertEqual(event["queue_length"] + event["busy_chargers"] + event["working_robots"], 2)

    def test_sample_frequency_does_not_change_results(self):
        base = SimulationConfig(duration=1234.567, seed=17, sample_count=51)
        sparse = simulate(base)
        dense = simulate(replace(base, sample_count=1001))
        self.assertEqual(sparse.visits, dense.visits)
        self.assertEqual(sparse.summary["time"], base.duration)
        self.assertEqual(dense.summary["time"], base.duration)
        for name, value in sparse.summary.items():
            if isfinite(value):
                self.assertAlmostEqual(value, dense.summary[name], places=9, msg=name)

    def test_probability_sum_and_count_conservation(self):
        for model in ("open", "closed"):
            config = SimulationConfig(model=model, duration=5000, seed=31)
            result = simulate(config)
            for row in result.history[1:]:
                self.assertAlmostEqual(sum(row[f"prob_busy_{k}"] for k in range(config.chargers + 1)), 1)
                self.assertEqual(row["arrivals"] - row["completions"], row["system_size"])
                self.assertGreaterEqual(row["queue_empty_probability"], row["prob_busy_0"] - 1e-12)
                self.assertLessEqual(row["queue_empty_probability"], 1 + 1e-12)
                if model == "closed":
                    self.assertLessEqual(row["system_size"], config.fleet_size)
                    self.assertAlmostEqual(row["mean_available_robots"] + row["mean_system_size"], config.fleet_size)

    def test_poisson_gaps_have_expected_mean_and_variation(self):
        engine = ChargingSimulation(SimulationConfig(arrival_rate=0.25))
        gaps = [engine.arrival_interval() for _ in range(20_000)]
        mean = sum(gaps) / len(gaps)
        variance = sum((x - mean) ** 2 for x in gaps) / len(gaps)
        self.assertAlmostEqual(mean, 4.0, delta=0.12)
        self.assertAlmostEqual(variance, 16.0, delta=1.0)

    def test_comparison_preserves_service_draws(self):
        config = SimulationConfig(duration=5000)
        poisson = simulate(config)
        fixed = simulate(replace(config, arrival_distribution="deterministic"))
        compared = 0
        for first, second in zip(poisson.visits, fixed.visits):
            if first.departed_at is not None and second.departed_at is not None:
                self.assertAlmostEqual(
                    first.departed_at - first.started_at,
                    second.departed_at - second.started_at, places=9,
                )
                compared += 1
        self.assertGreater(compared, 100)

    def test_event_limit_is_explicit(self):
        with self.assertRaises(SimulationLimitError):
            simulate(SimulationConfig(max_events=1))

    def test_invalid_configurations(self):
        for changes in (
            {"chargers": 0}, {"duration": float("nan")}, {"mean_charge_time": 0},
            {"arrival_rate": -1}, {"sample_count": 1},
            {"model": "closed", "fleet_size": 1, "chargers": 2},
            {"model": "closed", "fleet_size": 0},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(SimulationConfig(), **changes).validate()


class TheoryTests(unittest.TestCase):
    def test_known_mm1_solution(self):
        result = theoretical_metrics(SimulationConfig(chargers=1, arrival_rate=0.5, mean_charge_time=1))
        for name, expected in {
            "mean_queue_length": 0.5, "mean_system_size": 1,
            "mean_wait_time": 1, "mean_system_time": 2,
            "queue_empty_probability": 0.75, "utilization": 0.5,
        }.items():
            self.assertAlmostEqual(result[name], expected)

    def test_closed_no_queue_binomial_case(self):
        config = SimulationConfig(model="closed", fleet_size=4, chargers=4, mean_work_time=6, mean_charge_time=2)
        result = theoretical_metrics(config)
        self.assertAlmostEqual(result["mean_system_size"], 1)
        self.assertEqual(result["mean_queue_length"], 0)
        self.assertEqual(result["mean_wait_time"], 0)
        self.assertAlmostEqual(result["mean_system_time"], 2)
        self.assertAlmostEqual(result["availability"], 0.75)
        self.assertAlmostEqual(result["mean_available_robots"], 3)

    def test_closed_probability_balance_and_throughput(self):
        config = SimulationConfig(model="closed", fleet_size=50, chargers=3)
        result = theoretical_metrics(config)
        probabilities = result["state_probabilities"]
        self.assertAlmostEqual(sum(probabilities), 1)
        self.assertAlmostEqual(sum(result["occupancy_probabilities"]), 1)
        for state in range(config.fleet_size):
            birth_flow = probabilities[state] * (config.fleet_size - state) / config.mean_work_time
            death_flow = probabilities[state + 1] * min(state + 1, config.chargers) / config.mean_charge_time
            self.assertAlmostEqual(birth_flow, death_flow, places=12)
        self.assertAlmostEqual(result["throughput"], result["mean_available_robots"] / config.mean_work_time)

    def test_unavailable_benchmarks_are_not_fabricated(self):
        self.assertIsNone(theoretical_metrics(SimulationConfig(arrival_distribution="deterministic")))
        self.assertIsNone(theoretical_metrics(SimulationConfig(arrival_rate=1, chargers=1, mean_charge_time=2)))

    def test_long_runs_approach_stationary_values(self):
        for model in ("open", "closed"):
            config = SimulationConfig(model=model, duration=600_000, seed=1234, sample_count=2)
            observed = simulate(config).summary
            expected = theoretical_metrics(config)
            for name in ("mean_queue_length", "mean_system_size", "mean_wait_time", "mean_system_time"):
                with self.subTest(model=model, metric=name):
                    self.assertAlmostEqual(observed[name], expected[name], delta=0.07 * expected[name])
            for name in ("queue_empty_probability", "utilization"):
                self.assertAlmostEqual(observed[name], expected[name], delta=0.025)


if __name__ == "__main__":
    unittest.main()
