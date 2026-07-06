# -*- coding: utf-8 -*-
"""Taeglicher Forward-Test der First-Candle-Strategie (Paper Trading).

Laeuft nach US-Boersenschluss (per GitHub Actions oder manuell):
- holt die 5-Minuten-Daten der letzten Tage
- simuliert die Strategie fuer jeden noch nicht verarbeiteten Handelstag
- haengt die Trades an log/trades.csv an

WICHTIG: Es zaehlen nur Tage ab START (= nach Ende der Backtest-Daten).
Alles davor war Optimierungs-Zeitraum und wuerde das Ergebnis schoenfaerben.
"""

import json
import os
from datetime import time as dtime

import pandas as pd
import strategie as st

# Ein Tag darf erst NACH US-Boersenschluss verarbeitet werden - sonst
# wird eine laufende Session faelschlich als fertig gewertet.
JETZT_NY = pd.Timestamp.now(tz="America/New_York")

START = "2026-07-03"        # erster Tag NACH dem Backtest-Zeitraum
# Aufwaermphase: alle verfuegbaren Tage davor (max. ~60 Handelstage,
# mehr gibt die Gratis-Datenquelle bei 5-Min-Kerzen nicht her) werden
# mitgefuehrt, aber als "warmup" markiert - sie stammen aus dem
# Optimierungszeitraum und zaehlen NICHT als Beweis.
WARMUP_START = "2026-04-01"
# Die 10 groessten US-Aktien + S&P 500 (SPY) + Nasdaq-100 (QQQ)
# + F und SHOP (Kandidaten aus Backtest-Stichprobe 2)
TICKERS = ["NVDA", "MSFT", "AAPL", "AMZN", "GOOGL", "META", "AVGO",
           "TSLA", "BRK-B", "LLY", "SPY", "QQQ", "F", "SHOP"]
# Variante: (Entry-Modus, SL-Faktor, TP in R oder None, Entry-Deadline NY)
# "Video" = Original aus dem YouTube-Video: Retest-Entry, SL 50 %, TP 2R
# "Retest3K" = beste 2-Jahres-Zelle: wie RetestMax, aber Entry nur in den
#              ersten 3 Kerzen nach der Range (Idee des Users)
VARIANTEN = {
    "SL25": ("breakout", 0.25, None, "12:00"),
    "SL50": ("breakout", 0.5, None, "12:00"),
    "SL75": ("breakout", 0.75, None, "12:00"),
    "Video": ("retest", 0.5, 2.0, "12:00"),
    "RetestMax": ("retest", 1.0, 4.0, "12:00"),
    "Retest3K": ("retest", 1.0, 4.0, "09:45"),
}

LOG_CSV = "log/trades.csv"
TAGE_JSON = "log/tage.json"

# Gemeinsame Einstellungen; Entry/SL/TP kommen pro Variante
st.OR_KERZEN = 1
st.STOP_SLIP = 0.0005

os.makedirs("log", exist_ok=True)
if os.path.exists(TAGE_JSON):
    with open(TAGE_JSON, encoding="utf-8") as f:
        verarbeitet = set(json.load(f))
else:
    verarbeitet = set()

neue = []
for ticker in TICKERS:
    st.TICKER = ticker
    try:
        df = st.lade_daten(period="60d")
    except Exception as e:
        print(f"{ticker}: Download-Fehler ({e}) - Ticker uebersprungen")
        continue
    for tag in sorted(set(df.index.date)):
        tag_s = str(tag)
        key = f"{tag_s}|{ticker}"
        if tag_s < WARMUP_START or key in verarbeitet:
            continue
        tdf = df[df.index.date == tag]
        # nur abgeschlossene volle Handelstage werten
        # (letzte Kerze 15:55 New York; Halbtage werden ausgelassen)
        if len(tdf) < 30 or tdf.index[-1].time() < dtime(15, 50):
            continue
        # heutiger Tag: erst ab 16:05 New Yorker Zeit anfassen
        if tag_s == str(JETZT_NY.date()) and JETZT_NY.time() < dtime(16, 5):
            continue
        for vname, (modus, sl_f, tp_r, deadline) in VARIANTEN.items():
            st.ENTRY_MODUS = modus
            st.SL_FAKTOR = sl_f
            st.TP_R = tp_r
            st.LAST_ENTRY = deadline
            trade, grund = st.backtest_tag(tag, tdf)
            if trade:
                trade["ticker"] = ticker
                trade["variante"] = vname
                trade["phase"] = "forward" if tag_s >= START else "warmup"
                neue.append(trade)
                print(f"{tag_s} {ticker} {vname}: {trade['richtung']} "
                      f"-> {trade['exit_art']} {trade['r']:+.2f} R")
            else:
                print(f"{tag_s} {ticker} {vname}: kein Trade ({grund})")
        verarbeitet.add(key)

if neue:
    neu_df = pd.DataFrame(neue)
    if os.path.exists(LOG_CSV):
        alt = pd.read_csv(LOG_CSV)
        neu_df = pd.concat([alt, neu_df], ignore_index=True)
    neu_df.to_csv(LOG_CSV, index=False)
    print(f"\n{len(neue)} neue Eintraege -> {LOG_CSV}")
else:
    print("\nKeine neuen abgeschlossenen Handelstage.")

with open(TAGE_JSON, "w", encoding="utf-8") as f:
    json.dump(sorted(verarbeitet), f, indent=1)
