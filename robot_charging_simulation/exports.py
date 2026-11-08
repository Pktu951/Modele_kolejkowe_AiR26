"""Downloadable reproducible data, settings, and PNG charts."""

from io import BytesIO
import json
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

from models import SimulationResult


def figure_png(figure) -> bytes:
    buffer = BytesIO()
    figure.savefig(buffer, format="png", dpi=160)
    return buffer.getvalue()


def result_archive(results: list[SimulationResult], figures: dict) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for result in results:
            name = result.config.arrival_distribution if result.config.model == "open" else "closed"
            archive.writestr(f"{name}/config.json", json.dumps(result.config.to_dict(), indent=2))
            archive.writestr(f"{name}/history.csv", pd.DataFrame(result.history).to_csv(index=False))
            archive.writestr(f"{name}/visits.csv", pd.DataFrame([v.to_dict() for v in result.visits]).to_csv(index=False))
            archive.writestr(f"{name}/first_500_events.csv", pd.DataFrame(result.event_log).to_csv(index=False))
        for name, figure in figures.items():
            archive.writestr(f"plots/{name}.png", figure_png(figure))
    return buffer.getvalue()


def experiment_archive(raw: pd.DataFrame, summary: pd.DataFrame, scenarios: list, figure) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("runs.csv", raw.to_csv(index=False))
        archive.writestr("summary.csv", summary.to_csv(index=False))
        archive.writestr("scenarios.json", json.dumps([c.to_dict() for c in scenarios], indent=2))
        archive.writestr("experiments.png", figure_png(figure))
    return buffer.getvalue()
