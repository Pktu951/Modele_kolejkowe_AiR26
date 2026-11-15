SPRAWOZDANIE DO OVERLEAFA

1. W Overleaf wybierz New Project, a następnie Upload Project.
2. Wgraj sprawozdanie_overleaf.zip. Plikiem głównym jest main.tex.
3. Ustaw kompilator XeLaTeX i kodowanie UTF-8. Pakiety są standardowe.
4. Edytuj tekst i tabele w main.tex. Plik można też wkleić w całości do
   pustego projektu i dołączyć katalog figures. Kopie tabel są w tables/*.tex.

Nie trzeba dodawać brakujących ilustracji. Dołączono:
- figures/ui.png: prawdziwy screen naszej lokalnej aplikacji, model otwarty,
  24 godziny, c=2, d=20 minut, lambda=4/h, seed 42;
- figures/closed_experiment.png: wyniki eksperymentów z liczbą robotów
  i ładowarek, pięć powtórzeń dla każdej konfiguracji;
- figures/closed_trace.png: chwilowe liczby oczekujących i ładowanych,
  model zamknięty, N=10, c=2, d=20 minut, seed 41, 100 minut.

Screen skopiowano z examples/open_fixed_service_preview.png, zapisanego
podczas rzeczywistego uruchomienia UI. Nie jest to wygenerowana makieta.
Nie dodano logo uczelni. Dane autorów i data są wpisane na stronie tytułowej.

ODTWORZENIE WYNIKÓW

Pliki data/*_runs.csv zawierają pojedyncze przebiegi, *_summary.csv
średnie i odchylenia między powtórzeniami, a *_scenarios.json parametry.
Każda seria trwa 168 godzin, seedy to 42, 43, 44, 45 i 46.
Osobny snapshot_seed41.json opisuje przykład po 100 minutach.

Z katalogu robot_charging_simulation, przy zainstalowanych zależnościach:

    .venv/bin/python ../sprawozdanie/generate_results.py

Skrypt korzysta z aktualnego silnika projektu. Zapisuje dane, trzy tabele,
dwa wykresy i kopię prawdziwego screena. Uaktualnia oznaczone bloki tabel
w main.tex. Nie zmienia kodu symulacji ani pozostałego tekstu raportu.
Wybrane scenariusze obejmują 30 przebiegów otwartych, 45 zamkniętych
oraz 20 porównujących warianty obsługi. Łącznie: 95 przebiegów.

UWAGI DO INTERPRETACJI

Liczby w raporcie są wynikami demonstracyjnej symulacji.
Wyniki pojedynczego przebiegu na screenie nie są średnimi z pięciu powtórzeń.
Odchylenie standardowe między powtórzeniami nie jest przedziałem ufności.
Kolejki przeciążone dotyczą skończonego horyzontu; nie opisują stanu ustalonego.
Oba modele mają stałe ładowanie, natomiast w zamkniętym czas pracy jest losowy.
