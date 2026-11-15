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

W panelu po lewej wybierz model, liczbę ładowarek, czas obserwacji, ziarno losowania i liczbę punktów wykresu. Dla modelu otwartego i standardowego zamkniętego podajesz wspólny średni czas ładowania. Dla nowego wariantu **Zamknięty — indywidualna obsługa** podajesz osobny, stały czas każdej ładowarki w minutach. Wartości początkowe są wyłącznie demonstracyjne, a nie pomiarami rzeczywistych robotów.

W modelu otwartym podajesz intensywność napływu λ w zgłoszeniach na godzinę. Zgodnie z ustaleniem symulacja trwa zadany czas; liczba przybyłych robotów jest wynikiem. Każdy robot odwiedza stację raz. Możesz zaznaczyć oba rozkłady i porównać je bezpośrednio na tych samych wykresach.

W modelu zamkniętym podajesz N robotów w stałej flocie oraz średni czas ich pracy. Te same roboty wielokrotnie odwiedzają stację. Wymagane jest c ≤ N. Dostępność oceniamy przez średnią liczbę pracujących robotów E[R] i średni udział dostępnej floty A.

Przy średnim czasie pracy aplikacja wyświetla przelicznik **α w zgłoszeniach/h na pracującego robota**. Po uruchomieniu obu wariantów zamkniętych nad wykresami pojawia się tabela **„Intensywność zgłoszeń”**. **Chwilę odczytu wybierasz suwakiem lub wpisujesz w polu „Dokładny czas [min]”**, w zakresie od 0 do końca wykonanej symulacji. Oba pola są zsynchronizowane. Domyślnie wybrany jest koniec przebiegu; uruchomienie modelu z innymi parametrami resetuje wybór do nowego końca. Zmiana chwili korzysta z zapisanych wizyt i nie losuje nowego przebiegu ani nie przybliża stanu do najbliższej próbki wykresu.

W tabeli α to stały parametr pojedynczego źródła, λₙ=(N−n)α opisuje stan **w wybranej chwili t**, a λ_obs to liczba zgłoszeń **od 0 do t**, podzielona przez t. Wszystkie trzy wartości są podane na godzinę i mają opis swojego znaczenia. Pod tabelą są liczby **Oczekujące**, **Ładowane** i **Pracujące** w tej samej chwili t. Dla t=0 średnia λ_obs jest nieokreślona i ma oznaczenie „—”. Wykresy i tabela wyników końcowych nadal obejmują pełny przebieg. Rozwijane **„Jak obliczamy te wartości?”** zawiera definicje i wzory. W zwykłym modelu zamkniętym z seedem 41, przy ustawieniach domyślnych i czasie przebiegu co najmniej 100 minut, wybór t=100 pokazuje 0,5/h, 3/h i 6/h oraz stan 2 / 2 / 6.

W wariancie indywidualnym ładowarka o czasie 10 minut zawsze ładuje przez 10 minut, a ładowarka o czasie 30 minut zawsze przez 30 minut. Nie losujemy tych czasów. Czas pracy robotów poza stacją nadal jest losowy, o rozkładzie wykładniczym. Roboty czekają w jednej wspólnej kolejce FIFO. Gdy kilka stanowisk jest wolnych, robot trafia do najszybszego; przy równych czasach wybieramy niższy numer ładowarki.

Zakładka **Eksperymenty** przyjmuje listy liczb ładowarek oraz listy N (zamknięty) lub λ (otwarty). Program bada ich kombinacje, wykonuje wskazaną liczbę powtórzeń i pokazuje średnią oraz odchylenie standardowe między przebiegami. Niepoprawne kombinacje zamknięte są jawnie wypisane jako pominięte. Zmiana parametrów ukrywa stare wyniki, aby nie przypisać ich nowym ustawieniom.

