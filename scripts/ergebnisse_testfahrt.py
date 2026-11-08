#!/usr/bin/env python3
"""Aus den Rohdaten einer Testfahrt (log.csv + frames.bin) die veroeffentlichbaren Ergebnisse erzeugen:

  1. bereinigte Rohdaten  (Sperrzone um Start/Ziel entfernt)  -> OUT/daten/
  2. Empfangs-Timeline    (Position + Strasse/Hausnummer ueber Nominatim) -> OUT/empfang_timeline.csv, empfang_abschnitte.csv
  3. Karte                (Leaflet-HTML + PNG, nur Strecke ausserhalb der Sperrzone)

Datenschutz: Die Sperrzone (Standard 5 km um den ersten und letzten GPS-Fix) wird aus ALLEN Ausgaben entfernt. Es wird weder ein
Kreis noch der Mittelpunkt eingezeichnet. Die Rohdaten selbst gehoeren nicht ins Repo.

Nominatim-Nutzungsbedingungen: hoechstens 1 Anfrage/s, eigener User-Agent, Attribution
(https://operations.osmfoundation.org/policies/nominatim/). Ergebnisse werden zwischengespeichert (--cache).

    python scripts/ergebnisse_testfahrt.py ROHDATEN OUT --html docs/karte-testfahrt-1.html --png docs/screenshots/karte-testfahrt-1.png
"""
import argparse, bisect, collections, csv, datetime, json, math, os, struct, sys, time, urllib.parse, urllib.request

UA = "Ice-Traffic-Data-Auswertung/1.0 (privates Forschungsprojekt; github.com/icepaule/Ice-Traffic-Data)"


def dist_m(a, b, c, d):
    x = math.radians(d - b) * math.cos(math.radians((a + c) / 2))
    y = math.radians(c - a)
    return 6371000 * math.hypot(x, y)


def read_frames(path):
    d = open(path, "rb").read()
    p = 0
    while p + 14 <= len(d) and d[p:p + 4] == b"ITS5":
        s, u, l = struct.unpack("<IIH", d[p + 4:p + 14])
        yield s, u, d[p + 14:p + 14 + l]
        p += 14 + l


