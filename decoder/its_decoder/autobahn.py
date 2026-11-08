"""Baustellen, Sperrungen und Warnungen der Autobahn GmbH rund um Muenchen (offene Autobahn-App-API, ohne Schluessel).

Warum: Die mobilen Absperrtafeln der Baustellen senden per ITS-G5 eine Baustellenwarnung (Autobahn GmbH, "Baustellenwarner",
siehe docs/23). Wo die API eine Tagesbaustelle meldet, lohnt sich ein Empfangstest.
Quelle der API-Beschreibung: https://github.com/bundesAPI/autobahn-api ; Daten: https://verkehr.autobahn.de/o/autobahn/
Die Nutzungsbedingungen der Daten sind NICHT geprueft; die Daten werden nur zur Anzeige im privaten Dashboard abgerufen und nicht im Repo abgelegt.
"""
import json
import math
import threading
import time
import urllib.request

BASE = "https://verkehr.autobahn.de/o/autobahn"
ROADS = ["A8", "A9", "A92", "A94", "A95", "A96", "A99"]
SERVICES = ("roadworks", "warning", "closure")
CENTER = (48.14, 11.58)   # Muenchen
RADIUS_KM = 70
UA = "Ice-Traffic-Data-Dashboard/1.0 (privat; github.com/icepaule/Ice-Traffic-Data)"
REFRESH_S = 600

_state = {"items": [], "ts": 0, "fehler": 0}
_lock = threading.Lock()


def _km(lat, lon):
    x = math.radians(lon - CENTER[1]) * math.cos(math.radians((lat + CENTER[0]) / 2))
    y = math.radians(lat - CENTER[0])
    return 6371 * math.hypot(x, y)


def _get(path):
    req = urllib.request.Request(f"{BASE}/{path}", headers={"User-Agent": UA})
    return json.loads(urllib.request.urlopen(req, timeout=20).read())


def refresh():
    items, err = [], 0
    for road in ROADS:
        for svc in SERVICES:
            try:
                data = _get(f"{road}/services/{svc}").get(svc, [])
            except Exception:  # noqa: BLE001
                err += 1
                continue
            for it in data:
                c = it.get("coordinate") or {}
                lat, lon = c.get("lat"), c.get("long")
                try:
                    lat, lon = float(lat), float(lon)
                except (TypeError, ValueError):
                    continue
                if _km(lat, lon) > RADIUS_KM:
                    continue
                items.append({"typ": svc, "strasse": road, "titel": it.get("title", ""), "richtung": (it.get("subtitle") or "").strip(),
                              "lat": round(lat, 5), "lon": round(lon, 5), "gesperrt": str(it.get("isBlocked")).lower() == "true",
                              "zukuenftig": bool(it.get("future")), "art": it.get("display_type", ""), "beginn": it.get("startTimestamp", ""),
                              "text": " ".join(x for x in (it.get("description") or []) if x)[:400]})
    with _lock:
        _state.update(items=items, ts=time.time(), fehler=err)


def snapshot():
    with _lock:
        return dict(_state)


def start():
    def run():
        while True:
            try:
                refresh()
            except Exception:  # noqa: BLE001
                pass
            time.sleep(REFRESH_S)
    threading.Thread(target=run, daemon=True).start()