Dla indywidualnej obsługi formularz eksperymentów zawiera dodatkową listę stałych czasów. Wariant z c ładowarkami używa **pierwszych c pozycji**, bez sortowania i usuwania powtórzeń. Przykład `30, 10, 20`: c=1 oznacza ładowarkę 30-minutową, c=2 dodaje 10-minutową, a c=3 dodaje 20-minutową. Jeśli zabraknie czasu dla któregoś stanowiska, program poprosi o uzupełnienie listy. Edycje formularza eksperymentów zatwierdzasz przyciskiem „Uruchom eksperymenty”.

## Modele i drugi rozkład napływu

**Poisson, M/M/c/FIFO/∞/O.** Losujemy niezależne wykładnicze odstępy między zgłoszeniami o średniej 1/λ. To daje proces napływu Poissona; nie losujemy odstępów z rozkładu Poissona. Obsługa jest wykładnicza o średniej 1/μ.

**Deterministyczny, D/M/c/FIFO/∞/O.** Drugim rozkładem jest rozkład deterministyczny D: odstęp zawsze wynosi 1/λ. Napływ ma tę samą średnią intensywność co wariant Poissona. Pozostałe parametry nie zmieniają się. Dla danego ziarna oddzielny generator ładowania zapewnia tę samą kolejność losowanych czasów ładowania w obu otwartych wariantach.

**Zamknięty, M/M/c/FIFO/N/F.** Każdy pracujący robot zgłasza potrzebę ładowania po wykładniczym czasie pracy o średniej 1/α. Dla n robotów przy stacji intensywność przyjść to (N−n)α, a ukończeń min(n,c)μ. Roboty w kolejce i przy ładowarkach są niedostępne do pracy. Czas pracy i kolejne czasy ładowania są niezależne.

**Zamknięty — indywidualna obsługa.** N robotów powtarza cykl pracy i ładowania, ale ładowarka i ma własny stały czas dᵢ. Obsługa nie jest wykładnicza. Lista `charger_times` w konfiguracji przechowuje dokładnie c czasów w kolejności numerów ładowarek. Gdy kilka stanowisk kończy obsługę jednocześnie, silnik najpierw zwalnia wszystkie, a potem przydziela czekające roboty do najszybszych wolnych ładowarek. Nie przerywa ani nie przenosi rozpoczętego ładowania.

We wszystkich wariantach obowiązuje wspólna kolejka FIFO. W otwartym i standardowym zamkniętym ładowarki są jednakowe; wariant indywidualny pozwala na różne stałe czasy obsługi. Każdy robot może czekać; ładowanie nie jest przerywane. Stacja na początku jest pusta, a w zamkniętych wariantach wszystkie roboty pracują. Nie modelujemy dojazdów, awarii, bilansu energii, rozładowania baterii w kolejce ani wspólnego limitu mocy.

## Jak czytać wykresy

Wszystkie wykresy biegną od chwili 0 do wybranego końca obserwacji. Średnie i prawdopodobieństwa są narastające, a nie obliczane osobno dla krótkich przedziałów. W silniku jednostką czasu jest minuta; interfejs przelicza godziny i napływ na godzinę na minuty.

Każdy wariant ma także osobny wykres **„Chwilowa liczba robotów”** z dwiema ciągłymi liniami schodkowymi: oczekujący (niebieska) i ładowani (pomarańczowa). Łączna liczba robotów przy stacji nie jest na nim rysowana. Są to całkowite liczby robotów w danej chwili. W modelu otwartym każdy wybrany napływ ma własny wykres chwilowy. Schodki pokazują stan po zdarzeniach w danym momencie, aż do następnej zmiany. Obejmują wszystkie przyjazdy i zmiany obsługi, również te między próbkami średnich i po pierwszych 500 zdarzeniach. Jednoczesne zdarzenia są łączone w jeden stan, a wykres kończy się dokładnie na zadanym czasie symulacji. Suwak liczby punktów nie zmienia tych schodków.

