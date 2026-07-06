# ORB Forward-Test (Paper Trading)

Täglicher, automatischer Vorwärts-Test der First-Candle-Strategie
(Opening Range Breakout) auf **frischen Daten** – also auf Handelstagen,
die bei der Entwicklung der Strategie noch nicht existierten.

## Warum dieser Test?

Die Strategie wurde auf 60 Tagen Historie optimiert (Backtests im Ordner
`orb-backtest`). Ergebnis dort: Erwartungswert um null, alle "Verbesserungen"
waren Stichproben-Zufall. Dieser Forward-Test ist die einzige ehrliche
Prüfung: Er kann nicht schummeln, weil die Zukunft niemandem gehört.

## Was genau getestet wird

- **Strategie:** Erste 5-Min-Kerze (15:30 CH) = Range. Entry beim ersten
  5-Min-Close ausserhalb der Range. Stop-Loss in der Range-Mitte (Variante
  SL50) bzw. bei 75 % (Variante SL75). Kein Take-Profit – Exit am Stop oder
  zum Tagesschluss. Max. 1 Trade pro Tag und Aktie.
- **Werte (14):** die 10 grössten US-Aktien (NVDA, MSFT, AAPL, AMZN,
  GOOGL, META, AVGO, TSLA, BRK-B, LLY), die Indizes S&P 500 (SPY) und
  Nasdaq-100 (QQQ) sowie F und SHOP (Kandidaten aus Stichprobe 2 der
  Backtests).
- **Kosten:** 0.01 % Slippage pro Seite, Stop-Exits zusätzlich 0.05 %.
- **Start:** 2026-07-03 (erster Tag nach dem Backtest-Zeitraum).

## Einrichtung (einmalig)

1. Neues GitHub-Repository anlegen (z. B. `orb-forward-test`).
2. Diesen Ordner pushen:
   ```
   git init
   git add .
   git commit -m "ORB Forward-Test"
   git branch -M main
   git remote add origin https://github.com/DEIN-NAME/orb-forward-test.git
   git push -u origin main
   ```
3. Auf GitHub: **Settings → Pages → Source: Deploy from a branch →
   Branch: main, Ordner: /docs** → Save.
4. Fertig. Der Workflow läuft jeden Börsentag um 22:30 UTC automatisch
   (unter **Actions** auch manuell startbar mit "Run workflow").

Das Dashboard liegt dann unter
`https://DEIN-NAME.github.io/orb-forward-test/`.

## Manuell ausführen

```
pip install -r requirements.txt
python forward.py
python dashboard.py
```

## Bewertung (in 2–3 Monaten)

- Beide Varianten um 0 R oder darunter → Strategie endgültig ad acta.
- Eine Variante deutlich positiv (> +10 R über > 40 Trades) → dann, und erst
  dann, lohnt sich weiteres Nachdenken.
- **Bis dahin: kein echtes Geld.**
