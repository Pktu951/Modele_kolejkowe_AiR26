"""Prosta symulacja zamkniętego systemu ładowania robotów M/M/c/N."""
import math
import random
from collections import deque

# Zmień te wartości, aby ustawić parametry symulacji.
N = 20                  # liczba robotów
C = 3                   # liczba ładowarek
ALPHA = 0.1             # intensywność zgłoszeń jednego robota
MU = 0.5                # intensywność ładowania jednej ładowarki
CZAS_SYMULACJI = 100_000.0
ROZGRZEWKA = 10_000.0   # początkowy czas pomijany w pomiarach
MIN_ROBOTOW = 10        # wymagane minimum robotów dostępnych do pracy
ZIARNO = 1              # None oznacza losowe wyniki przy każdym uruchomieniu


def symuluj(n, c, alpha, mu, czas, rozgrzewka, minimum, ziarno):
    """Uruchamia jedną replikację; zwraca słownik z wynikami symulacji."""
    if n < 1:
        raise ValueError("Liczba robotów N musi być dodatnia.")
    if not 1 <= c <= n:
        raise ValueError("Liczba ładowarek c musi spełniać 1 <= c <= N.")
    if alpha <= 0 or mu <= 0 or czas <= 0:
        raise ValueError("Alpha, mu i czas symulacji muszą być dodatnie.")
    if not all(math.isfinite(x) for x in (alpha, mu, czas, rozgrzewka)):
        raise ValueError("Parametry symulacji muszą być skończone.")
    if not 0 <= rozgrzewka < czas:
        raise ValueError("Rozgrzewka musi być w zakresie od zera do czasu symulacji.")
    if not 0 <= minimum <= n:
        raise ValueError("Minimalna liczba robotów musi być w zakresie 0..N.")

    rng = random.Random(ziarno)
    teraz = 0.0
    kolejka = deque()
    ladujace = zdarzenia = oczekiwania = zakonczone_ladowania = 0
    suma_oczekiwania = pole_kolejki = zajetosc_ladowarek = 0.0
    dostepne_roboty = czas_niedoboru = 0.0
    czas_pomiaru = czas - rozgrzewka

    while teraz < czas:
        w_systemie = ladujace + len(kolejka)
        naplyw = (n - w_systemie) * alpha
        zakonczenia = min(w_systemie, c) * mu
        intensywnosc = naplyw + zakonczenia
        if intensywnosc == 0:
            break

        nastepne = teraz + rng.expovariate(intensywnosc)
        koniec_przedzialu = min(nastepne, czas)
        zmierzony_czas = max(0.0, koniec_przedzialu - max(teraz, rozgrzewka))
        if zmierzony_czas:
            pracujace = n - w_systemie
            pole_kolejki += len(kolejka) * zmierzony_czas
            zajetosc_ladowarek += ladujace * zmierzony_czas
            dostepne_roboty += pracujace * zmierzony_czas
            if pracujace < minimum:
                czas_niedoboru += zmierzony_czas

        teraz = koniec_przedzialu
        if teraz >= czas:
            break
        if teraz >= rozgrzewka:
            zdarzenia += 1

        if rng.random() < naplyw / intensywnosc:
            # Robot kończy pracę; wolna ładowarka obsługuje go od razu.
            if ladujace < c:
                ladujace += 1
                if teraz >= rozgrzewka:
                    oczekiwania += 1
            else:
                kolejka.append(teraz)
        else:
            # Ładowanie się kończy; następny robot jest obsługiwany FIFO.
            if teraz >= rozgrzewka:
                zakonczone_ladowania += 1
            if kolejka:
                zgloszenie = kolejka.popleft()
                if teraz >= rozgrzewka:
                    suma_oczekiwania += teraz - zgloszenie
                    oczekiwania += 1
            else:
                ladujace -= 1

    return {
        "średni czas oczekiwania": suma_oczekiwania / oczekiwania if oczekiwania else 0.0,
        "średnia długość kolejki": pole_kolejki / czas_pomiaru,
        "wykorzystanie ładowarek": zajetosc_ladowarek / (c * czas_pomiaru),
        "średnia liczba dostępnych robotów": dostepne_roboty / czas_pomiaru,
        "udział dostępnych robotów": dostepne_roboty / (n * czas_pomiaru),
        "prawdopodobieństwo dostępności poniżej minimum": czas_niedoboru / czas_pomiaru,
        "zakończone ładowania": zakonczone_ladowania,
        "liczba zdarzeń": zdarzenia,
    }


def main():
    print(f"Parametry: N={N}, c={C}, alpha={ALPHA}, mu={MU}")
    print(f"Czas symulacji: {CZAS_SYMULACJI}, rozgrzewka: {ROZGRZEWKA}, minimum robotów: {MIN_ROBOTOW}\n")
    print("Wyniki po rozgrzewce:")
    for nazwa, wynik in symuluj(N, C, ALPHA, MU, CZAS_SYMULACJI, ROZGRZEWKA, MIN_ROBOTOW, ZIARNO).items():
        print(f"{nazwa}: {wynik:.6f}")


if __name__ == "__main__":
    main()