Przykładowo zwykły model zamknięty z seedem 41, N=10, c=2, średnią pracą 120 min i ładowaniem 20 min po 100 minutach ma 2 roboty oczekujące, 2 ładowane i 4 przy stacji. Wartości chwilowe odróżniają ten stan od średnich liczonych od początku przebiegu.

Na pozostałych wykresach liniowych kolor oznacza wariant: niebieski — Poisson, pomarańczowy — deterministyczny, zielony — model zamknięty. Różne miary, stany zajętości lub wartości parametrów w obrębie danego wariantu rozróżniają style linii. Dla pary Q/K kolejka ma linię ciągłą, a system — przerywaną. Wykres czasu przedstawia tylko średni czas oczekiwania w kolejce W. Czas pobytu w systemie T pozostaje w tabelach i danych CSV; nie jest rysowany również na wykresach eksperymentów.

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

Kod w `theory.py` i jego testy pozostają w projekcie jako niezależny moduł do ewentualnego wykorzystania później. Zawiera on obliczenia Erlanga C dla modelu otwartego oraz rozwiązanie procesu narodzin i śmierci dla standardowego modelu zamkniętego. Dla indywidualnych stałych czasów zwraca `None`, ponieważ dotychczasowy wzór zakłada jednakowe ładowarki i wykładniczą obsługę. Aby w przyszłości dodać porównanie dla obsługiwanych modeli, można ponownie wywołać `theoretical_metrics(config)` i osobno zaprezentować zwrócone wartości.

Pomiary obejmują cały wybrany czas, w tym rozruch od pustej stacji. Ostrzeżenia o przeciążeniu pozostają pomocniczą informacją o parametrach przebiegu.

## Eksperymenty z terminala

```sh
python run_experiments.py --model both --duration-hours 168 --repetitions 5
python run_experiments.py --model closed --fleet-sizes 8,12,20 --charger-counts 1,2,4
python run_experiments.py --model open --arrival-rates 2,4,8 --charger-counts 1,2,3
python run_experiments.py --model closed-individual --charger-times 30,10,20 --charger-counts 1,2,3 --fleet-sizes 8,12,20
```

W `results/open`, `results/closed` lub `results/closed_individual` powstaną `runs.csv` (każde powtórzenie), `summary.csv` (średnie i odchylenia), `scenarios.json` (pełne parametry) i `experiments.png`. Opcja `--model both` zachowuje dwa pierwotne modele; nowy wariant wybierasz przez `--model closed-individual` z wymaganym `--charger-times`. Słupki błędu na wykresach to ± jedno odchylenie standardowe, a nie przedziały ufności. CSV podaje również liczbę powtórzeń z zaobserwowanym wynikiem danej miary. Nie należy traktować brakujących obserwacji jako zer. Limit jednej serii to 600 przebiegów, a limit pojedynczej symulacji to 500 000 zdarzeń; przekroczenie kończy się jawnym błędem.

Przykładowe, już wykonane serie są w `examples/demo_results`. Ich parametry i sposób odtworzenia opisuje `examples/README.md`. Pole `offered_utilization` / „u nominalne” oznacza zadane obciążenie modelu otwartego λ/(cμ). Jeśli jest ≥1, wyniki są miarami skończonego, przeciążonego przebiegu. W takim przypadku nie są oszacowaniem stabilnego stanu ustalonego; ich wartość zależy od czasu obserwacji.

W aplikacji ZIP z pojedynczej symulacji zawiera pełne parametry, historię miar (`history.csv`), dokładne stany chwilowe (`instantaneous_history.csv`), wizyty robotów, pierwsze 500 zdarzeń i wszystkie wykresy PNG, w tym nowe wykresy chwilowe. W `instantaneous_history.csv` kolumny `queue_length`, `busy_chargers` i `system_size` oznaczają odpowiednio oczekujących, ładowanych i razem przy stacji. W ZIP z eksperymentów znajdują się tabele, ustawienia i wykres porównawczy. Nazwy kolumn w plikach danych są angielskie.

