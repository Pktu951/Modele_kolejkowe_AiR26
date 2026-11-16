"""Interactive experiment interface. Run with: streamlit run app.py."""

import json

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from experiments import (
    METRIC_LABELS, SERVICE_DISTRIBUTION_LABELS, SERVICE_LABELS,
    build_scenarios, open_model_label, queue_model_name,
    parse_charger_times, parse_values,
    run_experiments, summarize_experiments,
)
from exports import experiment_archive, result_archive
from metrics import closed_arrival_summary
from models import SimulationConfig
from plots import experiment_chart, history_charts, result_label
from simulation import SimulationLimitError, simulate


def format_number(value: float) -> str:
    """Use a decimal comma and omit insignificant trailing zeros in UI text."""
    if pd.isna(value):
        return "—"
    return f"{value:.6f}".rstrip("0").rstrip(".").replace(".", ",")


def sidebar_controls() -> tuple[SimulationConfig, bool]:
    with st.sidebar:
        st.header("Parametry symulacji")
        model_label = st.radio(
            "Model", ["Otwarty", "Zamknięty", "Zamknięty — indywidualna obsługa"], key="model_choice",
        )
        model = "open" if model_label == "Otwarty" else "closed"
        individual_service = model_label == "Zamknięty — indywidualna obsługa"
        service_distribution = "deterministic"
        if not individual_service:
            service_distribution = st.selectbox(
                "Rozkład czasu ładowania", list(SERVICE_DISTRIBUTION_LABELS),
                format_func=SERVICE_DISTRIBUTION_LABELS.get, key="service_distribution",
            )
        chargers = st.number_input("Liczba ładowarek c", 1, 64, 2, key="chargers")
        duration_hours = st.number_input("Czas symulacji [h]", 0.1, 100_000.0, 24.0, key="duration_hours")
        mean_charge = 20.0
        charger_times = None
        if individual_service:
            with st.expander("Indywidualne czasy ładowania", expanded=True):
                st.caption("Stały czas każdej obsługi. Robot wybiera najszybszą wolną ładowarkę; wspólna kolejka FIFO.")
                charger_times = tuple(
                    st.number_input(
                        f"Czas ładowania — ładowarka {index + 1} [min]",
                        0.01, 100_000.0, 20.0, key=f"charger_time_{index}",
                    )
                    for index in range(chargers)
                )
        else:
            charge_label = "Średni czas ładowania 1/μ [min]" if service_distribution == "exponential" else "Czas ładowania 1/μ [min]"
            mean_charge = st.number_input(charge_label, 0.01, 100_000.0, 20.0, key="mean_charge")
        arrival_rate = 4.0
        fleet_size, mean_work = 10, 120.0
        if model == "open":
            arrival_rate = st.number_input("Intensywność napływu λ [zgłoszenia/h]", 0.001, 100_000.0, 4.0, key="arrival_rate")
            st.caption(f"Napływ: {open_model_label(service_distribution)}.")
            st.caption("Liczba zgłoszeń wynika z λ i czasu. Każdy robot przechodzi przez stację raz.")
        else:
            fleet_size = st.number_input("Liczba robotów N", 1, 5000, 10, key="fleet_size")
            mean_work = st.number_input("Średni czas pracy 1/α [min]", 0.01, 100_000.0, 120.0, key="mean_work")
            st.caption(f"α = {format_number(60.0 / mean_work)} zgłoszeń/h na pracującego robota.")
            if not individual_service:
                st.caption(f"Model {queue_model_name(service_distribution)} ze skończonym źródłem. λₙ = (N−n)α.")
            st.caption("Ta sama flota wielokrotnie pracuje, czeka i ładuje się. Wymagane c ≤ N.")
        seed = st.number_input("Ziarno losowania", 0, 2**31 - 1, 42, key="seed")
        sample_count = st.slider("Liczba punktów na wykresach średnich i prawdopodobieństw", 51, 1001, 301, step=50, key="sample_count")
        submitted = st.button("Uruchom symulację", type="primary", key="run_simulation")
    # PL: Interfejs używa godzin dla czasu eksperymentu i napływu, a silnik minut.
    config = SimulationConfig(
        model=model, chargers=chargers, duration=duration_hours * 60,
        mean_charge_time=mean_charge, arrival_rate=arrival_rate / 60,
        charger_times=charger_times,
        service_distribution=service_distribution,
        fleet_size=fleet_size, mean_work_time=mean_work,
        seed=seed, sample_count=sample_count,
    )
    return config, submitted


