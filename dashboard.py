# -*- coding: utf-8 -*-
"""Erzeugt docs/index.html (GitHub-Pages-Dashboard) aus log/trades.csv.

Trades sind zweigeteilt:
- "warmup"  = Aufwaermphase (Daten aus dem Optimierungszeitraum,
              nur zur Anschauung - NICHT beweiskraeftig)
- "forward" = echter Forward-Test ab START (das einzige Ergebnis,
              das zaehlt)
"""

import json
import os
from datetime import date

import pandas as pd

os.makedirs("docs", exist_ok=True)
START = "2026-07-03"
RISK_CHF = 100.0

SPALTEN = ["datum", "ticker", "variante", "phase", "richtung", "entry_zeit",
           "entry", "sl", "exit_zeit", "exit", "exit_art", "r"]
if os.path.exists("log/trades.csv"):
    t = pd.read_csv("log/trades.csv")
    if "phase" not in t.columns:
        t["phase"] = "forward"
    t = t.sort_values(["datum", "ticker"])
else:
    t = pd.DataFrame(columns=SPALTEN)

varianten = ["SL25", "SL50", "SL75", "Video", "RetestMax", "Retest3K"]
farben = {"SL25": "#f59e0b", "SL50": "#38bdf8", "SL75": "#a78bfa",
          "Video": "#34d399", "RetestMax": "#f472b6", "Retest3K": "#facc15"}


def stats_html(tv, titel, gross):
    rs = tv["r"].tolist()
    gewinne = [r for r in rs if r > 0]
    ges = sum(rs)
    tq = round(100 * len(gewinne) / len(rs), 1) if rs else 0
    cls = "plus" if ges >= 0 else "minus"
    w = "wert" if gross else "wert klein2"
    return f"""
  <div class="card"><div class="label">{titel}</div>
    <div class="{w} {cls}">{ges:+.2f} R</div>
    <div class="sub2">{len(rs)} Trades · {tq} % Treffer ·
    {ges * RISK_CHF:+.0f} CHF bei {RISK_CHF:.0f} CHF Risiko</div></div>"""


karten_fwd, karten_warm, datensaetze = "", "", []
for v in varianten:
    tv = t[t["variante"] == v]
    karten_fwd += stats_html(tv[tv["phase"] == "forward"],
                             f"{v} · Forward-Test (zaehlt)", True)
    karten_warm += stats_html(tv[tv["phase"] == "warmup"],
                              f"{v} · Aufwaermphase (In-Sample)", False)
    # kumulierte Kurve: Warmup gestrichelt, Forward durchgezogen
    tages = tv.groupby("datum")["r"].sum().sort_index()
    kum, s = [], 0.0
    for d, r in tages.items():
        s += r
        kum.append({"x": d, "y": round(s, 2)})
    warm = [p for p in kum if p["x"] < START]
    fwd = [p for p in kum if p["x"] >= START]
    if warm and fwd:
        fwd = [warm[-1]] + fwd          # Kurve verbinden
    datensaetze.append({"label": f"{v} Aufwaermphase", "data": warm,
                        "borderColor": farben[v], "borderDash": [6, 4],
                        "pointRadius": 0, "tension": 0.2})
    datensaetze.append({"label": f"{v} Forward", "data": fwd,
                        "borderColor": farben[v], "borderWidth": 2.5,
                        "pointRadius": 2, "tension": 0.2})

def pro_wert_tabelle(tp):
    """Gesamt-R pro Wert und Variante als HTML-Tabelle."""
    if len(tp) == 0:
        return ""
    p = tp.pivot_table(index="ticker", columns="variante", values="r",
                       aggfunc="sum").fillna(0).round(2)
    for v in varianten:
        if v not in p.columns:
            p[v] = 0.0
    p["Summe"] = p[varianten].sum(axis=1).round(2)
    p = p.sort_values("Summe", ascending=False)
    zl = ""
    for tk, z in p.iterrows():
        zellen = "".join(
            f"<td class='{'plus' if z[v] > 0 else 'minus'}'>{z[v]:+.1f}</td>"
            for v in varianten)
        cls = "plus" if z["Summe"] > 0 else "minus"
        zl += (f"<tr><td>{tk}</td>{zellen}"
               f"<td class='{cls}'><b>{z['Summe']:+.1f}</b></td></tr>")
    kopf = "".join(f"<th>{v}</th>" for v in varianten)
    return (f"<table><tr><th>Wert</th>{kopf}<th>Summe</th></tr>{zl}</table>")


pro_wert_fwd = pro_wert_tabelle(t[t["phase"] == "forward"])
pro_wert_warm = pro_wert_tabelle(t[t["phase"] == "warmup"])
panel_fwd = f"""<div class="panel"><h2>Pro Wert – Forward-Test (R)</h2>
{pro_wert_fwd}</div>""" if pro_wert_fwd else ""
panel_warm = f"""<div class="panel"><h2>Pro Wert – Aufwaermphase (R,
nicht beweiskraeftig)</h2>{pro_wert_warm}</div>""" if pro_wert_warm else ""

