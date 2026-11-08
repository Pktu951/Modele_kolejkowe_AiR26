# Symulacja stacji ładowania robotów

Osobny projekt do modeli z `../propozycja1.docx`. Podobnie jak przykład z głównego katalogu korzysta z Pythona, Streamlit i Matplotlib. Silnik jest symulacją zdarzeń dyskretnych: przeskakuje do następnego przyjścia lub zakończenia ładowania, zamiast czekać w czasie rzeczywistym.

## Uruchomienie

Python 3.10 lub nowszy. Wszystkie polecenia wykonuj w tym katalogu:

```sh
cd modele_kolejkowe/robot_charging_simulation
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Jeżeli środowisko `.venv` jest już przygotowane, wystarczą aktywacja i ostatnie polecenie. Aplikacja jest dostępna pod adresem podanym przez Streamlit, zwykle http://localhost:8501. Aby zatrzymać serwer, naciśnij Ctrl+C w terminalu. Na Windows aktywacja to `.venv\Scripts\activate`.

Plik `requirements-lock.txt` zapisuje dokładne wersje użyte do sprawdzenia projektu w Pythonie 3.12. Zamiast instalacji `requirements.txt` można użyć `python -m pip install -r requirements-lock.txt`, aby odtworzyć ten zestaw bibliotek.

## Co można ustawić

W panelu po lewej wybierz model, liczbę ładowarek, czas obserwacji, średni czas ładowania, ziarno losowania i liczbę punktów wykresu. Wartości początkowe są wyłącznie demonstracyjne, a nie pomiarami rzeczywistych robotów.

W modelu otwartym podajesz intensywność napływu λ w zgłoszeniach na godzinę. Zgodnie z ustaleniem symulacja trwa zadany czas; liczba przybyłych robotów jest wynikiem. Każdy robot odwiedza stację raz. Możesz zaznaczyć oba rozkłady i porównać je bezpośrednio na tych samych wykresach.

W modelu zamkniętym podajesz N robotów w stałej flocie oraz średni czas ich pracy. Te same roboty wielokrotnie odwiedzają stację. Wymagane jest c ≤ N. Dostępność oceniamy przez średnią liczbę pracujących robotów E[R] i średni udział dostępnej floty A.

Zakładka **Eksperymenty** przyjmuje listy liczb ładowarek oraz listy N (zamknięty) lub λ (otwarty). Program bada ich kombinacje, wykonuje wskazaną liczbę powtórzeń i pokazuje średnią oraz odchylenie standardowe między przebiegami. Niepoprawne kombinacje zamknięte są jawnie wypisane jako pominięte. Zmiana parametrów ukrywa stare wyniki, aby nie przypisać ich nowym ustawieniom.

## Modele i drugi rozkład napływu

**Poisson, M/M/c/FIFO/∞/O.** Losujemy niezależne wykładnicze odstępy między zgłoszeniami o średniej 1/λ. To daje proces napływu Poissona; nie losujemy odstępów z rozkładu Poissona. Obsługa jest wykładnicza o średniej 1/μ.

**Deterministyczny, D/M/c/FIFO/∞/O.** Drugim rozkładem jest rozkład deterministyczny D: odstęp zawsze wynosi 1/λ. Napływ ma tę samą średnią intensywność co wariant Poissona. Pozostałe parametry nie zmieniają się. Dla danego ziarna oddzielny generator ładowania zapewnia tę samą kolejność losowanych czasów ładowania w obu otwartych wariantach.

**Zamknięty, M/M/c/FIFO/N/F.** Każdy pracujący robot zgłasza potrzebę ładowania po wykładniczym czasie pracy o średniej 1/α. Dla n robotów przy stacji intensywność przyjść to (N−n)α, a ukończeń min(n,c)μ. Roboty w kolejce i przy ładowarkach są niedostępne do pracy. Czas pracy i kolejne czasy ładowania są niezależne.

W obu modelach obowiązuje FIFO oraz c identycznych, niezależnych ładowarek. Każdy robot może czekać; ładowanie nie jest przerywane. Stacja na początku jest pusta, a w zamkniętym modelu wszystkie roboty pracują. Nie modelujemy dojazdów, awarii, bilansu energii, rozładowania baterii w kolejce ani wspólnego limitu mocy.

## Jak czytać wykresy

Wszystkie wykresy biegną od chwili 0 do wybranego końca obserwacji. Średnie i prawdopodobieństwa są narastające, a nie obliczane osobno dla krótkich przedziałów. W silniku jednostką czasu jest minuta; interfejs przelicza godziny i napływ na godzinę na minuty.

Na wykresach liniowych kolor oznacza wariant: niebieski — Poisson, pomarańczowy — deterministyczny, zielony — model zamknięty. Różne miary, stany zajętości lub wartości parametrów w obrębie danego wariantu rozróżniają style linii. Dla pary Q/K kolejka ma linię ciągłą, a system — przerywaną. Wykres czasu przedstawia tylko średni czas oczekiwania w kolejce W. Czas pobytu w systemie T pozostaje w tabelach i danych CSV; nie jest rysowany również na wykresach eksperymentów.

„System” w miarach K i T oznacza samą stację: kolejkę i ładowarki. Także w modelu zamkniętym nie zaliczamy tu robotów pracujących poza stacją. Liczba robotów w całym zamkniętym obiegu zawsze wynosi N.

| Miara | Sposób obliczenia do chwili t |
|---|---|
| Średnia liczba w kolejce Q | Całka z liczby oczekujących po czasie, podzielona przez t |
| Średnia liczba w systemie K | Całka z liczby oczekujących i ładowanych, podzielona przez t |
| Średni czas w kolejce W | Suma pełnych oczekiwań / liczba rozpoczętych ładowań do t |
| Średni czas w systemie T | Suma pełnych czasów od przyjścia do końca ładowania / liczba zakończeń do t |
| P(pusta kolejka) | Czas bez oczekujących / t; roboty mogą się wtedy nadal ładować |
| P(B=k) | Czas z dokładnie k zajętymi ładowarkami / t, dla każdego k od 0 do c |
| Wykorzystanie | Łączny zajęty czas wszystkich ładowarek / (c·t) |
| E[R] | Średnia ważona czasem liczby pracujących robotów; tylko zamknięty |
| Dostępność A | E[R]/N; tylko zamknięty |

Prawdopodobieństwa są udziałami **czasu**, nie odsetkiem zdarzeń. Przy zmiennej długości odstępów liczenie odsetka zdarzeń dawałoby inny wynik. Liczba próbek wykresu zmienia tylko jego gęstość, a nie zdarzenia czy oszacowania końcowe. Dla ponad 10 ładowarek rozkład P(B=k) przedstawia mapa kolorów, aby pokazać wszystkie stany czytelnie.

Symulacja kończy się dokładnie po zadanym czasie i nie opróżnia pozostałej kolejki. W i T używają różnych zbiorów obserwacji: oczekiwanie znamy po rozpoczęciu ładowania, cały czas w systemie po jego zakończeniu. Niezakończone wartości nie są zerami. Gdy nie ma obserwacji, wynik jest nieokreślony (`—` / puste pole CSV). W chwili t=0 średnie czasowe też są nieokreślone. Długie oczekiwania mogą jeszcze nie zostać zaobserwowane, więc krótki przebieg może zaniżać średnie W i T. Liczniki zakończeń i pozostałych zgłoszeń pomagają to ocenić. W i T nie muszą w krótkim przebiegu spełniać dokładnie zależności T=W+1/μ ani wzoru Little'a.

## Wyniki i zachowany moduł teorii

Wykresy, tabele i eksportowane wykresy przedstawiają wyłącznie wyniki symulacji. Aplikacja nie wywołuje obliczeń teoretycznych ani nie pokazuje linii odniesienia lub kolumn z wartościami analitycznymi. Porównanie Poissona z napływem deterministycznym nadal dotyczy dwóch symulowanych przebiegów.

Kod w `theory.py` i jego testy pozostają w projekcie jako niezależny moduł do ewentualnego wykorzystania później. Zawiera on obliczenia Erlanga C dla modelu otwartego oraz rozwiązanie procesu narodzin i śmierci dla modelu zamkniętego. Aby w przyszłości dodać porównanie, można ponownie wywołać `theoretical_metrics(config)` i osobno zaprezentować zwrócone wartości.

Pomiary obejmują cały wybrany czas, w tym rozruch od pustej stacji. Ostrzeżenia o przeciążeniu pozostają pomocniczą informacją o parametrach przebiegu.

## Eksperymenty z terminala

```sh
python run_experiments.py --model both --duration-hours 168 --repetitions 5
python run_experiments.py --model closed --fleet-sizes 8,12,20 --charger-counts 1,2,4
python run_experiments.py --model open --arrival-rates 2,4,8 --charger-counts 1,2,3
```

W `results/open` i/lub `results/closed` powstaną `runs.csv` (każde powtórzenie), `summary.csv` (średnie i odchylenia), `scenarios.json` (pełne parametry) i `experiments.png`. Słupki błędu na wykresach to ± jedno odchylenie standardowe, a nie przedziały ufności. CSV podaje również liczbę powtórzeń z zaobserwowanym wynikiem danej miary. Nie należy traktować brakujących obserwacji jako zer. Limit jednej serii to 600 przebiegów, a limit pojedynczej symulacji to 500 000 zdarzeń; przekroczenie kończy się jawnym błędem.

Przykładowe, już wykonane serie są w `examples/demo_results`. Ich parametry i sposób odtworzenia opisuje `examples/README.md`. Pole `offered_utilization` / „u nominalne” oznacza zadane obciążenie modelu otwartego λ/(cμ). Jeśli jest ≥1, wyniki są miarami skończonego, przeciążonego przebiegu. W takim przypadku nie są oszacowaniem stabilnego stanu ustalonego; ich wartość zależy od czasu obserwacji.

W aplikacji ZIP z pojedynczej symulacji zawiera pełne parametry, historię miar, wizyty robotów, pierwsze 500 zdarzeń i wszystkie wykresy PNG. W ZIP z eksperymentów znajdują się tabele, ustawienia i wykres porównawczy. Nazwy kolumn w plikach danych są angielskie.

## Jak prześledzić kod

1. `models.py` — parametry i struktury pojedynczej wizyty oraz wyniku.
2. `simulation.py` — `run()` tworzy zdarzenia, `handle_arrival()` przydziela stanowisko lub kolejkę, `handle_departure()` kończy obsługę i ewentualnie planuje powrót robota.
3. `metrics.py` — `advance()` dolicza czas starego stanu przed jego zmianą; `snapshot()` odczytuje średnie narastające.
4. `theory.py` — zachowane obliczenia analityczne na później; aplikacja i wykresy obecnie z nich nie korzystają.
5. `experiments.py` — kombinacje parametrów, powtórzenia i podsumowanie.
6. `plots.py` i `exports.py` — rysowanie i eksport wyników.
7. `app.py` — interfejs użytkownika. Zapisanie wyników w `session_state` zapobiega nowemu losowaniu przy pobieraniu danych.

Angielskie nazwy i docstringi stanowią właściwą dokumentację kodu. Wszystkie polskie komentarze pomocnicze mają prefiks `# PL:` i znajdują się na osobnych liniach. Można je wyszukać przez `rg '# PL:'` i usunąć bez zmiany działania. Zdarzenia są rozstrzygane kolejno: koniec ładowania, przyjście, próbka wykresu. W wariancie deterministycznym pierwsze zgłoszenie przychodzi po 1/λ, a w Poissonie po pierwszym wylosowanym odstępie.

## Sprawdzenie poprawności

```sh
python -m unittest discover -s tests -v
```

Testy sprawdzają ręcznie policzony przebieg FIFO, całki po czasie, moment końca obserwacji, brakujące czasy niezakończonych wizyt, zachowanie liczby robotów, powroty tych samych robotów, normalizację prawdopodobieństw, niezależność od próbkowania wykresu, znane rozwiązania analityczne i długookresową zgodność symulacji z teorią. Testy interfejsu wykonują rzeczywisty kod Streamlit przez AppTest.

Źródła wzorów: [V. G. Kulkarni, rozdział 5.2.1](https://vkulkarn.web.unc.edu/wp-content/uploads/sites/17199/2018/07/HealthCareModels.pdf) oraz [J. Sztrik, rozdział 3.4](https://irh.inf.unideb.hu/~jsztrik/publications/books/GlobeEdit_Basic_Queueing_Theory_Sztrik_2016.pdf). Dokumentacja techniczna: [Streamlit AppTest](https://docs.streamlit.io/develop/api-reference/app-testing).