Dla obu wariantów zamkniętych ZIP zawiera również `arrival_intensity.csv` z trzema intensywnościami w zgłoszeniach/h, wybraną chwilą odczytu w minutach, liczbą zgłoszeń do tej chwili oraz liczbami robotów oczekujących, ładowanych i pracujących w tym momencie. To te same wartości, które pokazuje panel intensywności. Pozostałe pliki ZIP nadal opisują pełny przebieg. Bez jawnego wyboru czasu eksport używa końca symulacji; model otwarty nie otrzymuje tego zestawienia.

Metadane eksperymentów zawierają `service_type` i `charger_times`, aby odróżnić indywidualną stałą obsługę od wspólnych czasów wykładniczych. Dla indywidualnej obsługi nieużywana wspólna średnia `mean_charge_time` jest pomijana w konfiguracji JSON i pusta w CSV. W `visits.csv` identyfikatory `charger_id` zaczynają się od 0: wartość 0 odpowiada ładowarce nr 1 w aplikacji.

## Jak prześledzić kod

1. `models.py` — parametry i struktury pojedynczej wizyty oraz wyniku.
2. `simulation.py` — `run()` tworzy zdarzenia, `handle_arrival()` przydziela stanowisko lub kolejkę, `handle_departure()` kończy obsługę i ewentualnie planuje powrót robota.
3. `metrics.py` — `advance()` dolicza czas starego stanu przed jego zmianą; `snapshot()` odczytuje średnie narastające; `instantaneous_history()` odtwarza dokładne stany chwilowe z czasów wizyt robotów.
4. `theory.py` — zachowane obliczenia analityczne na później; aplikacja i wykresy obecnie z nich nie korzystają.
5. `experiments.py` — kombinacje parametrów, powtórzenia i podsumowanie.
6. `plots.py` i `exports.py` — rysowanie i eksport wyników.
7. `app.py` — interfejs użytkownika. Zapisanie wyników w `session_state` zapobiega nowemu losowaniu przy pobieraniu danych.

Angielskie nazwy i docstringi stanowią właściwą dokumentację kodu. Wszystkie polskie komentarze pomocnicze mają prefiks `# PL:` i znajdują się na osobnych liniach. Można je wyszukać przez `rg '# PL:'` i usunąć bez zmiany działania. Zdarzenia są rozstrzygane kolejno: koniec ładowania, przyjście, próbka wykresu. W wariancie deterministycznym pierwsze zgłoszenie przychodzi po 1/λ, a w Poissonie po pierwszym wylosowanym odstępie.

## Sprawdzenie poprawności

```sh
python -m unittest discover -s tests -v
```

Testy sprawdzają ręcznie policzony przebieg FIFO, całki po czasie, moment końca obserwacji, brakujące czasy niezakończonych wizyt, zachowanie liczby robotów, powroty tych samych robotów, normalizację prawdopodobieństw, niezależność od próbkowania wykresu, znane rozwiązania analityczne i długookresową zgodność symulacji z teorią. Dla nowego wariantu sprawdzają też stałe czasy poszczególnych ładowarek, wybór najszybszej, jednoczesne zakończenia, prefiksy listy czasów i odtwarzanie z eksportu JSON. Testy interfejsu wykonują rzeczywisty kod Streamlit przez AppTest dla wszystkich trzech wyborów modelu.

Źródła wzorów: [V. G. Kulkarni, rozdział 5.2.1](https://vkulkarn.web.unc.edu/wp-content/uploads/sites/17199/2018/07/HealthCareModels.pdf) oraz [J. Sztrik, rozdział 3.4](https://irh.inf.unideb.hu/~jsztrik/publications/books/GlobeEdit_Basic_Queueing_Theory_Sztrik_2016.pdf). Dokumentacja techniczna: [Streamlit AppTest](https://docs.streamlit.io/develop/api-reference/app-testing).