zeilen = ""
for _, z in t.sort_values(["datum", "ticker"]).tail(40)[::-1].iterrows():
    cls = "plus" if z["r"] > 0 else "minus"
    ph = "Forward" if z["phase"] == "forward" else "Aufwaermph."
    zeilen += (f"<tr><td>{z['datum']}</td><td>{z['ticker']}</td>"
               f"<td>{z['variante']}</td><td>{ph}</td><td>{z['richtung']}</td>"
               f"<td>{z['entry_zeit']}</td><td>{z['exit_art']}</td>"
               f"<td class='{cls}'>{z['r']:+.2f} R</td></tr>")

leer = ""
if len(t[t["phase"] == "forward"]) == 0:
    leer = """<div class="hinweis">Der echte Forward-Test hat noch keine
Trades - er beginnt mit dem ersten Handelstag ab 2026-07-03. Die
Aufwaermphase unten dient nur zur Anschauung.</div>"""

html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ORB Forward-Test</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  body {{ font-family: system-ui, sans-serif; background: #0f172a;
         color: #e2e8f0; margin: 0; padding: 24px; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  .sub {{ color: #94a3b8; margin-bottom: 20px; }}
  .cards {{ display: grid; grid-template-columns:
            repeat(auto-fit, minmax(260px, 1fr)); gap: 12px;
            margin-bottom: 12px; }}
  .card {{ background: #1e293b; border-radius: 10px; padding: 14px 16px; }}
  .card .label {{ font-size: 12px; color: #94a3b8; }}
  .card .wert {{ font-size: 24px; font-weight: 600; margin-top: 4px; }}
  .card .wert.klein2 {{ font-size: 18px; }}
  .card .sub2 {{ font-size: 12px; color: #94a3b8; margin-top: 4px; }}
  .plus {{ color: #4ade80; }} .minus {{ color: #f87171; }}
  .panel {{ background: #1e293b; border-radius: 10px; padding: 16px;
           margin-bottom: 24px; }}
  .panel h2 {{ font-size: 15px; margin: 0 0 12px; color: #94a3b8;
              font-weight: 500; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ padding: 6px 8px; text-align: left;
            border-bottom: 1px solid #334155; }}
  th {{ color: #94a3b8; font-weight: 500; }}
  .hinweis {{ background: #172554; border: 1px solid #3b82f6;
             border-radius: 10px; padding: 12px 16px; margin-bottom: 24px;
             font-size: 14px; }}
  .warnung {{ background: #422006; border: 1px solid #a16207;
             color: #fde68a; border-radius: 10px; padding: 10px 16px;
             margin-bottom: 24px; font-size: 13px; }}
</style>
</head>
<body>
<h1>First-Candle-Strategie – Forward-Test (Paper Trading)</h1>
<div class="sub">Direkt-Entry · kein TP · Top-10-US-Aktien + SPY + QQQ
+ F + SHOP (14 Werte) · Forward-Start {START} · Stand {date.today()} ·
inkl. 0.05 % Stop-Slippage</div>
{leer}
<div class="cards">{karten_fwd}</div>
<div class="cards">{karten_warm}</div>
<div class="warnung">⚠️ Die Aufwaermphase (gestrichelt) stammt aus dem
Zeitraum, auf dem die Strategie optimiert wurde - sie sieht deshalb
systematisch zu gut aus und beweist nichts. Es zaehlt nur die
durchgezogene Forward-Linie ab {START}.</div>
<div class="panel"><h2>Kontoverlauf (kumuliertes R, alle 14 Werte)</h2>
  <canvas id="equity" height="90"></canvas></div>
{panel_fwd}
{panel_warm}
<div class="panel"><h2>Letzte Trades</h2>
<table><tr><th>Datum</th><th>Wert</th><th>Variante</th><th>Phase</th>
<th>Richtung</th><th>Entry</th><th>Exit</th><th>R</th></tr>
{zeilen}
</table></div>
<script>
const datensaetze = {json.dumps(datensaetze)};
Chart.defaults.color = "#94a3b8";
Chart.defaults.borderColor = "#334155";
new Chart(document.getElementById("equity"), {{
  type: "line",
  data: {{ datasets: datensaetze }},
  options: {{ parsing: {{ xAxisKey: "x", yAxisKey: "y" }},
    scales: {{ x: {{ type: "category" }},
              y: {{ title: {{ display: true, text: "R" }} }} }} }}
}});
</script>
</body>
</html>"""

with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(html)
print("-> docs/index.html geschrieben")
