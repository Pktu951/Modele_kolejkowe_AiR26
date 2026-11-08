"""Run reproducible grids from the terminal and save CSV, JSON, and PNG files."""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt

from experiments import build_scenarios, parse_values, run_experiments, summarize_experiments
from exports import figure_png
from models import SimulationConfig
from plots import experiment_chart


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=["open", "closed", "both"], default="both")
    parser.add_argument("--charger-counts", default="1,2,3")
    parser.add_argument("--fleet-sizes", default="10,15,20")
    parser.add_argument("--arrival-rates", default="2,4,6", help="Requests per hour.")
    parser.add_argument("--duration-hours", type=float, default=168)
    parser.add_argument("--mean-charge-time", type=float, default=20, help="Minutes.")
    parser.add_argument("--mean-work-time", type=float, default=120, help="Minutes.")
    parser.add_argument("--min-available", type=int, default=7)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("results"))
    args = parser.parse_args()
    models = ["open", "closed"] if args.model == "both" else [args.model]
    for model in models:
        base = SimulationConfig(
            model=model, duration=args.duration_hours * 60,
            mean_charge_time=args.mean_charge_time, mean_work_time=args.mean_work_time,
            min_available=args.min_available, seed=args.seed,
        )
        scenarios, skipped = build_scenarios(
            base, parse_values(args.charger_counts, integer=True),
            fleet_sizes=parse_values(args.fleet_sizes, integer=True),
            arrival_rates_per_hour=parse_values(args.arrival_rates),
        )
        for case in skipped:
            print("Skipped invalid scenario:", case)
        # PL: Każdy wariant uruchamiamy wiele razy, a nie opieramy się na jednym losowaniu.
        raw = run_experiments(scenarios, args.repetitions)
        summary = summarize_experiments(raw)
        directory = args.output / model
        directory.mkdir(parents=True, exist_ok=True)
        raw.to_csv(directory / "runs.csv", index=False)
        summary.to_csv(directory / "summary.csv", index=False)
        (directory / "scenarios.json").write_text(
            json.dumps([config.to_dict() for config in scenarios], indent=2), encoding="utf-8"
        )
        figure = experiment_chart(summary)
        (directory / "experiments.png").write_bytes(figure_png(figure))
        plt.close(figure)
        print(f"{model}: {len(scenarios)} scenarios, {len(raw)} runs -> {directory}")


if __name__ == "__main__":
    main()
