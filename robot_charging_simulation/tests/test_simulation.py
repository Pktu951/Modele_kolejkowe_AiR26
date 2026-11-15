"""Hand-calculated paths, conservation laws, and stationary cross-checks."""

from dataclasses import replace
from math import isfinite, isnan
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models import SimulationConfig
from simulation import ChargingSimulation, SimulationLimitError, simulate
from theory import closed_theory, open_theory, theoretical_metrics


class EventSimulationTests(unittest.TestCase):
    def test_fifo_time_integrals_and_horizon_ties(self):
        config = SimulationConfig(
            chargers=1, duration=5.0, arrival_rate=1.0, mean_charge_time=2.0,
            arrival_distribution="deterministic", sample_count=6,
        )
        engine = ChargingSimulation(config)
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

    def test_closed_charging_is_fixed_while_work_remains_random(self):
        config = SimulationConfig(model="closed", mean_charge_time=17.5, duration=4000)
        engine = ChargingSimulation(config)
        with patch.object(engine.charge_rng, "expovariate", side_effect=AssertionError("Closed charging must not draw a random time")):
            result = engine.run()
        completed = [visit for visit in result.visits if visit.departed_at is not None]
        self.assertGreater(len(completed), 100)
        for visit in completed:
            self.assertAlmostEqual(visit.departed_at - visit.started_at, 17.5)
        first_arrivals = [next(v.arrived_at for v in result.visits if v.robot_id == robot) for robot in range(config.fleet_size)]
        self.assertGreater(len(set(first_arrivals)), 1)
        self.assertEqual(config.service_type, "shared_deterministic")

    def test_equal_charger_times_match_both_closed_variants(self):
        for simultaneous in (False, True):
            with self.subTest(simultaneous=simultaneous):
                config = SimulationConfig(model="closed", chargers=3, mean_charge_time=2, duration=2000)
                shared = ChargingSimulation(config)
                individual = ChargingSimulation(replace(config, charger_times=(2.0,) * 3))
                if simultaneous:
                    # PL: Jednoczesne zakończenia muszą jednakowo rozstrzygać remisy.
                    shared.work_duration = lambda: 1.0
                    individual.work_duration = lambda: 1.0
                first, second = shared.run(), individual.run()
                self.assertEqual(first.visits, second.visits)
                self.assertEqual(first.event_log, second.event_log)
                for left, right in zip(first.history, second.history):
                    for name, value in left.items():
                        if isfinite(value):
                            self.assertEqual(value, right[name], name)
                        else:
                            self.assertTrue(isnan(right[name]), name)

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

    def test_open_service_is_fixed_for_both_arrival_distributions(self):
        for distribution in ("poisson", "deterministic"):
            with self.subTest(distribution=distribution):
                config = SimulationConfig(duration=5000, mean_charge_time=17.5, arrival_distribution=distribution)
                engine = ChargingSimulation(config)
                with patch.object(engine.charge_rng, "expovariate", side_effect=AssertionError("Open charging must not draw a random time")):
                    result = engine.run()
                completed = [visit for visit in result.visits if visit.departed_at is not None]
                self.assertGreater(len(completed), 100)
                for visit in completed:
                    self.assertAlmostEqual(visit.departed_at - visit.started_at, 17.5)
                slower = simulate(replace(config, mean_charge_time=40.0))
                self.assertEqual([v.arrived_at for v in result.visits], [v.arrived_at for v in slower.visits])
                self.assertEqual(config.service_type, "shared_deterministic")

    def test_ddc_at_capacity_from_empty_has_no_waiting(self):
        result = simulate(SimulationConfig(
            chargers=2, duration=10, arrival_rate=1,
            arrival_distribution="deterministic", mean_charge_time=2,
        ))
        self.assertEqual(result.summary["arrivals"], 10)
        self.assertEqual(result.summary["completions"], 8)
        self.assertEqual(result.summary["mean_queue_length"], 0)
        self.assertEqual(result.summary["mean_wait_time"], 0)
        self.assertEqual(result.summary["queue_empty_probability"], 1)
        self.assertAlmostEqual(result.summary["utilization"], 17 / 20)

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

    def test_individual_service_fixed_times_fifo_and_simultaneous_completions(self):
        config = SimulationConfig(
            model="closed", fleet_size=3, chargers=2,
            charger_times=(4.0, 2.0), duration=5, sample_count=6,
        )
        engine = ChargingSimulation(config)
        engine.work_duration = lambda: 1.0
        with patch.object(engine, "charge_duration", side_effect=AssertionError("Fixed service must not draw a random time")):
            result = engine.run()
        # PL: W t=5 obie ładowarki się zwalniają. Czekający robot dostaje szybszą nr 2,
        # PL: choć zdarzenie wolniejszej nr 1 było zapisane w kalendarzu wcześniej.
        self.assertEqual([visit.charger_id for visit in result.visits], [1, 0, 1, 1])
        self.assertEqual([visit.started_at for visit in result.visits], [1.0, 1.0, 3.0, 5.0])
        self.assertEqual([visit.departed_at for visit in result.visits], [3.0, 5.0, 5.0, None])
        for name, expected in {
            "mean_queue_length": 3 / 5, "mean_system_size": 11 / 5,
            "mean_wait_time": 3 / 4, "mean_system_time": 10 / 3,
            "utilization": 4 / 5, "queue_empty_probability": 2 / 5,
            "mean_available_robots": 4 / 5,
        }.items():
            self.assertAlmostEqual(result.summary[name], expected, msg=name)
        for event in result.event_log:
            self.assertEqual(event["working_robots"] + event["queue_length"] + event["busy_chargers"], 3)

    def test_individual_service_reproducibility_and_equal_time_ties(self):
        config = SimulationConfig(
            model="closed", chargers=3, charger_times=(10.0, 10.0, 30.0),
            fleet_size=8, duration=4000, sample_count=51,
        )
        engine = ChargingSimulation(config)
        self.assertEqual(engine.select_free_charger(), 0)
        first = engine.run()
        second = simulate(replace(config, sample_count=201))
        self.assertEqual(first.visits, second.visits)
        for name, value in first.summary.items():
            if isfinite(value):
                self.assertAlmostEqual(value, second.summary[name], places=9, msg=name)
        started = [visit for visit in first.visits if visit.started_at is not None]
        self.assertEqual([visit.visit_id for visit in started], list(range(len(started))))
        self.assertEqual([visit.started_at for visit in started], sorted(visit.started_at for visit in started))
        for visit in first.visits:
            if visit.departed_at is not None:
                self.assertAlmostEqual(visit.departed_at - visit.started_at, config.charger_times[visit.charger_id])
        for row in first.history[1:]:
            self.assertAlmostEqual(row["mean_system_size"] + row["mean_available_robots"], config.fleet_size)
            self.assertAlmostEqual(sum(row[f"prob_busy_{k}"] for k in range(4)), 1)

    def test_individual_service_validation_and_json_parameters(self):
        config = SimulationConfig(model="closed", charger_times=[10.0, 20.0])
        config.validate()
        self.assertEqual(config.charger_times, (10.0, 20.0))
        self.assertNotIn("mean_charge_time", config.to_dict())
        for changes in (
            {"model": "open"}, {"charger_times": ()}, {"charger_times": (10.0,)},
            {"charger_times": (0.0, 20.0)}, {"charger_times": (-1.0, 20.0)},
            {"charger_times": (float("inf"), 20.0)}, {"charger_times": (float("nan"), 20.0)},
            {"charger_times": (True, 20.0)},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(config, **changes).validate()


class TheoryTests(unittest.TestCase):
    def test_legacy_exponential_open_known_mm1_solution(self):
        result = open_theory(SimulationConfig(chargers=1, arrival_rate=0.5, mean_charge_time=1))
        for name, expected in {
            "mean_queue_length": 0.5, "mean_system_size": 1,
            "mean_wait_time": 1, "mean_system_time": 2,
            "queue_empty_probability": 0.75, "utilization": 0.5,
        }.items():
            self.assertAlmostEqual(result[name], expected)

    def test_legacy_exponential_closed_no_queue_binomial_case(self):
        config = SimulationConfig(model="closed", fleet_size=4, chargers=4, mean_work_time=6, mean_charge_time=2)
        result = closed_theory(config)
        self.assertAlmostEqual(result["mean_system_size"], 1)
        self.assertEqual(result["mean_queue_length"], 0)
        self.assertEqual(result["mean_wait_time"], 0)
        self.assertAlmostEqual(result["mean_system_time"], 2)
        self.assertAlmostEqual(result["availability"], 0.75)
        self.assertAlmostEqual(result["mean_available_robots"], 3)

    def test_legacy_exponential_closed_probability_balance_and_throughput(self):
        config = SimulationConfig(model="closed", fleet_size=50, chargers=3)
        result = closed_theory(config)
        probabilities = result["state_probabilities"]
        self.assertAlmostEqual(sum(probabilities), 1)
        self.assertAlmostEqual(sum(result["occupancy_probabilities"]), 1)
        for state in range(config.fleet_size):
            birth_flow = probabilities[state] * (config.fleet_size - state) / config.mean_work_time
            death_flow = probabilities[state + 1] * min(state + 1, config.chargers) / config.mean_charge_time
            self.assertAlmostEqual(birth_flow, death_flow, places=12)
        self.assertAlmostEqual(result["throughput"], result["mean_available_robots"] / config.mean_work_time)

    def test_unavailable_benchmarks_are_not_fabricated(self):
        self.assertIsNone(theoretical_metrics(SimulationConfig()))
        self.assertIsNone(theoretical_metrics(SimulationConfig(arrival_distribution="deterministic")))
        self.assertIsNone(theoretical_metrics(SimulationConfig(arrival_rate=1, chargers=1, mean_charge_time=2)))
        self.assertIsNone(theoretical_metrics(SimulationConfig(model="closed")))
        self.assertIsNone(theoretical_metrics(SimulationConfig(model="closed", charger_times=(10.0, 30.0))))

    def test_md1_long_run_matches_pollaczek_khinchine_means(self):
        config = SimulationConfig(
            chargers=1, arrival_rate=0.5, mean_charge_time=1,
            duration=200_000, seed=1234, sample_count=2,
        )
        observed = simulate(config).summary
        # PL: Niezależny wzór tylko dla jednej ładowarki: W = lambda*d^2 / (2*(1-rho)).
        # Source: https://www.netlab.tkk.fi/opetus/s383143/kalvot/E_mg1jono.pdf, p. 6.
        expected = {
            "mean_queue_length": 0.25, "mean_system_size": 0.75,
            "mean_wait_time": 0.5, "mean_system_time": 1.5,
        }
        for name in ("mean_queue_length", "mean_system_size", "mean_wait_time", "mean_system_time"):
            with self.subTest(metric=name):
                self.assertAlmostEqual(observed[name], expected[name], delta=0.07 * expected[name])
        self.assertAlmostEqual(observed["utilization"], 0.5, delta=0.025)


if __name__ == "__main__":
    unittest.main()
