#!/usr/bin/env python3
"""POI-Datei fuer die Dashboard-Karte erzeugen: decoder/its_decoder/static/poi.json

Quellen (oeffentlich):
  * TEMPUS interaktive Karte (Google My Maps, eingebettet auf https://tempus-muenchen.de/karte): Lichtsignalanlagen mit RSU
    (ITS-G5 / C-V2X / hybrid), Use Cases, Testfeld-Strassen, Buslinien 178 und 180.
  * BASt "Digitales Testfeld Autobahn" (https://www.bast.de/DE/Themen/Fahren/HF_3/Massnahmen/digitales-testfeld.html):
    "etwa 140 Kilometer langen Abschnitt auf der A9 zwischen Nuernberg und Muenchen". Die genaue Ausdehnung nennt die Seite nicht;
    gezeichnet wird die A9 (OpenStreetMap) von Muenchen-Nord bis ca. 140 km nach Norden. Ob dort ITS-G5 gesendet wird, ist NICHT belegt.
  * Strassennamen zu den LSA-Punkten: Nominatim (OpenStreetMap), hoechstens 1 Anfrage/s.

    python scripts/poi_tempus.py [--cache /tmp/nominatim-cache.json] [--out decoder/its_decoder/static/poi.json]
"""
import argparse, json, math, os, re, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

UA = "Ice-Traffic-Data-Auswertung/1.0 (privates Forschungsprojekt; github.com/icepaule/Ice-Traffic-Data)"
MID = "1oOJLO9c4-xhMJ-eVpLNPi818OhqZALXl"
K = "{http://www.opengis.net/kml/2.2}"
TECH = {"ITSG5": "ITS-G5", "CV2X": "C-V2X", "Hybrid (ITSG5 & CV2X)": "Hybrid"}


def get(url, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=120).read()


def dp(pts, tol):
    """Douglas-Peucker (Toleranz in Grad)"""
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    n = math.hypot(dx, dy) or 1e-12
    best, bi = 0, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy * pts[i][0] - dx * pts[i][1] + x2 * y1 - y2 * x1) / n
        if d > best:
            best, bi = d, i
    if best <= tol:
        return [pts[0], pts[-1]]
    return dp(pts[:bi + 1], tol)[:-1] + dp(pts[bi:], tol)


def strasse(lat, lon, cache, path):
    k = f"p{lat:.4f},{lon:.4f}"
    if k in cache:
        return cache[k]
    q = urllib.parse.urlencode({"lat": f"{lat:.6f}", "lon": f"{lon:.6f}", "format": "jsonv2", "zoom": 17, "addressdetails": 1, "accept-language": "de"})
    try:
        a = json.loads(get("https://nominatim.openstreetmap.org/reverse?" + q)).get("address", {})
    except Exception as e:  # noqa: BLE001
        a = {}
    r = {"strasse": a.get("road", ""), "ortsteil": a.get("suburb") or a.get("city_district") or "", "ort": a.get("city") or a.get("town") or a.get("village") or a.get("municipality") or ""}
    cache[k] = r
    json.dump(cache, open(path, "w"), ensure_ascii=False)
    time.sleep(1.1)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="/tmp/nominatim-cache.json")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "decoder", "its_decoder", "static", "poi.json"))
    ap.add_argument("--kml")
    a = ap.parse_args()
    cache = json.load(open(a.cache)) if os.path.exists(a.cache) else {}
    kml = open(a.kml, "rb").read() if a.kml else get(f"https://www.google.com/maps/d/kml?mid={MID}&forcekml=1")
    root = ET.fromstring(kml)
    pois, lines = [], []
    for f in root.iter(K + "Folder"):
        fn = f.find(K + "name").text
        gebiet = "Stadt" if "STADT" in fn else "Land"
        for p in f.findall(K + "Placemark"):
            name = p.find(K + "name").text or ""
            d = p.find(K + "description")
            desc = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", d.text if d is not None and d.text else "")).strip()
            if fn.startswith("LSAs"):
                tech = TECH.get(name, name)
                for pt in p.iter(K + "Point"):
                    lon, lat = (float(x) for x in pt.find(K + "coordinates").text.strip().split(",")[:2])
                    s = strasse(lat, lon, cache, a.cache)
                    ort = ", ".join(v for v in (s["strasse"], s["ortsteil"] or s["ort"]) if v)
                    pois.append({"typ": "lsa", "tech": tech, "gebiet": gebiet, "name": f"Ampel mit RSU ({tech})", "nahe": ort, "lat": round(lat, 6), "lon": round(lon, 6), "text": desc})
            elif fn.startswith("Use Cases"):
                for pt in p.iter(K + "Point"):
                    lon, lat = (float(x) for x in pt.find(K + "coordinates").text.strip().split(",")[:2])
                    pois.append({"typ": "usecase", "tech": "", "gebiet": gebiet, "name": f"Use Case: {name}", "nahe": "", "lat": round(lat, 6), "lon": round(lon, 6), "text": desc})
            else:  # Testfeld-Linien
                kind = "bus" if name.startswith("Buslinie") else "testfeld"
                for ls in p.iter(K + "LineString"):
                    pts = [[float(v) for v in c.split(",")[:2]] for c in ls.find(K + "coordinates").text.split()]
                    pts = dp(pts, 0.00005 if kind == "testfeld" else 0.00003)
                    lines.append({"typ": kind, "gebiet": gebiet, "name": name, "text": desc, "pts": [[round(y, 5), round(x, 5)] for x, y in pts]})
    # A9 (Digitales Testfeld Autobahn)
    ov = json.loads(get("https://overpass-api.de/api/interpreter", urllib.parse.urlencode({"data": '[out:json][timeout:60];way["ref"~"(^|;)A ?9($|;)"]["highway"="motorway"](48.20,11.00,49.46,12.00);out geom tags;'}).encode()))
    n = 0
    for w in ov["elements"]:
        pts = [[p["lon"], p["lat"]] for p in w["geometry"]]
        if len(pts) < 2:
            continue
        pts = dp(pts, 0.0001)
        lines.append({"typ": "a9", "gebiet": "Land", "name": "A9", "text": "", "pts": [[round(y, 4), round(x, 4)] for x, y in pts]})
        n += 1
    out = {"stand": time.strftime("%Y-%m-%d"),
           "quellen": [
               {"name": "TEMPUS – interaktive Karte (Lage der Ampeln mit RSU, Use Cases, Testfeld)", "url": "https://tempus-muenchen.de/karte"},
               {"name": "BASt – Digitales Testfeld Autobahn (A9 zwischen Nürnberg und München, ca. 140 km)", "url": "https://www.bast.de/DE/Themen/Fahren/HF_3/Massnahmen/digitales-testfeld.html"},
               {"name": "Straßen- und Ortsnamen: © OpenStreetMap-Mitwirkende (ODbL), Nominatim", "url": "https://www.openstreetmap.org/copyright"}],
           "pois": pois, "linien": lines}
    json.dump(out, open(a.out, "w"), ensure_ascii=False, separators=(",", ":"))
    from collections import Counter
    print(len(pois), "POIs", Counter((p["typ"], p["tech"]) for p in pois), len(lines), "Linien, A9-Wege", n, os.path.getsize(a.out) // 1024, "kB")


if __name__ == "__main__":
    main()
