#!/usr/bin/env python3
import requests, textwrap, re, os, urllib.parse
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
from icalendar import Calendar
import recurring_ical_events

ICS_URLS = ["ICS Link1","ICS Link 2"]
TODO_FILE = "todo_file.txt"
OUTPUT = "/var/www/html/dashboard.png"
W, H = 1920, 1200

BG, RED, WHITE, GREY, DIM = "#050505", "#FF3E3E", "#FFFFFF", "#1A1A1A", "#888888"


def clean_agenda_text(text):
    if not text: return ""
    text = re.sub(r'[^\u0020-\u007E\u00A0-\u00FF\u0152\u0153\u0178]', '', text)
    return text.strip()

def get_todo():
    """Récupère les tâches depuis le fichier texte s'il existe"""
    if not os.path.exists(TODO_FILE): return []
    try:
        with open(TODO_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    except: return []

def get_ics_agenda():
    """Récupère et fusionne plusieurs calendriers avec gestion des récurrences"""
    all_day, timed = [], []
    start_day = datetime.now().replace(hour=0, minute=0, second=0)

    for url in ICS_URLS:
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
                    all_day.append(f"// {summary}")
                else:
                    t_s = start.strftime("%H:%M")
                    t_e = end.strftime("%H:%M") if isinstance(end, datetime) else "??:??"
                    timed.append((start, f"// {t_s} - {t_e}: {summary}"))
        except: continue

    timed.sort(key=lambda x: x[0])
    return all_day, [t[1] for t in timed]

def get_weather_symbol(desc):
    d = desc.lower()
    if any(x in d for x in ["soleil", "clear", "sunny"]): return "\u2600"
    if any(x in d for x in ["nuage", "cloud", "overcast", "couvert"]): return "\u2601"
    if any(x in d for x in ["pluie", "rain", "bruine", "averses"]): return "\u2614"
    if any(x in d for x in ["orage", "thunder"]): return "\u26A1"
    if any(x in d for x in ["neige", "snow"]): return "\u2744"
    return "\u2321"

def get_weather_data(city):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1&lang=fr"
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            h = r.json()['weather'][0]['hourly']
            return [h[i] for i in [3, 4, 5, 6, 7]]
        return None
    except: return None

def get_news():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get("https://news.google.com/rss/search?q=belgique&hl=fr-BE&gl=BE&ceid=BE:fr", headers=headers, timeout=10)
        titles = re.findall(r'<title>(.*?)</title>', r.text)
        news = [t.split(" - ")[0].replace("<![CDATA[", "").replace("]]>", "").strip() for t in titles if "Google" not in t]
        return news[1:30]
    except: return [""]

# --- RENDU ---
img = Image.new('RGB', (W, H), color=BG)
draw = ImageDraw.Draw(img)

f_p = "/usr/share/fonts/truetype/dejavu/DejaVuSans"
try:
    f_huge = ImageFont.truetype(f"{f_p}-Bold.ttf", 110)
    f_mid = ImageFont.truetype(f"{f_p}-Bold.ttf", 40)
    f_reg = ImageFont.truetype(f"{f_p}.ttf", 26)
    f_small = ImageFont.truetype(f"{f_p}.ttf", 26)
    f_mono = ImageFont.truetype(f"{f_p}Mono.ttf", 18)
except:
    f_huge = f_mid = f_reg = f_small = f_mono = ImageFont.load_default()

# 1. HEADER
now_dt = datetime.now()
jours = ["LUNDI", "MARDI", "MERCREDI", "JEUDI", "VENDREDI", "SAMEDI", "DIMANCHE"]
mois = ["JANVIER", "FÉVRIER", "MARS", "AVRIL", "MAI", "JUIN", "JUILLET", "AOÛT", "SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DÉCEMBRE"]
draw.text((80, 80), f"{jours[now_dt.weekday()]} {now_dt.day} {mois[now_dt.month-1]} {now_dt.year}", fill=RED, font=f_huge)

# 2. MÉTÉO
sep_x = 1150
draw.line((80, 310, sep_x - 60, 310), fill=GREY, width=2)
draw.text((80, 340), "METEO", fill=RED, font=f_mid)
y_w = 410
for city in ["Location 1", "Location 2", "Location 3"]:
    draw.text((80, y_w), city.upper(), fill=WHITE, font=f_small)
    data = get_weather_data(city)
    if data:
        x_s = 320
        for h_d in data:
            symbol = get_weather_symbol(h_d.get('lang_fr', [{}])[0].get('value', ''))
            draw.text((x_s, y_w), f"{int(h_d['time'])//100:02d}h {symbol} {h_d['tempC']}°", fill=DIM, font=f_small)
            x_s += 160
    y_w += 65

draw.line((80, 610, sep_x - 60, 610), fill=GREY, width=2)
draw.text((80, 640), "AGENDA", fill=RED, font=f_mid)
y_a = 720
all_day_evs, timed_evs = get_ics_agenda()
for ev in all_day_evs:
    draw.text((80, y_a), ev, fill=RED, font=f_reg)
    y_a += 42
for ev in timed_evs:
    draw.text((80, y_a), ev, fill=WHITE, font=f_reg)
    y_a += 38
    if y_a > 1140: break

draw.line((sep_x, 310, sep_x, 1140), fill=GREY, width=2)

draw.text((sep_x + 50, 340), "TODO", fill=RED, font=f_mid)
y_todo = 410
for item in get_todo():
    draw.text((sep_x + 50, y_todo), f"{item}", fill=WHITE, font=f_reg)
    y_todo += 40
    if y_todo > 620: break

draw.line((sep_x + 40, 650, W - 80, 650), fill=GREY, width=1)
draw.text((sep_x + 50, 680), "NEWS", fill=RED, font=f_mid)
y_n = 750
for item in get_news():
    wrapped = textwrap.wrap(item, width=45)
    for i, line in enumerate(wrapped):
        draw.text((sep_x + 50, y_n), ("// " if i == 0 else "   ") + line, fill=WHITE, font=f_small)
        y_n += 22
    y_n += 10
    if y_n > 1130: break

draw.text((80, H - 55), f"STATUS: ONLINE | {W}x{H} | REFRESH: {now_dt.strftime('%H:%M')}", fill=DIM, font=f_mono)

img.save(OUTPUT)
