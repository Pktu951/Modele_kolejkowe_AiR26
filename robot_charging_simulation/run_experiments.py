"""Run reproducible grids from the terminal and save CSV, JSON, and PNG files."""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt

from experiments import build_scenarios, parse_charger_times, parse_values, run_experiments, summarize_experiments
from exports import figure_png
from models import SimulationConfig
from plots import experiment_chart


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=["open", "closed", "closed-individual", "both"], default="both")
    parser.add_argument("--charger-counts", default="1,2,3")
    parser.add_argument("--fleet-sizes", default="10,15,20")
    parser.add_argument("--arrival-rates", default="2,4,6", help="Requests per hour.")
    parser.add_argument("--duration-hours", type=float, default=168)
    parser.add_argument(
        "--mean-charge-time", "--charge-time", dest="mean_charge_time", type=float, default=20,
        help="Exact fixed charging duration in minutes for identical chargers in either model.",
    )
    parser.add_argument("--charger-times", help="Fixed times in minutes, in charger order; required for closed-individual.")
    parser.add_argument("--mean-work-time", type=float, default=120, help="Minutes.")
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("results"))
    args = parser.parse_args()
    if args.model == "closed-individual" and args.charger_times is None:
        parser.error("closed-individual requires --charger-times, e.g. 10,30,20.")
    if args.model != "closed-individual" and args.charger_times is not None:
        parser.error("--charger-times is supported only with --model closed-individual.")
    try:
        time_pool = parse_charger_times(args.charger_times) if args.charger_times is not None else None
    except ValueError as error:
        parser.error(str(error))
    models = ["open", "closed"] if args.model == "both" else [args.model]
    for model in models:
        individual_service = model == "closed-individual"
        base = SimulationConfig(
            model="closed" if individual_service else model, duration=args.duration_hours * 60,
            chargers=1 if individual_service else 2,
            charger_times=time_pool[:1] if individual_service else None,
            mean_charge_time=args.mean_charge_time, mean_work_time=args.mean_work_time,
            seed=args.seed,
        )
        scenarios, skipped = build_scenarios(
            base, parse_values(args.charger_counts, integer=True),
            fleet_sizes=parse_values(args.fleet_sizes, integer=True),
            arrival_rates_per_hour=parse_values(args.arrival_rates),
            charger_times=time_pool,
        )
        for case in skipped:
            print("Skipped invalid scenario:", case)
        # PL: Każdy wariant uruchamiamy wiele razy, a nie opieramy się na jednym losowaniu.
        raw = run_experiments(scenarios, args.repetitions)
        summary = summarize_experiments(raw)
        directory = args.output / ("closed_individual" if individual_service else model)
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