def geocode(lat, lon, cache, path):
    k = f"{lat:.4f},{lon:.4f}"
    if k in cache:
        return cache[k]
    q = urllib.parse.urlencode({"lat": f"{lat:.6f}", "lon": f"{lon:.6f}", "format": "jsonv2", "zoom": 18, "addressdetails": 1, "accept-language": "de"})
    req = urllib.request.Request("https://nominatim.openstreetmap.org/reverse?" + q, headers={"User-Agent": UA})
    try:
        a = json.load(urllib.request.urlopen(req, timeout=30)).get("address", {})
    except Exception as e:  # noqa: BLE001
        a = {"fehler": str(e)[:40]}
    r = {"strasse": a.get("road") or a.get("pedestrian") or a.get("footway") or a.get("path") or "",
         "hausnummer": a.get("house_number", ""),
         "ortsteil": a.get("suburb") or a.get("city_district") or a.get("neighbourhood") or "",
         "ort": a.get("city") or a.get("town") or a.get("village") or a.get("municipality") or "", "plz": a.get("postcode", "")}
    cache[k] = r
    json.dump(cache, open(path, "w"), ensure_ascii=False, indent=0)
    time.sleep(1.1)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw"); ap.add_argument("out")
    ap.add_argument("--trim-km", type=float, default=5.0)
    ap.add_argument("--cache", default="/tmp/nominatim-cache.json")
    ap.add_argument("--html"); ap.add_argument("--png")
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out, "daten"), exist_ok=True)
    cache = json.load(open(a.cache)) if os.path.exists(a.cache) else {}
    trim = a.trim_km * 1000

    rows = [r for r in csv.reader(open(os.path.join(a.raw, "log.csv"))) if len(r) == 13 and r[0]]
    ts = lambda s: datetime.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    fixes = [(ts(r[0]), float(r[3]), float(r[4])) for r in rows if r[2] == "1" and float(r[3]) != 0]
    h0, h1 = fixes[0], fixes[-1]
    inzone = lambda lat, lon: dist_m(lat, lon, h0[1], h0[2]) <= trim or dist_m(lat, lon, h1[1], h1[2]) <= trim
    zone_t = [t for t, la, lo in fixes if inzone(la, lo)]
    near_zone = lambda t: bool(zone_t) and (lambda i: min(abs(t - zone_t[max(0, i - 1)]), abs(t - zone_t[min(len(zone_t) - 1, i)])) <= 120)(bisect.bisect(zone_t, t))

    # 1. bereinigtes Log
    kept = []
    for r in rows:
        t = ts(r[0])
        if r[2] == "1" and float(r[3]) != 0:
            if inzone(float(r[3]), float(r[4])):
                continue
        elif near_zone(t):
            continue
        kept.append(r)
    with open(os.path.join(a.out, "daten", "log_bereinigt.csv"), "w", newline="") as f:
        f.write("utc,uptime_s,fix,lat,lon,kmh,sats,cam,denm,spatem,mapem,signiert,sonstige\n")
        csv.writer(f, lineterminator="\n").writerows(kept)
    # 1b. bereinigte Frames
    T = [p[0] for p in fixes]

    def own(t):
        i = bisect.bisect(T, t)
        if i == 0 or i >= len(T) or T[i] - T[i - 1] > 30:
            return None
        w = (t - T[i - 1]) / (T[i] - T[i - 1])
        return fixes[i - 1][1] + w * (fixes[i][1] - fixes[i - 1][1]), fixes[i - 1][2] + w * (fixes[i][2] - fixes[i - 1][2])
    fr_keep = []; fr_all = 0
    for s, u, f in read_frames(os.path.join(a.raw, "frames.bin")):
        fr_all += 1
        if s < 1.7e9:
            continue
        o = own(s)
        if (o and not inzone(*o)) or (not o and not near_zone(s)):
            fr_keep.append((s, u, f))
    with open(os.path.join(a.out, "daten", "frames_bereinigt.bin"), "wb") as w:
        for s, u, f in fr_keep:
            w.write(b"ITS5" + struct.pack("<IIH", s, u, len(f)) + f)
    with open(os.path.join(a.out, "daten", "frames_bereinigt.pcap"), "wb") as w:
        w.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 105))
        for s, u, f in fr_keep:
            w.write(struct.pack("<IIII", s, u, len(f), len(f)) + f)
    print(f"Log: {len(rows)} -> {len(kept)} Zeilen; Frames: {fr_all} -> {len(fr_keep)}")

    # Typen der bereinigten Frames (fuer Timeline)
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "decoder"))
    from its_decoder import gn, schemas
    S = schemas.load()
    fr_typ = []
    for s, u, f in fr_keep:
        g = gn.parse_frame(f, S["SEC"])
        fr_typ.append((s + u / 1e6, g.msg_type or "?"))
    fr_t = [x[0] for x in fr_typ]

    # 2. Timeline
    tl = []
    for r in kept:
        if r[2] != "1" or float(r[3]) == 0:
            continue
        pk = sum(int(x) for x in r[7:13])
        if pk == 0:
            continue
        t = ts(r[0])
        lo, hi = bisect.bisect_left(fr_t, t - 10), bisect.bisect_right(fr_t, t)
        sv = collections.Counter(fr_typ[i][1] for i in range(lo, hi))
        tl.append(dict(utc=r[0], lat=float(r[3]), lon=float(r[4]), kmh=int(r[5]), sats=int(r[6]), pakete=pk,
                       cam_log=int(r[7]), denm_log=int(r[8]), spatem_log=int(r[9]), mapem_log=int(r[10]), signiert_log=int(r[11]), sonstige_log=int(r[12]),
                       gespeichert_cam=sv.get("CAM", 0), gespeichert_denm=sv.get("DENM", 0)))
    n = len({f"{x['lat']:.4f},{x['lon']:.4f}" for x in tl if f"{x['lat']:.4f},{x['lon']:.4f}" not in cache})
    print(f"{len(tl)} Empfangsfenster, {n} neue Adressabfragen (~{n * 1.1 / 60:.1f} min)")
    for x in tl:
        x.update(geocode(x["lat"], x["lon"], cache, a.cache))
    cols = ["utc", "lat", "lon", "kmh", "sats", "pakete", "cam_log", "denm_log", "spatem_log", "mapem_log", "signiert_log", "sonstige_log",
            "gespeichert_cam", "gespeichert_denm", "strasse", "hausnummer", "ortsteil", "ort", "plz"]
    with open(os.path.join(a.out, "empfang_timeline.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for x in tl:
            w.writerow({**x, "lat": f"{x['lat']:.5f}", "lon": f"{x['lon']:.5f}"})
    # Abschnitte (Luecke > 30 s trennt)
    seg = []
    for x in tl:
        t = ts(x["utc"])
        if seg and t - seg[-1]["t1"] <= 30:
            s = seg[-1]; s["t1"] = t; s["pakete"] += x["pakete"]; s["fenster"] += 1; s["kmh"].append(x["kmh"])
            s["strassen"][(x["strasse"] or "?")] += 1; s["last"] = x
            s["gcam"] += x["gespeichert_cam"]; s["gdenm"] += x["gespeichert_denm"]; s["son"] += x["sonstige_log"]
        else:
            seg.append(dict(t0=t, t1=t, utc0=x["utc"], pakete=x["pakete"], fenster=1, kmh=[x["kmh"]], strassen=collections.Counter([x["strasse"] or "?"]),
                            first=x, last=x, gcam=x["gespeichert_cam"], gdenm=x["gespeichert_denm"], son=x["sonstige_log"]))
    with open(os.path.join(a.out, "empfang_abschnitte.csv"), "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["von_utc", "bis_utc", "dauer_s", "fenster", "pakete", "davon_sonstige", "gespeichert_cam", "gespeichert_denm", "kmh_median", "strassen", "ortsteil", "ort"])
        for s in seg:
            w.writerow([s["utc0"], s["last"]["utc"], round(s["t1"] - s["t0"]) + 10, s["fenster"], s["pakete"], s["son"], s["gcam"], s["gdenm"],
                        sorted(s["kmh"])[len(s["kmh"]) // 2], " > ".join(k for k, _ in s["strassen"].most_common(4)), s["first"]["ortsteil"], s["first"]["ort"]])
    print(f"{len(seg)} Abschnitte")

    # DENM-Ereignisse mit Adresse (nur ausserhalb Sperrzone)
    den = []
    for s, u, f in fr_keep:
        g = gn.parse_frame(f, S["SEC"])
        if g.msg_type == "DENM" and g.payload:
            try:
                m = S["DENM"].decode("DENM", g.payload)["denm"]
            except Exception:  # noqa: BLE001
                continue
            ep = m["management"]["eventPosition"]; la, lo = ep["latitude"] / 1e7, ep["longitude"] / 1e7
            if inzone(la, lo):
                continue
            k = (m["management"]["actionID"]["originatingStationID"], m["management"]["actionID"]["sequenceNumber"])
            if not any(d["k"] == k for d in den):
                den.append(dict(k=k, lat=la, lon=lo, t=s, ursache=m["situation"]["eventType"]["causeCode"], pakete=0))
            [d for d in den if d["k"] == k][0]["pakete"] += 1
    for d in den:
        d.update(geocode(d["lat"], d["lon"], cache, a.cache))
        d["utc"] = datetime.datetime.fromtimestamp(d["t"], datetime.UTC).strftime("%H:%M:%S")
    json.dump([{k: v for k, v in d.items() if k not in ("k", "t")} for d in den], open(os.path.join(a.out, "denm_ereignisse.json"), "w"), ensure_ascii=False, indent=1)

    # 3. Karte
    trk = [(ts(r[0]), float(r[3]), float(r[4]), sum(int(x) for x in r[7:13])) for r in kept if r[2] == "1" and float(r[3]) != 0]
    # Kartenausschnitt = Empfangsfenster + Rand (nicht die ganze Strecke: so bleiben die Gegenden um Start/Ziel ausserhalb des Bildes)
    lats = [x["lat"] for x in tl] + [d["lat"] for d in den]; lons = [x["lon"] for x in tl] + [d["lon"] for d in den]
    bb = [min(lats) - 0.006, min(lons) - 0.010, max(lats) + 0.006, max(lons) + 0.010]
    inbb = lambda la, lo: bb[0] <= la <= bb[2] and bb[1] <= lo <= bb[3]
    trk = [p for p in trk if inbb(p[1], p[2])]
    pts = [[round(trk[i - 1][1], 5), round(trk[i - 1][2], 5), round(trk[i][1], 5), round(trk[i][2], 5), trk[i][3]] for i in range(1, len(trk)) if trk[i][0] - trk[i - 1][0] <= 30]
    win = [{"lat": round(x["lat"], 5), "lon": round(x["lon"], 5), "t": x["utc"][11:19], "p": x["pakete"], "kmh": x["kmh"],
            "adr": ", ".join(v for v in [(x["strasse"] + (" " + x["hausnummer"] if x["hausnummer"] else "")).strip(), x["ortsteil"], x["ort"]] if v)} for x in tl]
    dn = [{"lat": round(d["lat"], 5), "lon": round(d["lon"], 5), "t": d["utc"], "u": d["ursache"], "n": d["pakete"],
           "adr": ", ".join(v for v in [(d["strasse"] + (" " + d["hausnummer"] if d["hausnummer"] else "")).strip(), d["ortsteil"], d["ort"]] if v)} for d in den]
    if a.html:
        html = HTML.replace("__PTS__", json.dumps(pts)).replace("__WIN__", json.dumps(win, ensure_ascii=False)).replace("__DEN__", json.dumps(dn, ensure_ascii=False)).replace("__BB__", json.dumps(bb))
        open(a.html, "w").write(html)
    if a.png:
        from staticmap import CircleMarker, Line, StaticMap
        import staticmap.staticmap as sm
        m = StaticMap(1100, 900, url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png", headers={"User-Agent": UA})
        col = lambda p: "#d9d9d9" if p == 0 else "#2a9d6f" if p < 15 else "#e0a82a" if p < 40 else "#d9382a"
        for i in range(1, len(trk)):
            if trk[i][0] - trk[i - 1][0] <= 30:
                m.add_line(Line([(trk[i - 1][2], trk[i - 1][1]), (trk[i][2], trk[i][1])], col(trk[i][3]), 4))
        for d in den:
            m.add_marker(CircleMarker((d["lon"], d["lat"]), "#000000", 16)); m.add_marker(CircleMarker((d["lon"], d["lat"]), "#ff6a00", 11))
        cx, cy = (bb[1] + bb[3]) / 2, (bb[0] + bb[2]) / 2
        z = 16
        while z > 9:
            x0 = (bb[1] + 180) / 360 * 2 ** z; x1 = (bb[3] + 180) / 360 * 2 ** z
            yy = lambda la: (1 - math.log(math.tan(math.radians(la)) + 1 / math.cos(math.radians(la))) / math.pi) / 2 * 2 ** z
            if (x1 - x0) * 256 <= 1100 and (yy(bb[0]) - yy(bb[2])) * 256 <= 880:
                break
            z -= 1
        img = m.render(zoom=z, center=(cx, cy))
        from PIL import ImageDraw
        dr = ImageDraw.Draw(img)
        dr.rectangle([0, 880, 1100, 900], fill="white")
        dr.text((6, 884), "Karte (c) OpenStreetMap-Mitwirkende (ODbL) | Spur: gruen 1-14, gelb 15-39, rot >=40 Pakete je 10 s, grau keine | orange: DENM | Start/Ziel-Sperrzone entfernt", fill="black")
        img.save(a.png)
    print("fertig")


HTML = """<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Karte Testfahrt 1</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.css">
<style>html,body{height:100%;margin:0;font-family:system-ui,sans-serif}#m{height:100%}
.leg{background:#fffd;padding:8px 10px;border-radius:6px;font-size:13px;line-height:1.5}.leg i{display:inline-block;width:12px;height:12px;margin-right:6px;border-radius:2px}
@media(prefers-color-scheme:dark){.leg{background:#222d;color:#eee}}</style></head><body><div id="m"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js"></script>
<script>
const PTS=__PTS__, WIN=__WIN__, DEN=__DEN__, BB=__BB__;
const map=L.map('m',{maxBounds:[[BB[0],BB[1]],[BB[2],BB[3]]],maxBoundsViscosity:1,minZoom:11}).fitBounds([[BB[0],BB[1]],[BB[2],BB[3]]]);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>-Mitwirkende'}).addTo(map);
const col=p=>p==0?'#999':p<15?'#2a9d6f':p<40?'#e0a82a':'#d9382a';
PTS.forEach(s=>L.polyline([[s[0],s[1]],[s[2],s[3]]],{color:col(s[4]),weight:4,opacity:.9}).addTo(map));
WIN.forEach(w=>L.circleMarker([w.lat,w.lon],{radius:4+Math.min(8,w.p/8),color:'#000',weight:1,fillColor:col(w.p),fillOpacity:.9}).bindPopup('<b>'+w.t+' UTC</b><br>'+w.p+' Pakete in 10 s · '+w.kmh+' km/h<br>'+(w.adr||'')).addTo(map));
DEN.forEach(d=>L.marker([d.lat,d.lon]).bindPopup('<b>DENM Ursache '+d.u+'</b> ('+d.n+' Pakete)<br>'+d.t+' UTC<br>'+d.adr).addTo(map));
const lg=L.control({position:'bottomleft'});lg.onAdd=()=>{const d=L.DomUtil.create('div','leg');d.innerHTML='<b>Pakete je 10 s</b><br><i style="background:#999"></i>0<br><i style="background:#2a9d6f"></i>1–14<br><i style="background:#e0a82a"></i>15–39<br><i style="background:#d9382a"></i>≥ 40<br>Marker: Gefahrenmeldung (DENM)<br><small>Strecke ohne Start/Ziel (Sperrzone)</small>';return d};lg.addTo(map);
</script></body></html>
"""

if __name__ == "__main__":
    main()