def sync_inspection_time(source_key: str, target_key: str) -> None:
    """Synchronize the slider and numeric input before the next app rerun."""
    st.session_state[target_key] = st.session_state[source_key]


def select_inspection_time(result) -> float:
    """Select a point in an existing trajectory without drawing new events."""
    prefix = f"arrival_time_{result.config.variant_key}"
    slider_key, input_key, signature_key = f"{prefix}_slider", f"{prefix}_input", f"{prefix}_signature"
    signature = json.dumps(result.config.to_dict(), sort_keys=True)
    end_time = float(result.summary["time"])
    if (
        st.session_state.get(signature_key) != signature
        or slider_key not in st.session_state or input_key not in st.session_state
    ):
        # PL: Nowe parametry przebiegu resetują oba pola do końca nowej symulacji.
        st.session_state[signature_key] = signature
        st.session_state[slider_key] = end_time
        st.session_state[input_key] = end_time
    slider_column, input_column = st.columns([3, 1])
    with slider_column:
        st.slider(
            "Chwila odczytu [min]", 0.0, end_time, step=min(0.01, end_time),
            key=slider_key, on_change=sync_inspection_time, args=(slider_key, input_key),
        )
    with input_column:
        st.number_input(
            "Dokładny czas [min]", 0.0, end_time, step=min(1.0, end_time), format="%.6f",
            key=input_key, on_change=sync_inspection_time, args=(input_key, slider_key),
        )
    return float(st.session_state[input_key])


def display_closed_arrival_summary(result) -> float:
    """Separate a fixed source parameter from selected-state and observed rates."""
    st.subheader("Intensywność zgłoszeń")
    observation_time = select_inspection_time(result)
    summary = closed_arrival_summary(result, observation_time)
    time_label = format_number(summary["time"])
    st.caption(
        f"Seed: {result.config.seed} · Odczyt: {time_label} min · "
        f"Pełny przebieg: {format_number(result.summary['time'])} min · "
        f"Roboty: {result.config.fleet_size} · Ładowarki: {result.config.chargers}"
    )
    # PL: Wiersze rozróżniają stały parametr, wybraną chwilę i średnią od początku do tej chwili.
    table = pd.DataFrame([
        {
            "Wielkość": "Pojedynczy pracujący robot — α",
            "Wartość [zgłoszenia/h]": summary["alpha_per_hour"],
            "Co oznacza?": f"Stały parametr ze średniego czasu pracy {format_number(result.config.mean_work_time)} min.",
        },
        {
            "Wielkość": f"Cała flota — λₙ w chwili {time_label} min",
            "Wartość [zgłoszenia/h]": summary["state_arrival_rate_per_hour"],
            "Co oznacza?": f"Intensywność dla {summary['working_robots']} pracujących robotów w tej chwili.",
        },
        {
            "Wielkość": f"Zaobserwowany napływ — λ_obs od 0 do {time_label} min",
            "Wartość [zgłoszenia/h]": summary["observed_arrival_rate_per_hour"],
            "Co oznacza?": f"Liczba zgłoszeń do ładowania w tym okresie: {summary['arrivals']}.",
        },
    ])
    # PL: Statyczna tabela pozwala zawinąć objaśnienia bez poziomego przewijania.
    st.table(table.set_index("Wielkość").style.format({"Wartość [zgłoszenia/h]": format_number}, na_rep="—"))
    st.caption(f"Stan floty w chwili {time_label} min")
    for column, label, field in zip(
        st.columns(3),
        ("Oczekujące", "Ładowane", "Pracujące"),
        ("queue_length", "busy_chargers", "working_robots"),
    ):
        column.metric(label, summary[field])
    with st.expander("Jak obliczamy te wartości?", expanded=False):
        st.markdown(
            "**α** jest stałą intensywnością zgłoszeń jednego robota podczas pracy: "
            "`α = 60 / średni czas pracy [min]` w zgłoszeniach/h. "
            "Nie oznacza stałych odstępów: czas pracy nadal losujemy z rozkładu wykładniczego.\n\n"
            "**λₙ** dotyczy stanu w wybranej chwili: `λₙ = (N − n) × α`, "
            "gdzie `n = oczekujące + ładowane`, a `N − n` to liczba pracujących robotów.\n\n"
            "**λ_obs** jest średnią z obserwacji: `λ_obs = liczba zgłoszeń / (czas [min] / 60)`. "
            "Każdy powrót do stacji liczymy jako kolejne zgłoszenie, także gdy robot zaczyna ładowanie od razu. "
            "Okres obejmuje czas od 0 do wybranej chwili, więc wartość może różnić się od λₙ. "
            "Dla czasu 0 λ_obs jest nieokreślona i pokazujemy „—”.\n\n"
            "Zmiana chwili odczytu nie losuje nowego przebiegu. "
            "Średni czas oczekiwania W w tabeli wyników końcowych nadal pochodzi z pełnej symulacji."
        )
    return observation_time


