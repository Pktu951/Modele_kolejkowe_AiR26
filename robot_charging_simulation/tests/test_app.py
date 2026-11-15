"""Exercise the real Streamlit controls, rendering, validation, and downloads."""

from pathlib import Path
import sys
import unittest

from streamlit.testing.v1 import AppTest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))


class AppTests(unittest.TestCase):
    def app(self):
        app = AppTest.from_file(str(PROJECT / "app.py")).run(timeout=60)
        self.assertFalse(app.exception)
        return app

    def assert_simulation_only(self, app, expected_columns):
        columns = list(app.dataframe[0].value.columns)
        self.assertEqual(len(columns), expected_columns)
        self.assertTrue(all(column.startswith("Symulacja · ") for column in columns))
        text = " ".join(element.value.lower() for element in app.markdown)
        for reference in ("teoria", "teoretycz", "analitycz", "stan ustalony", "erlanga"):
            self.assertNotIn(reference, text)
        self.assertEqual(len(app.latex), 0)

    def test_open_comparison_and_result_download(self):
        app = self.app()
        app.button("run_simulation").click().run(timeout=60)
        self.assertFalse(app.exception)
        results = app.session_state["simulation_results"][1]
        self.assertEqual([r.config.arrival_distribution for r in results], ["poisson", "deterministic"])
        self.assertEqual(len(app.dataframe), 3)
        self.assert_simulation_only(app, expected_columns=2)
        self.assertEqual(len(app.get("download_button")), 1)
        arrivals = [r.summary["arrivals"] for r in results]
        app.run(timeout=60)
        self.assertEqual([r.summary["arrivals"] for r in app.session_state["simulation_results"][1]], arrivals)

    def test_closed_model_and_fleet_settings(self):
        app = self.app()
        app.radio("model_choice").set_value("Zamknięty").run(timeout=60)
        app.number_input("fleet_size").set_value(12)
        app.number_input("chargers").set_value(3)
        app.button("run_simulation").click().run(timeout=60)
        self.assertFalse(app.exception)
        result = app.session_state["simulation_results"][1][0]
        self.assertEqual(result.config.model, "closed")
        self.assertEqual(result.config.fleet_size, 12)
        self.assertTrue(0 <= result.summary["availability"] <= 1)
        self.assertNotIn("min_available", [widget.key for widget in app.number_input])
        self.assertNotIn("shortage_probability", result.summary)
        self.assertNotIn("Ryzyko niedoboru P(R < m)", app.dataframe[0].value.index)
        self.assert_simulation_only(app, expected_columns=1)
        self.assertEqual(len(app.get("download_button")), 1)

    def test_individual_closed_service_and_parameter_changes(self):
        app = self.app()
        app.radio("model_choice").set_value("Zamknięty — indywidualna obsługa").run(timeout=60)
        app.number_input("chargers").set_value(3).run(timeout=60)
        self.assertNotIn("mean_charge", [widget.key for widget in app.number_input])
        for index, duration in enumerate((30.0, 10.0, 20.0)):
            app.number_input(f"charger_time_{index}").set_value(duration)
        app.button("run_simulation").click().run(timeout=60)
        self.assertFalse(app.exception)
        result = app.session_state["simulation_results"][1][0]
        self.assertEqual(result.config.charger_times, (30.0, 10.0, 20.0))
        self.assertTrue(0 <= result.summary["availability"] <= 1)
        self.assert_simulation_only(app, expected_columns=1)
        self.assertIn("indywidualna obsługa", app.dataframe[0].value.columns[0])
        self.assertEqual(len(app.get("download_button")), 1)
        for visit in result.visits:
            if visit.departed_at is not None:
                self.assertAlmostEqual(visit.departed_at - visit.started_at, result.config.charger_times[visit.charger_id])
        app.number_input("charger_time_1").set_value(8.0).run(timeout=60)
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe), 0)

    def test_individual_closed_grid_uses_entered_time_prefixes(self):
        app = self.app()
        app.radio("model_choice").set_value("Zamknięty — indywidualna obsługa").run(timeout=60)
        app.text_input("individual_grid_chargers").set_value("1,2,3")
        app.text_input("grid_charger_times").set_value("30,10,20")
        app.text_input("grid_fleets").set_value("2,4")
        app.number_input("repetitions").set_value(2)
        app.button("run_experiments").click().run(timeout=60)
        self.assertFalse(app.exception)
        _, raw, summary, scenarios, skipped = app.session_state["experiment_results"]
        self.assertEqual(len(raw), 10)
        self.assertEqual(len(summary), 5)
        self.assertEqual(len(skipped), 1)
        self.assertEqual(scenarios[-1].charger_times, (30.0, 10.0, 20.0))
        self.assertIn("Stałe czasy ładowarek [min]", app.dataframe[0].value.columns)
        self.assertEqual(len(app.get("download_button")), 1)
        app.text_input("grid_charger_times").set_value("30,12,20")
        app.button("run_experiments").click().run(timeout=60)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["experiment_results"][3][-1].charger_times, (30.0, 12.0, 20.0))

    def test_individual_closed_grid_rejects_missing_charger_times(self):
        app = self.app()
        app.radio("model_choice").set_value("Zamknięty — indywidualna obsługa").run(timeout=60)
        app.text_input("individual_grid_chargers").set_value("1,3")
        app.text_input("grid_charger_times").set_value("10,20")
        app.button("run_experiments").click().run(timeout=60)
        self.assertFalse(app.exception)
        self.assertTrue(any("co najmniej 3" in error.value for error in app.error))

    def test_open_grid_runs_both_distributions(self):
        app = self.app()
        app.text_input("grid_chargers").set_value("1,2")
        app.text_input("grid_rates").set_value("2,4")
        app.number_input("repetitions").set_value(2)
        app.button("run_experiments").click().run(timeout=60)
        self.assertFalse(app.exception)
        _, raw, summary, _, _ = app.session_state["experiment_results"]
        self.assertEqual(len(raw), 16)
        self.assertEqual(len(summary), 8)
        self.assertEqual(len(app.get("download_button")), 1)

    def test_closed_grid_reports_invalid_cases(self):
        app = self.app()
        app.radio("model_choice").set_value("Zamknięty").run(timeout=60)
        app.text_input("grid_chargers").set_value("1,3")
        app.text_input("grid_fleets").set_value("2,4")
        app.number_input("repetitions").set_value(2)
        app.button("run_experiments").click().run(timeout=60)
        self.assertFalse(app.exception)
        stored = app.session_state["experiment_results"]
        self.assertEqual(len(stored[1]), 6)
        self.assertEqual(len(stored[4]), 1)
        self.assertTrue(any("Pominięto" in warning.value for warning in app.warning))

    def test_stale_results_and_empty_distribution_selection(self):
        app = self.app()
        app.button("run_simulation").click().run(timeout=60)
        app.number_input("chargers").set_value(3).run(timeout=60)
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe), 0)
        app.multiselect("distributions").set_value([]).run(timeout=60)
        self.assertFalse(app.exception)
        self.assertTrue(any("Wybierz" in item.value for item in app.info))

    def test_invalid_closed_population_is_visible(self):
        app = self.app()
        app.radio("model_choice").set_value("Zamknięty").run(timeout=60)
        app.number_input("fleet_size").set_value(1).run(timeout=60)
        self.assertFalse(app.exception)
        self.assertEqual(len(app.error), 1)

    def test_unstable_open_model_warns_but_runs(self):
        app = self.app()
        app.number_input("arrival_rate").set_value(12.0)
        app.number_input("duration_hours").set_value(1.0)
        app.multiselect("distributions").set_value(["deterministic"])
        app.button("run_simulation").click().run(timeout=60)
        self.assertFalse(app.exception)
        self.assertTrue(any("u ≥ 1" in item.value for item in app.warning))
        self.assertEqual(len(app.get("download_button")), 1)


if __name__ == "__main__":
    unittest.main()
