"""Prosta symulacja zamkniętego systemu ładowania robotów M/M/c/N."""
import math
import random
from collections import deque

# Zmień te wartości, aby ustawić parametry symulacji.
N = 20                  # liczba robotów
C = 3                   # liczba ładowarek
ALPHA = 0.1             # intensywność zgłoszeń jednego robota
MU = 0.5                # intensywność ładowania jednej ładowarki
SIMULATION_TIME = 100_000.0
WARMUP = 10_000.0   # początkowy czas pomijany w pomiarach
MIN_ROBOTS = 10        # wymagane minimum robotów dostępnych do pracy
SEED = 1              # None oznacza losowe wyniki przy każdym uruchomieniu


def simulate(robot_count, charger_count, work_rate, charge_rate, duration, warmup, min_available, seed):
    """Uruchamia jedną replikację; zwraca słownik z wynikami symulacji."""
    if robot_count < 1:
        raise ValueError("Liczba robotów N musi być dodatnia.")
    if not 1 <= charger_count <= robot_count:
        raise ValueError("Liczba ładowarek c musi spełniać 1 <= c <= N.")
    if work_rate <= 0 or charge_rate <= 0 or duration <= 0:
        raise ValueError("Alpha, mu i czas symulacji muszą być dodatnie.")
    if not all(math.isfinite(x) for x in (work_rate, charge_rate, duration, warmup)):
        raise ValueError("Parametry symulacji muszą być skończone.")
    if not 0 <= warmup < duration:
        raise ValueError("Rozgrzewka musi być w zakresie od zera do czasu symulacji.")
    if not 0 <= min_available <= robot_count:
        raise ValueError("Minimalna liczba robotów musi być w zakresie 0..N.")

    random_generator = random.Random(seed)
    current_time = 0.0
    queue = deque()
    charging = events = wait_samples = completed_charges = 0
    total_wait = queue_area = charger_busy_area = 0.0
    available_robot_area = shortage_time = 0.0
    measurement_time = duration - warmup

    while current_time < duration:
        in_system = charging + len(queue)
        arrival_rate = (robot_count - in_system) * work_rate
        completion_rate = min(in_system, charger_count) * charge_rate
        total_rate = arrival_rate + completion_rate
        if total_rate == 0:
            break

        next_event_time = current_time + random_generator.expovariate(total_rate)
        interval_end = min(next_event_time, duration)
        measured_interval = max(0.0, interval_end - max(current_time, warmup))
        if measured_interval:
            working_robots = robot_count - in_system
            queue_area += len(queue) * measured_interval
            charger_busy_area += charging * measured_interval
            available_robot_area += working_robots * measured_interval
            if working_robots < min_available:
                shortage_time += measured_interval

        current_time = interval_end
        if current_time >= duration:
            break
        if current_time >= warmup:
            events += 1

        if random_generator.random() < arrival_rate / total_rate:
            # Robot kończy pracę; wolna ładowarka obsługuje go od razu.
            if charging < charger_count:
                charging += 1
                if current_time >= warmup:
                    wait_samples += 1
            else:
                queue.append(current_time)
        else:
            # Ładowanie się kończy; następny robot jest obsługiwany FIFO.
            if current_time >= warmup:
                completed_charges += 1
            if queue:
                arrival_time = queue.popleft()
                if current_time >= warmup:
                    total_wait += current_time - arrival_time
                    wait_samples += 1
            else:
                charging -= 1

    return {
        "średni czas oczekiwania": total_wait / wait_samples if wait_samples else 0.0,
        "średnia długość kolejki": queue_area / measurement_time,
        "wykorzystanie ładowarek": charger_busy_area / (charger_count * measurement_time),
        "średnia liczba dostępnych robotów": available_robot_area / measurement_time,
        "udział dostępnych robotów": available_robot_area / (robot_count * measurement_time),
        "prawdopodobieństwo dostępności poniżej minimum": shortage_time / measurement_time,
        "zakończone ładowania": completed_charges,
        "liczba zdarzeń": events,
    }


def main():
    print(f"Parametry: N={N}, c={C}, alpha={ALPHA}, mu={MU}")
    print(f"Czas symulacji: {SIMULATION_TIME}, rozgrzewka: {WARMUP}, minimum robotów: {MIN_ROBOTS}\n")
    print("Wyniki po rozgrzewce:")
    for name, value in simulate(N, C, ALPHA, MU, SIMULATION_TIME, WARMUP, MIN_ROBOTS, SEED).items():
        print(f"{name}: {value:.6f}")


if __name__ == "__main__":
    main()