def display_results(results):
    columns = {}
    names = list(METRIC_LABELS) if results[0].config.model == "closed" else list(METRIC_LABELS)[:6]
    for result in results:
        columns[f"Symulacja · {result_label(result)}"] = [result.summary[name] for name in names]
    st.subheader("Wyniki na końcu obserwacji")
    st.dataframe(
        pd.DataFrame(columns, index=[METRIC_LABELS[name] for name in names]).style.format("{:.4f}", na_rep="—"),
        width="stretch",
    )
    for result in results:
        row = result.summary
        st.write(
            f"**{result_label(result)}:** zgłoszenia {row['arrivals']}, rozpoczęte ładowania "
            f"{row['service_starts']}, zakończone {row['completions']}, "
            f"pozostałe przy stacji {row['unfinished_visits']}."
        )
        if not row["completions"]:
            st.info("Nie zakończyło się jeszcze żadne ładowanie. Średni czas w systemie jest nieokreślony (—).")
    inspection_times = {}
    for result in results:
        if result.config.model == "closed":
            inspection_times[result.config.variant_key] = display_closed_arrival_summary(result)
    st.caption(
        "Wykresy chwilowe pokazują liczbę oczekujących (niebieski) i ładowanych (pomarańczowy) w danej chwili. "
        "Schodki zmieniają się w momentach zdarzeń; pozostałe wykresy pokazują miary narastające."
    )
    figures = history_charts(results)
    for figure in figures.values():
        st.pyplot(figure, width="stretch")
    st.download_button(
        "Pobierz wykresy i dane symulacji (ZIP)", result_archive(results, figures, inspection_times),
        file_name="charging_simulation.zip", mime="application/zip", key="download_simulation",
    )
    for figure in figures.values():
        plt.close(figure)
    with st.expander("Sprawdź zdarzenia krok po kroku i parametry uruchomienia"):
        for result in results:
            st.write(result_label(result))
            st.json(result.config.to_dict())
            st.caption("Pierwsze 500 zdarzeń. Czasy są w minutach; identyfikatory robotów zaczynają się od 0.")
            st.dataframe(pd.DataFrame(result.event_log), width="stretch", hide_index=True)


