"""Stationary benchmarks for M/M/c and the finite-source closed model."""

from math import exp, lgamma, log

from models import SimulationConfig


def _normalize(log_weights: list[float]) -> list[float]:
    """Normalize in log space so large fleets do not overflow factorials."""
    offset = max(log_weights)
    weights = [exp(value - offset) for value in log_weights]
    total = sum(weights)
    return [value / total for value in weights]


def open_theory(config: SimulationConfig) -> dict | None:
    """Erlang C applies only to a stable Poisson/exponential open station."""
    if config.arrival_distribution != "poisson":
        return None
    offered_load = config.arrival_rate * config.mean_charge_time
    utilization = offered_load / config.chargers
    if utilization >= 1:
        return None
    count = config.chargers
    # PL: offered_load to rho = lambda / mu z wykładu.
    # PL: utilization to lambda / (c * mu), czyli rho z propozycja1.docx.
    log_weights = [k * log(offered_load) - lgamma(k + 1) for k in range(count)]
    tail_weight = count * log(offered_load) - lgamma(count + 1) - log(1 - utilization)
    probabilities = _normalize(log_weights + [tail_weight])
    wait_probability = probabilities[-1]
    mean_wait = wait_probability / (count / config.mean_charge_time - config.arrival_rate)
    return {
        "mean_queue_length": config.arrival_rate * mean_wait,
        "mean_system_size": config.arrival_rate * (mean_wait + config.mean_charge_time),
        "mean_wait_time": mean_wait,
        "mean_system_time": mean_wait + config.mean_charge_time,
        # PL: P(Q=0) obejmuje też chwilę, gdy wszystkie ładowarki pracują,
        # PL: lecz żaden dodatkowy robot jeszcze nie czeka.
        "queue_empty_probability": 1 - wait_probability * utilization,
        "utilization": utilization,
        "wait_probability": wait_probability,
        "occupancy_probabilities": probabilities,
    }


def closed_theory(config: SimulationConfig) -> dict:
    """Solve the birth-death chain with N-n working sources and c chargers."""
    log_weights = [0.0]
    for state in range(1, config.fleet_size + 1):
        birth_rate = (config.fleet_size - state + 1) / config.mean_work_time
        death_rate = min(state, config.chargers) / config.mean_charge_time
        # PL: Bilans sąsiednich stanów: p[n] = p[n-1] * lambda[n-1] / mu[n].
        log_weights.append(log_weights[-1] + log(birth_rate) - log(death_rate))
    probabilities = _normalize(log_weights)
    mean_system = sum(n * p for n, p in enumerate(probabilities))
    mean_queue = sum(max(n - config.chargers, 0) * p for n, p in enumerate(probabilities))
    mean_busy = mean_system - mean_queue
    throughput = mean_busy / config.mean_charge_time
    occupancy = [0.0] * (config.chargers + 1)
    for n, probability in enumerate(probabilities):
        occupancy[min(n, config.chargers)] += probability
    return {
        "mean_queue_length": mean_queue,
        "mean_system_size": mean_system,
        # PL: We wzorze Little'a używamy faktycznej przepustowości, a nie N * alpha.
        "mean_wait_time": mean_queue / throughput,
        "mean_system_time": mean_system / throughput,
        "queue_empty_probability": sum(probabilities[:config.chargers + 1]),
        "utilization": mean_busy / config.chargers,
        "mean_available_robots": config.fleet_size - mean_system,
        "availability": (config.fleet_size - mean_system) / config.fleet_size,
        "throughput": throughput,
        "occupancy_probabilities": occupancy,
        "state_probabilities": probabilities,
    }


def theoretical_metrics(config: SimulationConfig) -> dict | None:
    config.validate()
    return closed_theory(config) if config.model == "closed" else open_theory(config)
