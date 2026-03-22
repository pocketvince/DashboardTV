#!/usr/bin/env python3
import requests, re, os, urllib.parse
from datetime import datetime
from icalendar import Calendar
import recurring_ical_events

ICS_URLS = ["ICS Link 1","ICS Link 2"]
TODO_FILE = "todo_file.txt"
OUTPUT_HTML = "/var/www/html/dashboard.html"

def clean_agenda_text(text):
    if not text: return ""
    text = re.sub(r'[^\u0020-\u007E\u00A0-\u00FF\u0152\u0153\u0178]', '', text)
    return text.strip()

def get_todo():
    if not os.path.exists(TODO_FILE): return []
    try:
        with open(TODO_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    except: return []

def get_ics_agenda():
    all_day, timed = [], []
    start_day = datetime.now().replace(hour=0, minute=0, second=0)
    for url in ICS_URLS: ### debug (if forget link on line 7
        if not url.startswith("http") or "ICS Link" in url: continue
        try:
            r = requests.get(url, timeout=15)
            cal = Calendar.from_ical(r.content)
            events = recurring_ical_events.of(cal).at(start_day.date())
            for ev in events:
                summary = clean_agenda_text(str(ev.get('summary')))
                start = ev.get('dtstart').dt
                end = ev.get('dtend').dt if ev.get('dtend') else start
                if not isinstance(start, datetime):
                    all_day.append(summary)
                else:
                    t_s = start.strftime("%H:%M")
                    t_e = end.strftime("%H:%M") if isinstance(end, datetime) else "??:??"
                    timed.append((start, f"{t_s} \u2014 {t_e}", summary))
        except: continue
    timed.sort(key=lambda x: x[0])
    return all_day, [(t[1], t[2]) for t in timed]

def get_weather_symbol(desc):
    d = desc.lower()
    if any(x in d for x in ["soleil", "clear", "sunny"]): return "\u2600"
    if any(x in d for x in ["nuage", "cloud", "overcast", "couvert"]): return "\u2601"
    if any(x in d for x in ["pluie", "rain", "bruine", "averses"]): return "\u2614"
    if any(x in d for x in ["orage", "thunder"]): return "\u26A1"
    if any(x in d for x in ["neige", "snow"]): return "\u2744"
    return "\u2193"

def get_weather_data(city):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'} #weather area
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1&lang=fr"
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            h = r.json()['weather'][0]['hourly']
            return [h[i] for i in [3, 4, 5, 6, 7]]
        return None
    except: return None

def get_news():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'} #news area
        r = requests.get("https://news.google.com/rss/search?q=belgique&hl=fr-BE&gl=BE&ceid=BE:fr", headers=headers, timeout=10)
        titles = re.findall(r'<title>(.*?)</title>', r.text)
        news = [t.split(" - ")[0].replace("<![CDATA[", "").replace("]]>", "").strip() for t in titles if "Google" not in t]
        return news[1:8]
    except: return [""]

# --- GENERATION HTML ---
now_dt = datetime.now() #can be changed in english
jours = ["LUNDI", "MARDI", "MERCREDI", "JEUDI", "VENDREDI", "SAMEDI", "DIMANCHE"]
mois = ["JANVIER", "FÉVRIER", "MARS", "AVRIL", "MAI", "JUIN", "JUILLET", "AOÛT", "SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DÉCEMBRE"]

meteo_html = ""
for city in ["Location 1", "Location 2", "Location 3"]:
    data = get_weather_data(city)
    slots = ""
    if data:
        for h_d in data:
            time_str = f"{int(h_d['time'])//100:02d}h"
            symbol = get_weather_symbol(h_d.get('lang_fr', [{}])[0].get('value', ''))
            temp = h_d['tempC']
            slots += f'<div class="meteo-slot"><div class="meteo-time">{time_str}</div><div class="meteo-icon">{symbol}</div><div class="meteo-temp">{temp}<sup>°</sup></div></div>'
    meteo_html += f'<div class="meteo-row"><div class="meteo-city">{city}</div><div class="meteo-slots">{slots}</div></div>'

agenda_html = ""
all_day_evs, timed_evs = get_ics_agenda()
for ev in all_day_evs:
    agenda_html += f'<div class="agenda-item"><div class="bar"></div><div><div class="agenda-name hot">{ev}</div></div></div>'
for time_str, name in timed_evs:
    agenda_html += f'<div class="agenda-item"><div class="bar dim"></div><div><div class="agenda-name">{name}</div><div class="agenda-time">{time_str}</div></div></div>'

todo_html = ""
for item in get_todo():
    todo_html += f'<div class="todo-item"><div class="checkbox"></div><div class="todo-text">{item}</div></div>'

news_html = ""
for item in get_news():
    news_html += f'<div class="news-item"><div class="slash">//</div><div class="news-text">{item}</div></div>'

html_template = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=1920"><title>Dashboard</title><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@300;400;500&family=Barlow+Condensed:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {    --red:     #E8321A;    --red-dim: #7A1A0D;    --bg:      #0A0A0A;    --bg2:     #111111;    --bg3:     #161616;    --line:    #242424;    --line2:   #353535;    --white:   #F0EDE8;    --muted:   #787870;    --mono:    'DM Mono', monospace;    --cond:    'Barlow Condensed', sans-serif;    --display: 'Bebas Neue', cursive;  }
  html, body {    width: 1920px;    height: 1080px;    overflow: hidden;    background: var(--bg);    color: var(--white);    font-family: var(--cond);  }
  body::before {    content: '';    position: fixed;    inset: 0;    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 300 300' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");    opacity: 0.022;    pointer-events: none;    z-index: 999;  }
  .root { display: grid; grid-template-rows: 148px 1fr 32px; height: 1080px; width: 1920px; }
  .header { display: flex; align-items: flex-end; justify-content: space-between; padding: 0 80px 22px; border-bottom: 1px solid var(--line2); position: relative; background: var(--bg); }
  .header::after { content: ''; position: absolute; bottom: -4px; left: 0; right: 0; height: 3px; background: var(--red); }
  .date-main { font-family: var(--display); font-size: 104px; line-height: 1; letter-spacing: 0.025em; color: var(--white); text-transform: uppercase; }
  .date-main .accent { color: var(--red); }
  .header-right { display: flex; flex-direction: column; align-items: flex-end; gap: 8px; padding-bottom: 10px; }
  .status-row { font-family: var(--mono); font-size: 11px; letter-spacing: 0.14em; color: var(--muted); display: flex; align-items: center; gap: 10px; }
  .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--red); flex-shrink: 0; }
  .columns { display: grid; grid-template-columns: 1fr 1fr 1fr; height: 100%; overflow: hidden; }
  .col { display: flex; flex-direction: column; padding: 52px 68px; border-right: 1px solid var(--line); overflow: hidden; }
  .col:last-child { border-right: none; }  .col:nth-child(2) { background: var(--bg2); }  .col:nth-child(3) { background: var(--bg3); }
  .label { font-family: var(--display); font-size: 12px; letter-spacing: 0.3em; color: var(--red); display: flex; align-items: center; gap: 14px; margin-bottom: 40px; flex-shrink: 0; text-transform: uppercase; }
  .label::after { content: ''; flex: 1; height: 1px; background: var(--line2); }
  .meteo-rows { display: flex; flex-direction: column; flex: 1; justify-content: flex-start; gap: 15px; }
  .meteo-row { display: flex; flex-direction: column; gap: 20px; padding: 28px 0; border-top: 1px solid var(--line); }
  .meteo-row:last-child { border-bottom: 1px solid var(--line); }
  .meteo-city { font-family: var(--mono); font-size: 11px; font-weight: 500; letter-spacing: 0.2em; color: var(--muted); text-transform: uppercase; }
  .meteo-slots { display: grid; grid-template-columns: repeat(5, 1fr); }
  .meteo-slot { display: flex; flex-direction: column; align-items: center; gap: 7px; border-left: 1px solid var(--line); padding: 0 6px; }
  .meteo-slot:first-child { border-left: none; align-items: center; padding-left: 0; }
  .meteo-time { font-family: var(--mono); font-size: 10px; letter-spacing: 0.1em; color: var(--muted); }
  .meteo-icon { font-size: 20px; line-height: 1; }
  .meteo-temp { font-family: var(--display); font-size: 40px; line-height: 1; color: var(--white); }
  .meteo-temp sup { font-family: var(--mono); font-size: 12px; color: var(--muted); vertical-align: super; font-weight: 300; }
  .col-mid { padding: 0; gap: 0; }
  .sub { flex: 1; padding: 52px 68px; display: flex; flex-direction: column; overflow: hidden; }
  .sub:first-child { border-bottom: 1px solid var(--line2); flex: 0 0 auto; min-height: 45%; }
  .agenda-list { display: flex; flex-direction: column; gap: 22px; }
  .agenda-item { display: flex; gap: 20px; align-items: stretch; }
  .bar { width: 3px; background: var(--red); flex-shrink: 0; border-radius: 1px; min-height: 40px; }
  .bar.dim { background: var(--red-dim); }
  .agenda-name { font-family: var(--cond); font-size: 28px; font-weight: 600; letter-spacing: 0.03em; line-height: 1.1; color: var(--white); }
  .agenda-name.hot { color: var(--red); }
  .agenda-time { font-family: var(--mono); font-size: 11px; letter-spacing: 0.1em; color: var(--muted); margin-top: 5px; }
  .todo-list { display: flex; flex-direction: column; gap: 16px; flex: 1; }
  .todo-item { display: flex; align-items: center; gap: 20px; padding: 16px 22px; background: var(--bg); border-left: 3px solid var(--line2); }
  .checkbox { width: 18px; height: 18px; border: 1.5px solid var(--line2); flex-shrink: 0; }
  .todo-text { font-family: var(--cond); font-size: 23px; font-weight: 400; letter-spacing: 0.04em; }
  .news-list { display: flex; flex-direction: column; flex: 1; overflow: hidden; }
  .news-item { display: flex; gap: 16px; align-items: flex-start; padding: 20px 0; border-top: 1px solid var(--line); }
  .news-item:last-child { border-bottom: 1px solid var(--line); }
  .slash { font-family: var(--mono); font-size: 11px; color: var(--red-dim); flex-shrink: 0; margin-top: 4px; letter-spacing: 0.04em; }
  .news-text { font-family: var(--cond); font-size: 19px; font-weight: 300; line-height: 1.4; letter-spacing: 0.025em; color: var(--white); }
  .ticker { background: var(--red); display: flex; align-items: center; padding: 0 80px; gap: 32px; height: 32px; }
  .ticker-tag { font-family: var(--mono); font-size: 9px; font-weight: 500; letter-spacing: 0.22em; color: rgba(0,0,0,0.45); text-transform: uppercase; flex-shrink: 0; }
  .ticker-sep { width: 1px; height: 12px; background: rgba(0,0,0,0.25); flex-shrink: 0; }
  .ticker-text { font-family: var(--mono); font-size: 10px; letter-spacing: 0.12em; color: var(--white); white-space: nowrap; }
  .ticker-text b { color: #000; font-weight: 500; }
</style></head><body>
<div class="root">
  <header class="header">
    <div class="date-main">__DATE__</div>
    <div class="header-right">
      <div class="status-row">
        <span class="dot"></span>
        REFRESH __REFRESH__
      </div>
    </div>
  </header>
  <div class="columns">
    <div class="col">
      <div class="label">Météo</div>
      <div class="meteo-rows">
        __METEO__
      </div>
    </div>
    <div class="col col-mid">
      <div class="sub">
        <div class="label">Agenda</div>
        <div class="agenda-list">
          __AGENDA__
        </div>
      </div>
      <div class="sub">
        <div class="label">Todo</div>
        <div class="todo-list">
          __TODO__
        </div>
      </div>
    </div>
    <div class="col">
      <div class="label">News</div>
      <div class="news-list">
        __NEWS__
      </div>
    </div>
  </div>
  <div class="ticker">
    <div class="ticker-tag">SYSTEM</div>
    <div class="ticker-sep"></div>
    <div class="ticker-text"><b>ONLINE</b> // DATA SYNCED</div>
  </div>
</div></body></html>"""

html_output = html_template.replace("__DATE__", f"{jours[now_dt.weekday()]} <span class=\"accent\">{now_dt.day}</span> {mois[now_dt.month-1]} {now_dt.year}")
html_output = html_output.replace("__REFRESH__", now_dt.strftime('%H:%M'))
html_output = html_output.replace("__METEO__", meteo_html)
html_output = html_output.replace("__AGENDA__", agenda_html)
html_output = html_output.replace("__TODO__", todo_html)
html_output = html_output.replace("__NEWS__", news_html)

with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write(html_output)