def experiments_tab(config):
    st.subheader("Eksperymenty dla wielu parametrów")
    st.write(
        "Wpisz listy wartości. Program uruchomi wszystkie poprawne kombinacje i powtórzy każdą "
        "z różnymi ziarnami. Wartości dziesiętne zapisuj kropką."
    )
    with st.form("experiment_form"):
        default_counts = (
            ", ".join(str(count) for count in range(1, min(config.chargers, 3) + 1))
            if config.individual_service else "1, 2, 3"
        )
        charger_text = st.text_input(
            "Liczby ładowarek c", default_counts,
            key="individual_grid_chargers" if config.individual_service else "grid_chargers",
        )
        charger_times_text = None
        if config.individual_service:
            charger_times_text = st.text_input(
                "Stałe czasy ładowarek dla eksperymentów [min]",
                ", ".join(f"{value:g}" for value in config.charger_times), key="grid_charger_times",
            )
            st.caption("Wariant z c ładowarkami używa pierwszych c czasów z tej listy, w podanej kolejności. Podaj czas także dla każdej dodatkowej ładowarki.")
        if config.model == "closed":
            size_text = st.text_input("Liczby robotów N", "10, 15, 20", key="grid_fleets")
        else:
            size_text = st.text_input("Intensywności napływu λ [zgłoszenia/h]", "2, 4, 6", key="grid_rates")
            st.caption("Każda kombinacja zostanie zbadana dla napływu Poissona i wybranego rozkładu czasu ładowania.")
        repetitions = st.number_input("Liczba powtórzeń każdego wariantu", 1, 30, 5, key="repetitions")
        if config.individual_service:
            st.caption(f"Czas każdego przebiegu: {config.duration / 60:g} h; stałe czasy ładowania z listy powyżej.")
        elif config.service_distribution == "exponential":
            st.caption(f"Czas każdego przebiegu: {config.duration / 60:g} h; wykładnicze ładowanie o średniej {config.mean_charge_time:g} min.")
        else:
            st.caption(f"Czas każdego przebiegu: {config.duration / 60:g} h; stałe ładowanie: {config.mean_charge_time:g} min.")
        submitted = st.form_submit_button("Uruchom eksperymenty", key="run_experiments")
    signature = json.dumps([config.to_dict(), charger_text, size_text, repetitions, charger_times_text], sort_keys=True)
    if submitted:
        progress = st.progress(0.0, text="Przygotowanie eksperymentów")
        try:
            chargers = parse_values(charger_text, integer=True)
            sizes = parse_values(size_text, integer=config.model == "closed")
            if any(c > 64 for c in chargers):
                raise ValueError("W interfejsie można porównać do 64 ładowarek.")
            if config.model == "closed" and any(n > 5000 for n in sizes):
                raise ValueError("W interfejsie można porównać do 5000 robotów.")
            scenarios, skipped = build_scenarios(
                config, chargers,
                fleet_sizes=sizes if config.model == "closed" else None,
                arrival_rates_per_hour=sizes if config.model == "open" else None,
                charger_times=parse_charger_times(charger_times_text) if config.individual_service else None,
            )
            raw = run_experiments(
                scenarios, repetitions,
                lambda done, total: progress.progress(done / total, text=f"Przebiegi: {done}/{total}"),
            )
            st.session_state["experiment_results"] = (signature, raw, summarize_experiments(raw), scenarios, skipped)
        except SimulationLimitError:
            st.error("Przekroczono limit 500 000 zdarzeń w jednym z przebiegów. Skróć czas, zmniejsz napływ lub zwiększ średni czas pracy robotów.")
        except ValueError as error:
            st.error(str(error))
        finally:
            progress.empty()
    stored = st.session_state.get("experiment_results")
    if stored is None or stored[0] != signature:
        st.info("Uruchom serię, aby zobaczyć porównanie dla aktualnych parametrów.")
        return
    _, raw, summary, scenarios, skipped = stored
    if skipped:
        st.warning("Pominięto niepoprawne kombinacje (c > N): " + "; ".join(skipped))
    display_columns = ["chargers", "fleet_size" if config.model == "closed" else "arrival_rate_per_hour", "distribution", "repetitions"]
    if config.individual_service:
        display_columns += ["service_type", "charger_times"]
    if config.model == "open":
        growing_queue = summary["offered_utilization"].ge(1)
        if growing_queue.any():
            st.warning("Seria zawiera warianty, w których kolejka może narastać. Wyniki dotyczą wybranego czasu obserwacji.")
    metrics = list(METRIC_LABELS) if config.model == "closed" else list(METRIC_LABELS)[:6]
    display = summary[display_columns + metrics].copy()
    if config.individual_service:
        display["service_type"] = display["service_type"].map(SERVICE_LABELS)
    closed_label = "Zamknięty" if config.individual_service else f"Zamknięty {queue_model_name(config.service_distribution)}"
    display["distribution"] = display["distribution"].map(
        lambda d: closed_label if d == "closed" else open_model_label(config.service_distribution)
    )
    st.dataframe(display.rename(columns={
        "chargers": "Ładowarki c", "fleet_size": "Roboty N", "arrival_rate_per_hour": "Napływ λ [/h]",
        "distribution": "Napływ", "repetitions": "Powtórzenia", **METRIC_LABELS,
        "charger_times": "Stałe czasy ładowarek [min]",
        "service_type": "Obsługa",
    }), width="stretch", hide_index=True)
    st.caption("Punkty to średnie z powtórzeń, a słupki błędu pokazują ± jedno odchylenie standardowe.")
    if repetitions == 1:
        st.info("Jedno powtórzenie nie pozwala oszacować zmienności między przebiegami.")
    if raw["completions"].eq(0).any():
        st.warning("Niektóre przebiegi nie miały zakończonych ładowań. T jest tam nieokreślone; CSV podaje liczbę obserwowanych powtórzeń każdej miary.")
    figure = experiment_chart(summary, columns=1)
    st.pyplot(figure, width="stretch")
    st.download_button(
        "Pobierz wyniki eksperymentów (ZIP)", experiment_archive(raw, summary, scenarios, figure),
        file_name="charging_experiments.zip", mime="application/zip", key="download_experiments",
    )
    plt.close(figure)


