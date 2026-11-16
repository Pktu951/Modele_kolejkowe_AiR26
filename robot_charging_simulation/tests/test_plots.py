"""Ensure result charts contain only measurements from simulation histories."""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import numpy as np

from models import SimulationConfig
from metrics import instantaneous_history
from plots import experiment_chart, history_charts, result_label
from experiments import run_experiments, summarize_experiments
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
            for result in results:
                lines = figures[f"instantaneous_{result.config.variant_key}"].axes[0].lines
                self.assertEqual(len(lines), 2)
                states = instantaneous_history(result)
                for line, metric in zip(lines, ("queue_length", "busy_chargers")):
                    self.assertEqual(line.get_drawstyle(), "steps-post")
                    np.testing.assert_allclose(line.get_xdata(), [row["time"] for row in states])
                    np.testing.assert_array_equal(line.get_ydata(), [row[metric] for row in states])
                self.assertEqual(len({line.get_color() for line in lines}), 2)
                self.assertTrue(all(line.get_linestyle() == "-" for line in lines))
                self.assertEqual([line.get_label() for line in lines], ["Oczekujące", "Ładowane"])
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

    def test_open_charts_show_poisson_simulation_without_references(self):
        config = SimulationConfig(duration=600)
        self.check_chart_data([simulate(config)])

    def test_exponential_charts_and_experiments_label_poisson_model(self):
        config = SimulationConfig(duration=600, service_distribution="exponential")
        results = [simulate(config)]
        self.assertEqual(result_label(results[0]), "Poisson (M/M/c)")
        self.check_chart_data(results)
        frame = summarize_experiments(run_experiments([r.config for r in results], 2))
        figure = experiment_chart(frame)
        try:
            labels = figure.axes[0].get_legend_handles_labels()[1]
            self.assertTrue(any("M/M/c" in text for text in labels))
            self.assertEqual(len(labels), 1)
        finally:
            plt.close(figure)

    def test_closed_charts_and_availability_have_no_references(self):
        self.check_chart_data([simulate(SimulationConfig(model="closed", duration=600))])

    def test_closed_exponential_charts_and_experiments_label_service_choice(self):
        result = simulate(SimulationConfig(model="closed", service_distribution="exponential", duration=600))
        self.assertIn("Zamknięty M/M/c", result_label(result))
        self.check_chart_data([result])
        frame = summarize_experiments(run_experiments([result.config], 2))
        figure = experiment_chart(frame)
        try:
            self.assertIn("M/M/c", figure.axes[0].get_legend_handles_labels()[1][0])
        finally:
            plt.close(figure)

    def test_individual_service_charts_and_availability_have_no_references(self):
        self.check_chart_data([simulate(SimulationConfig(
            model="closed", charger_times=(10.0, 30.0), duration=600,
        ))])


if __name__ == "__main__":
    unittest.main()
