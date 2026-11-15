# Przykładowe eksperymenty

Plik `arrival_intensity_preview.png` pokazuje panel intensywności z regulacją chwili odczytu dla zwykłego modelu zamkniętego: seed=41, N=10, c=2, pełny przebieg 120 minut, średnia praca 120 minut i średnie ładowanie 20 minut. Na suwaku i w polu liczbowym wybrano t=100 minut. Tabela rozróżnia α=0,5/h, λₙ=3/h i λ_obs=6/h (10 zgłoszeń do 100. minuty). Poniżej pokazuje stan w tej samej chwili: 2 oczekujące, 2 ładowane i 6 pracujących robotów.

Plik `instantaneous_closed_seed41.png` pokazuje dodatkowo wartości chwilowe zwykłego modelu zamkniętego: N=10, c=2, seed=41, średnia praca 120 minut, średnie ładowanie 20 minut, obserwacja 100 minut. W ostatnim punkcie 2 roboty czekają (niebieska linia ciągła) i 2 się ładują (pomarańczowa linia ciągła). Wykres zawiera dokładne momenty zmian, a nie średnie narastające; nie rysuje łącznej liczby robotów przy stacji.

Te wyniki powstały w symulatorze dla parametrów demonstracyjnych. Nie są pomiarami rzeczywistych robotów i nie stanowią rekomendacji liczby ładowarek dla konkretnej instalacji.

Każdy przebieg trwał 168 godzin. Dwa pierwotne modele miały wykładnicze czasy ładowania o średniej 20 minut; nowy wariant indywidualny ma stałe czasy opisane poniżej. Każdy wariant miał 5 powtórzeń z ziarnami 42–46. Stacja początkowo była pusta, a w modelach zamkniętych wszystkie roboty pracowały.

Model otwarty: λ ∈ {2, 4, 6} zgłoszeń/h, c ∈ {1, 2, 3}, napływ Poissona i deterministyczny. To 18 wariantów i 90 przebiegów. Niektóre kombinacje mają λ/(cμ) ≥1. Ich wykresy pokazują wyniki skończonej obserwacji przeciążenia, a nie stabilny stan ustalony. Duże kolejki tych wariantów mogą dominować wspólną skalę wykresu. Aby dokładniej porównać stabilne przypadki, uruchom własną serię np. λ ∈ {2}, c ∈ {1, 2, 3}.

Model zamknięty: N ∈ {10, 15, 20}, c ∈ {1, 2, 3}, średni czas pracy 120 minut. To 9 wariantów i 45 przebiegów. Dostępność floty opisują średnia liczba pracujących robotów E[R] oraz ich udział A=E[R]/N.

Model zamknięty z indywidualną obsługą: te same N, c i średni czas pracy, ale lista stałych czasów ładowarek wynosi `30, 10, 20` minut. Wariant c=1 używa pierwszej ładowarki (30 minut), c=2 pierwszych dwóch (30 i 10 minut), a c=3 wszystkich trzech. Wspólna kolejka jest FIFO; przy kilku wolnych stanowiskach robot trafia do najszybszego. To kolejne 9 wariantów i 45 przebiegów, zapisane w `demo_results/closed_individual`.

W każdym podkatalogu `open`, `closed` i `closed_individual` znajdują się:

- `runs.csv` — końcowe wyniki wszystkich powtórzeń;
- `summary.csv` — średnie, odchylenia standardowe i liczby obserwowanych powtórzeń;
- `scenarios.json` — konfiguracja każdego wariantu; ziarna kolejnych powtórzeń zwiększają się o 1;
- `experiments.png` — porównanie wyników ze słupkami ± jedno odchylenie standardowe.

Wyniki można odtworzyć z głównego katalogu nowego projektu:

```sh
python run_experiments.py --model both --duration-hours 168 --repetitions 5 --output examples/demo_results
python run_experiments.py --model closed-individual --charger-times 30,10,20 --duration-hours 168 --repetitions 5 --output examples/demo_results
```

Warianty mają tę samą długość obserwacji; rozkład i parametry obsługi zależą od wybranego modelu. Wynik pojedynczego przebiegu może zależeć od losowania pracy robotów lub napływu i ładowania; odchylenie standardowe pokazuje zmienność między powtórzeniami i nie jest przedziałem ufności. W i T opierają się na obserwacjach zakończonych odpowiednio rozpoczęciem i końcem ładowania. Przy przeciążeniu część szczególnie długich wizyt pozostaje niezakończona w końcu obserwacji.