def model_notes():
    st.subheader("Co jest symulowane")
    st.markdown(
        "**Model otwarty:** napływ Poissona ze stałym ładowaniem daje M/D/c, "
        "a z wykładniczym ładowaniem M/M/c. W pierwszym wpisany czas dotyczy każdej obsługi, "
        "w drugim jest średnią losowanych czasów. Ładowarki są jednakowe, kolejka jest FIFO, "
        "a po obsłudze robot opuszcza stację.\n\n"
        "**Model zamknięty z jednakowymi ładowarkami, M/D/c lub M/M/c ze skończonym źródłem:** "
        "N robotów pracuje i wraca do ładowania. Czas pracy jest wykładniczy o średniej 1/α. "
        "Ładowanie trwa stały czas 1/μ albo jest losowane wykładniczo ze średnią 1/μ. "
        "Łączna intensywność zgłoszeń zależy od stanu: λₙ=(N−n)α. Roboty w kolejce lub przy ładowarkach "
        "są niedostępne do pracy.\n\n"
        "**Model zamknięty — indywidualna obsługa:** każda ładowarka ma własny, stały czas ładowania. "
        "Czas pracy robota nadal jest losowy, wykładniczy. Kolejka jest wspólna i obsługiwana FIFO. "
        "Robot trafia do najszybszej wolnej ładowarki; przy równych czasach wybieramy niższy numer. "
        "Jeżeli kilka ładowarek kończy w tej samej chwili, najpierw wszystkie się zwalniają, "
        "a następnie przydzielamy roboty z kolejki."
    )
    st.markdown(
        "**Dostępność:** n oznacza liczbę robotów czekających lub ładowanych. "
        "R=N−n to liczba pracujących robotów, E[R] jej średnia, "
        "A=E[R]/N to średni udział dostępnej floty.\n\n"
        "**Pomiar:** wykresy chwilowe pokazują dokładną liczbę robotów między zdarzeniami. "
        "Wykresy średnich i prawdopodobieństw pokazują oszacowania narastające od chwili 0, "
        "a średnie długości i prawdopodobieństwa są ważone czasem. "
        "Liczba punktów dotyczy tylko tych miar narastających; nie zmienia przebiegu ani schodków chwilowych. "
        "W chwili 0 średnie czasowe są nieokreślone.\n\n"
        "**Początek i koniec:** stacja jest początkowo pusta; w modelu zamkniętym wszystkie roboty pracują. "
        "Zatrzymujemy się dokładnie po zadanym czasie, pozostawiając niezakończone zgłoszenia. "
        "Czasy dojazdu, awarie, pojemność baterii i ograniczenia wspólnej mocy nie są modelowane."
    )


def main():
    st.set_page_config(page_title="Stacja ładowania robotów", layout="wide")
    st.title("Stacja ładowania robotów")
    st.write("Symulacja modelu otwartego i zamkniętego oraz eksperymenty z liczbą ładowarek i obciążeniem.")
    config, submitted = sidebar_controls()
    try:
        config.validate()
    except ValueError as error:
        if config.model == "closed" and config.chargers > config.fleet_size:
            st.error("Liczba ładowarek c nie może przekraczać liczby robotów N.")
        else:
            st.error(f"Niepoprawne parametry: {error}")
        return
    load = config.arrival_rate * config.mean_charge_time / config.chargers
    if config.model == "open" and load >= 1:
        st.warning("Napływ osiąga lub przekracza wydajność stacji (u ≥ 1). Kolejka może narastać; wyniki dotyczą wybranego czasu obserwacji.")
    signature = json.dumps(config.to_dict(), sort_keys=True)
    simulation_tab, batch_tab, notes_tab = st.tabs(["Symulacja i wykresy", "Eksperymenty", "Opis modeli i miar"])
    with simulation_tab:
        if submitted:
            try:
                with st.spinner("Obliczanie przebiegu zdarzeń..."):
                    # PL: Liczymy wybrany model i zapisujemy jego wyniki.
                    # PL: Samo przełączenie zakładki nie uruchamia nowego losowania.
                    results = [simulate(config)]
                    st.session_state["simulation_results"] = (signature, results)
            except SimulationLimitError:
                st.error("Przekroczono limit 500 000 zdarzeń. Skróć czas, zmniejsz napływ lub zwiększ średni czas pracy robotów.")
        stored = st.session_state.get("simulation_results")
        if stored is not None and stored[0] == signature:
            display_results(stored[1])
        else:
            st.info("Ustaw parametry po lewej i wybierz „Uruchom symulację”. Wykresy dotyczą wyłącznie uruchomienia z tymi parametrami.")
    with batch_tab:
        experiments_tab(config)
    with notes_tab:
        model_notes()


if __name__ == "__main__":
    main()
