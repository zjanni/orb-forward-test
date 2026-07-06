# -*- coding: utf-8 -*-
"""First-Candle-Strategie (ORB) - Strategie-Logik fuer den Forward-Test.

Endfassung aus der Backtest-Analyse (Juli 2026):
- Opening Range = erste 5-Minuten-Kerze (09:30-09:35 New York)
- Entry: direkt beim ersten 5-Minuten-CLOSE ausserhalb der Range
- SL: einstellbarer Punkt in der Range (SL_FAKTOR, 0.5 = Mitte)
- Kein Take-Profit: Exit nur per SL oder zum Tagesschluss
- Kein Entry nach LAST_ENTRY (New Yorker Zeit), max. 1 Trade pro Tag
- Kosten: 0.01 % Slippage pro Seite, Stop-Exits zusaetzlich 0.05 %
"""

import pandas as pd
import yfinance as yf

# ---------------- Parameter (werden von forward.py gesetzt) ----------------
TICKER = "TSLA"
SL_FAKTOR = 0.5
TP_R = None                 # None = kein TP, Trade laeuft bis SL/Tagesschluss
ENTRY_MODUS = "breakout"    # "breakout" = Entry beim Close ausserhalb der Range
OR_KERZEN = 1               # Anzahl 5-Min-Kerzen fuer die Opening Range
LAST_ENTRY = "12:00"        # danach kein neuer Entry (New Yorker Zeit)
RETEST_TOL = 0.0005
SLIPPAGE = 0.0001           # 0.01 % pro Seite
STOP_SLIP = 0.0005          # 0.05 % zusaetzlich bei Stop-Loss-Exits
ENTRY_AM_CLOSE = False      # True: Retest-Entry erst zum SCHLUSSKURS der
                            # Ausloese-Kerze (noetig fuer Kerzen-Filter,
                            # sonst Blick in die Zukunft)
PERIOD = "60d"
INTERVAL = "5m"


def lade_daten(period=None):
    df = yf.download(TICKER, period=period or PERIOD, interval=INTERVAL,
                     auto_adjust=False, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.tz_convert("America/New_York")
    return df.between_time("09:30", "15:59")


def backtest_tag(tag, df):
    """Wendet die Regeln auf einen Handelstag an.
    Gibt (trade_dict oder None, grund_kein_trade oder None) zurueck."""
    df = df.copy()
    if len(df) < 10:
        return None, "zu wenig Daten"

    erste = df.iloc[:OR_KERZEN]
    or_high = float(erste["High"].max())
    or_low = float(erste["Low"].min())
    or_range = or_high - or_low
    sl = None
    rest = df.iloc[OR_KERZEN:]

    richtung = None
    level = None
    entry_stop = None
    entry_deadline = pd.Timestamp(f"{tag} {LAST_ENTRY}",
                                  tz="America/New_York")

    for zeit, k in rest.iterrows():
        o, h, l, c = (float(k["Open"]), float(k["High"]),
                      float(k["Low"]), float(k["Close"]))

        # Retest-Modus: Entry-Stop gesetzt, warten auf Ausloesung
        if entry_stop is not None:
            ausgeloest = (l <= entry_stop) if richtung == "short" \
                else (h >= entry_stop)
            if ausgeloest:
                if zeit > entry_deadline:
                    return None, "Entry erst nach Deadline"
                if ENTRY_AM_CLOSE:
                    return simuliere_trade(df, zeit, richtung, c, sl,
                                           or_high, or_low,
                                           ab_naechster=True), None
                return simuliere_trade(df, zeit, richtung, entry_stop,
                                       sl, or_high, or_low), None
            if (richtung == "short" and c > level) or \
               (richtung == "long" and c < level):
                return None, "zurueck in Range vor Entry"
            continue

        # Retest-Modus: Breakout da, warten auf Retest
        if richtung is not None:
            zurueck_in_range = (c > level) if richtung == "short" \
                else (c < level)
            if zurueck_in_range:
                return None, "Fake Breakout"
            if richtung == "short":
                if h >= level * (1 - RETEST_TOL) and c < level:
                    entry_stop = l
            else:
                if l <= level * (1 + RETEST_TOL) and c > level:
                    entry_stop = h
            if zeit > entry_deadline and entry_stop is None:
                return None, "kein Retest bis Deadline"
            continue

        # Warten auf den ersten Close ausserhalb der Range
        if c < or_low:
            richtung, level = "short", or_low
            sl = or_low + SL_FAKTOR * or_range
        elif c > or_high:
            richtung, level = "long", or_high
            sl = or_high - SL_FAKTOR * or_range
        elif zeit > entry_deadline:
            return None, "kein Breakout bis Deadline"
        if richtung is not None and ENTRY_MODUS == "breakout":
            if zeit > entry_deadline:
                return None, "Breakout erst nach Deadline"
            return simuliere_trade(df, zeit, richtung, c, sl,
                                   or_high, or_low,
                                   ab_naechster=True), None

    if richtung is None:
        return None, "kein Breakout"
    return None, "kein Entry"


def simuliere_trade(df, entry_zeit, richtung, entry, sl, or_high, or_low,
                    ab_naechster=False):
    """Simuliert SL/TP ab der Entry-Kerze. Konservativ: wenn SL und TP in
    derselben Kerze liegen, zaehlt der SL."""
    risiko = (sl - entry) if richtung == "short" else (entry - sl)
    if risiko <= 0:
        return None
    if TP_R is None:
        tp = None
    else:
        tp = entry - TP_R * risiko if richtung == "short" \
            else entry + TP_R * risiko

    nach = df.loc[entry_zeit:]
    if ab_naechster:
        nach = nach.iloc[1:]
    exit_preis, exit_zeit, exit_art = None, None, None
    for zeit, k in nach.iterrows():
        h, l = float(k["High"]), float(k["Low"])
        if richtung == "short":
            if h >= sl:
                exit_preis, exit_zeit, exit_art = sl, zeit, "SL"
                break
            if tp is not None and l <= tp:
                exit_preis, exit_zeit, exit_art = tp, zeit, "TP"
                break
        else:
            if l <= sl:
                exit_preis, exit_zeit, exit_art = sl, zeit, "SL"
                break
            if tp is not None and h >= tp:
                exit_preis, exit_zeit, exit_art = tp, zeit, "TP"
                break
    if exit_preis is None:
        exit_zeit = df.index[-1]
        exit_preis = float(df.iloc[-1]["Close"])
        exit_art = "Tagesschluss"

    exit_slip = SLIPPAGE + (STOP_SLIP if exit_art == "SL" else 0)
    if richtung == "short":
        entry_eff = entry * (1 - SLIPPAGE)
        exit_eff = exit_preis * (1 + exit_slip)
        gewinn = entry_eff - exit_eff
    else:
        entry_eff = entry * (1 + SLIPPAGE)
        exit_eff = exit_preis * (1 - exit_slip)
        gewinn = exit_eff - entry_eff

    return {
        "datum": str(entry_zeit.date()),
        "richtung": richtung,
        "entry_zeit": entry_zeit.strftime("%H:%M"),
        "entry": round(entry, 2),
        "sl": round(sl, 2),
        "tp": round(tp, 2) if tp is not None else None,
        "exit_zeit": exit_zeit.strftime("%H:%M"),
        "exit": round(exit_preis, 2),
        "exit_art": exit_art,
        "r": round(gewinn / risiko, 3),
        "or_high": round(or_high, 2),
        "or_low": round(or_low, 2),
    }
