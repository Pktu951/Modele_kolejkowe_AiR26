"""Ensure result charts contain only measurements from simulation histories."""

from dataclasses import replace
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import numpy as np

from models import SimulationConfig
from plots import history_charts
from simulation import simulate


class SimulationOnlyChartTests(unittest.TestCase):
    def check_chart_data(self, results):
        expected_metrics = {
            "mean_counts": ("mean_queue_length", "mean_system_size"),
            "mean_times": ("mean_wait_time",),
            "empty_queue": ("queue_empty_probability",),
            "utilization": ("utilization",),
        }
        if results[0].config.model == "closed":
            expected_metrics["availability"] = ("availability",)
        with patch("theory.theoretical_metrics", side_effect=AssertionError("Theory must stay unused")):
            figures = history_charts(results)
        try:
            for name, metrics in expected_metrics.items():
                lines = figures[name].axes[0].lines
                self.assertEqual(len(lines), len(results) * len(metrics), name)
                for result_index, result in enumerate(results):
                    for metric_index, metric in enumerate(metrics):
                        line = lines[result_index * len(metrics) + metric_index]
                        np.testing.assert_allclose(line.get_xdata(), [r["time"] for r in result.history])
                        np.testing.assert_allclose(line.get_ydata(), [r[metric] for r in result.history], equal_nan=True)
                labels = " ".join(line.get_label().lower() for line in lines)
                self.assertNotIn("teoria", labels)
                self.assertNotIn("stan ustalony", labels)
        finally:
            for figure in figures.values():
                plt.close(figure)

    def test_open_charts_show_both_simulations_without_references(self):
        config = SimulationConfig(duration=600)
        self.check_chart_data([
            simulate(config),
            simulate(replace(config, arrival_distribution="deterministic")),
        ])

    def test_closed_charts_and_availability_have_no_references(self):
        self.check_chart_data([simulate(SimulationConfig(model="closed", duration=600))])

    def test_individual_service_charts_and_availability_have_no_references(self):
        self.check_chart_data([simulate(SimulationConfig(
            model="closed", charger_times=(10.0, 30.0), duration=600,
        ))])


if __name__ == "__main__":
    unittest.main()
