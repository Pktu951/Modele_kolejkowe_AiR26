SPRAWOZDANIE DO OVERLEAFA

1. W Overleaf wybierz New Project, a następnie Upload Project.
2. Wgraj sprawozdanie_overleaf.zip. Plikiem głównym jest main.tex.
3. Ustaw kompilator XeLaTeX i kodowanie UTF-8. Pakiety są standardowe.
4. Edytuj tekst i tabele w main.tex. Plik można też wkleić w całości do
   pustego projektu i dołączyć katalog figures. Kopie tabel są w tables/*.tex.
5. Dołączony main.pdf jest podglądem skompilowanego sprawozdania.

Nie trzeba dodawać brakujących ilustracji. Dołączono:
- figures/ui.jpg: aktualny, prawdziwy screen wyników modelu otwartego M/M/c,
  24 godziny, c=2, średnie ładowanie 20 minut, lambda=4/h, seed 42;
- figures/closed_experiment.png: porównanie stałej i wykładniczej obsługi
  dla różnych liczb robotów i ładowarek, po pięć powtórzeń;
- figures/closed_trace.png: chwilowe liczby oczekujących i ładowanych,
  model zamknięty, N=10, c=2, d=20 minut, seed 41, 100 minut.

Screen wykonano w przeglądarce podczas rzeczywistego uruchomienia aktualnej
aplikacji. Nie jest to makieta. Zachowano dostarczone logo uczelni w logo.jpg,
dane autorów i datę na stronie tytułowej.

ODTWORZENIE WYNIKÓW

Pliki data/*_runs.csv zawierają pojedyncze przebiegi, *_summary.csv
średnie i odchylenia między powtórzeniami, a *_scenarios.json parametry.
Każda seria trwa 168 godzin, seedy to 42, 43, 44, 45 i 46.
Osobny snapshot_seed41.json opisuje zamknięty wariant ze stałą obsługą
po 100 minutach.

Z katalogu robot_charging_simulation, przy zainstalowanych zależnościach:

    .venv/bin/python ../sprawozdanie/generate_results.py

Skrypt korzysta z aktualnego silnika projektu. Zapisuje dane, trzy tabele,
dwa wykresy. Nie nadpisuje screena ani logo. Uaktualnia oznaczone bloki tabel
w main.tex. Nie zmienia kodu symulacji ani pozostałego tekstu raportu.
Wybrane scenariusze obejmują 30 przebiegów otwartych, 90 zamkniętych
oraz 20 porównujących stałe czasy ładowarek. Łącznie: 140 przebiegów.
Napływ otwarty jest wyłącznie Poissona. W otwartym i zwykłym zamkniętym
porównujemy stały oraz wykładniczy czas ładowania o tej samej średniej.
Wariant indywidualny zachowuje stałe czasy stanowisk.

UWAGI DO INTERPRETACJI

Liczby w raporcie są wynikami demonstracyjnej symulacji.
Wyniki pojedynczego przebiegu na screenie nie są średnimi z pięciu powtórzeń.
Odchylenie standardowe między powtórzeniami nie jest przedziałem ufności.
Kolejki przeciążone dotyczą skończonego horyzontu; nie opisują stanu ustalonego.
W zamkniętym czas pracy pozostaje losowy i wykładniczy. Łączna intensywność
zgłoszeń zależy od liczby pracujących robotów. Model zachowuje skończoną flotę.
