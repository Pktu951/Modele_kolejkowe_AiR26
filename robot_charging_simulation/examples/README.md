# Przykładowe eksperymenty

Te wyniki powstały w symulatorze dla parametrów demonstracyjnych. Nie są pomiarami rzeczywistych robotów i nie stanowią rekomendacji liczby ładowarek dla konkretnej instalacji.

Każdy przebieg trwał 168 godzin. Średni czas ładowania wynosił 20 minut. Każdy wariant miał 5 powtórzeń z ziarnami 42–46. Stacja początkowo była pusta, a w modelu zamkniętym wszystkie roboty pracowały.

Model otwarty: λ ∈ {2, 4, 6} zgłoszeń/h, c ∈ {1, 2, 3}, napływ Poissona i deterministyczny. To 18 wariantów i 90 przebiegów. Niektóre kombinacje mają λ/(cμ) ≥1. Ich wykresy pokazują wyniki skończonej obserwacji przeciążenia, a nie stabilny stan ustalony. Duże kolejki tych wariantów mogą dominować wspólną skalę wykresu. Aby dokładniej porównać stabilne przypadki, uruchom własną serię np. λ ∈ {2}, c ∈ {1, 2, 3}.

Model zamknięty: N ∈ {10, 15, 20}, c ∈ {1, 2, 3}, średni czas pracy 120 minut, wymagane minimum m=7 dostępnych robotów. To 9 wariantów i 45 przebiegów. m jest stałą liczbą robotów, a nie procentem floty: przy różnych N dostępność A i ryzyko P(R<m) opisują różne aspekty działania.

W każdym podkatalogu `open` i `closed` znajdują się:

- `runs.csv` — końcowe wyniki wszystkich powtórzeń;
- `summary.csv` — średnie, odchylenia standardowe i liczby obserwowanych powtórzeń;
- `scenarios.json` — konfiguracja każdego wariantu; ziarna kolejnych powtórzeń zwiększają się o 1;
- `experiments.png` — porównanie wyników ze słupkami ± jedno odchylenie standardowe.

Wyniki można odtworzyć z głównego katalogu nowego projektu:

```sh
python run_experiments.py --model both --duration-hours 168 --repetitions 5 --output examples/demo_results
```

Warianty mają tę samą długość obserwacji i te same średnie czasy obsługi. Wynik pojedynczego przebiegu może zależeć od losowania; odchylenie standardowe pokazuje zmienność między powtórzeniami i nie jest przedziałem ufności. W i T opierają się na obserwacjach zakończonych odpowiednio rozpoczęciem i końcem ładowania. Przy przeciążeniu część szczególnie długich wizyt pozostaje niezakończona w końcu obserwacji.
