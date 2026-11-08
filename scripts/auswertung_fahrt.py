#!/usr/bin/env python3
"""Auswertung einer Testfahrt: log.csv + frames.bin (vom Auto-Knoten, Statusseite http://192.168.4.1) -> Kennzahlen + Bilder.

Datenschutz: Alles, was in der Naehe von Start und Ziel liegt (--trim-km, Standard 5 km), wird aus den Ausgaben
entfernt. Bilder verwenden relative Koordinaten (km zum Mittelpunkt der Reststrecke), keine Lat/Lon-Werte.

Aufruf (im venv mit decoder/requirements.txt + matplotlib):
    python scripts/auswertung_fahrt.py DATENORDNER AUSGABEORDNER [--trim-km 5]
"""
import argparse, bisect, collections, csv, datetime, hashlib, json, math, os, statistics as st, struct, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "decoder"))
from its_decoder import gn, schemas  # noqa: E402

ITS_EPOCH = 1072915200  # 2004-01-01 UTC
LIGHTS = ["Abblendlicht", "Fernlicht", "Blinker links", "Blinker rechts", "Tagfahrlicht", "Rückfahrlicht", "Nebellicht", "Standlicht"]


def dist_m(a, b, c, d):
    x = math.radians(d - b) * math.cos(math.radians((a + c) / 2))
    y = math.radians(c - a)
    return 6371000 * math.hypot(x, y)


def read_frames(path):
    d = open(path, "rb").read()
    p = 0
    while p + 14 <= len(d) and d[p:p + 4] == b"ITS5":
        s, u, l = struct.unpack("<IIH", d[p + 4:p + 14])
        yield s + u / 1e6, d[p + 14:p + 14 + l]
        p += 14 + l


def decode(S, ts, f):
    r = {"ts": ts, "len": len(f), "mac": f[10:16].hex(), "qos": f[24:26].hex() if f[0] & 0x80 else ""}
    hdr = 26 if f[0] & 0x80 else 24
    r["basic"] = f[hdr + 8:hdr + 12].hex()
    g = gn.parse_frame(f, S["SEC"])
    r["secured"] = g.secured
    r["type"] = g.msg_type
    r["gn_addr"] = g.gn_addr
    if g.secured:
        try:
            m = S["SEC"].decode("Ieee1609Dot2Data", f[hdr + 12:])
            r["sig"] = m["content"][1]
        except Exception:  # noqa: BLE001
            pass
    if g.msg_type in S and g.payload:
        try:
            r["msg"] = S[g.msg_type].decode(g.msg_type, g.payload)
        except Exception:  # noqa: BLE001
            pass
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data"); ap.add_argument("out")
    ap.add_argument("--trim-km", type=float, default=5.0)
    ap.add_argument("--pcap", help="Rohframes zusaetzlich als pcap (Wireshark, LINKTYPE 802.11) schreiben - enthaelt Positionen, nicht veroeffentlichen!")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.pcap:
        with open(a.pcap, "wb") as w:
            w.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 105))
            for ts, f in read_frames(os.path.join(a.data, "frames.bin")):
                w.write(struct.pack("<IIII", int(ts), int((ts % 1) * 1e6), len(f), len(f)) + f)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    C1, C2, C3 = "#2a6fdb", "#e0642a", "#2a9d6f"

    # ---------- log.csv ----------
    rows = [r for r in csv.reader(open(os.path.join(a.data, "log.csv"))) if len(r) == 13 and r[0]]
    fix = [(datetime.datetime.fromisoformat(r[0].replace("Z", "+00:00")).timestamp(), float(r[3]), float(r[4]), int(r[5]),
            sum(int(x) for x in r[7:13])) for r in rows if r[2] == "1" and float(r[3]) != 0]
    if not fix:
        sys.exit("keine GPS-Fixe im Log")
    h0, h1 = fix[0], fix[-1]
    trim = a.trim_km * 1000

    def keep(lat, lon):
        return dist_m(lat, lon, h0[1], h0[2]) > trim and dist_m(lat, lon, h1[1], h1[2]) > trim
    fk = [p for p in fix if keep(p[1], p[2])]
    lat0 = st.mean(p[1] for p in fk); lon0 = st.mean(p[2] for p in fk)
    xy = lambda lat, lon: ((lon - lon0) * 111.32 * math.cos(math.radians(lat0)), (lat - lat0) * 110.57)
    T = [p[0] for p in fix]

    def own(t):
        i = bisect.bisect(T, t)
        if i == 0 or i >= len(T) or T[i] - T[i - 1] > 30:
            return None
        w = (t - T[i - 1]) / (T[i] - T[i - 1])
        return fix[i - 1][1] + w * (fix[i][1] - fix[i - 1][1]), fix[i - 1][2] + w * (fix[i][2] - fix[i - 1][2])

    # ---------- frames.bin ----------
    S = schemas.load()
    recs = []
    for ts, f in read_frames(os.path.join(a.data, "frames.bin")):
        r = decode(S, ts, f)
        o = own(ts)
        r["own"] = o
        r["ok"] = bool(o) and keep(*o)  # darf veroeffentlicht werden
        recs.append(r)
    res = {"trim_km": a.trim_km}
    res["log"] = {"zeilen": len(rows), "dauer_h": round((fix[-1][0] - fix[0][0]) / 3600, 2), "max_kmh": max(p[3] for p in fix)}
    dec = [r for r in recs if "msg" in r]
    res["frames"] = {"gesamt": len(recs), "decodiert": len(dec), "signiert": sum(1 for r in recs if r["secured"]),
                     "typen": dict(collections.Counter(r["type"] for r in recs))}

    # ---------- Zertifikate ----------
    sec = S["SEC"]
    certs = {}
    for r in dec:
        sg = r["sig"]["signer"]
        if sg[0] == "certificate":
            c = sg[1][0]
            h = hashlib.sha256(sec.encode("Certificate", c)).digest()[-8:].hex()
            certs[h] = c; r["ath"] = h
        else:
            r["ath"] = sg[1].hex()
    aa_of = {h: c["issuer"][1].hex() for h, c in certs.items()}
    dig = [r for r in dec if r["sig"]["signer"][0] == "digest"]
    res["zertifikate"] = {
        "eindeutig": len(certs), "digest_pakete": len(dig), "digest_zuordenbar": sum(1 for r in dig if r["ath"] in aa_of),
        "aussteller": dict(collections.Counter(aa_of.values())),
        "gueltigkeit_h": dict(collections.Counter(c["toBeSigned"]["validityPeriod"]["duration"][1] for c in certs.values())),
        "beginn_tage": dict(collections.Counter((datetime.datetime.fromtimestamp(ITS_EPOCH + c["toBeSigned"]["validityPeriod"]["start"], datetime.UTC)).strftime("%Y-%m-%d") for c in certs.values())),
        "ssp": sorted({f"{p['psid']}:{p['ssp'][1].hex()}" for c in certs.values() for p in c["toBeSigned"]["appPermissions"]}),
        "mit_region": sum(1 for c in certs.values() if "region" in c["toBeSigned"]),
    }
    lt = [r["ts"] - (r["sig"]["tbsData"]["headerInfo"]["generationTime"] / 1e6 + ITS_EPOCH) for r in dec]
    res["zeit"] = {"empfang_minus_generation_median_s": round(st.median(lt), 1), "min": round(min(lt), 1), "max": round(max(lt), 1)}

    # ---------- CAM ----------
    cams = [r for r in dec if r["type"] == "CAM"]
    hf = lambda r: r["msg"]["cam"]["camParameters"]["highFrequencyContainer"][1]
    bc = lambda r: r["msg"]["cam"]["camParameters"]["basicContainer"]
    lfc = lambda r: r["msg"]["cam"]["camParameters"].get("lowFrequencyContainer")
    ids = {r["msg"]["header"]["stationID"] for r in cams}
    clus = collections.defaultdict(set)
    for r in cams:
        h = hf(r)
        clus[r["msg"]["header"]["stationID"]].add((h["vehicleLength"]["vehicleLengthValue"], h["vehicleWidth"], h["vehicleLength"]["vehicleLengthConfidenceIndication"]))
    aa_cl = collections.defaultdict(collections.Counter)
    for r in cams:
        aa = aa_of.get(r["ath"])
        if aa:
            aa_cl[aa][hf(r)["vehicleLength"]["vehicleLengthConfidenceIndication"]] += 1
    lights = collections.Counter()
    for r in cams:
        L = lfc(r)
        if L:
            b = L[1]["exteriorLights"][0][0]
            lights[",".join(n for i, n in enumerate(LIGHTS) if b & (0x80 >> i)) or "keine"] += 1
    sp = [hf(r)["speed"]["speedValue"] * 0.036 for r in cams]
    res["cam"] = {"pakete": len(cams), "stationen": len(ids), "stationstyp": dict(collections.Counter(bc(r)["stationType"] for r in cams)),
                  "kmh_median": round(st.median(sp)), "kmh_max": round(max(sp)), "stehend": sum(1 for x in sp if x < 1),
                  "lf_container": sum(1 for r in cams if lfc(r)), "aussteller_vs_laengenkonfidenz": {k: dict(v) for k, v in aa_cl.items()},
                  "aussenlichter": dict(lights), "laenge_dm": dict(collections.Counter(h[0] for v in clus.values() for h in v)),
                  "pathhistory_median": st.median(len(lfc(r)[1]["pathHistory"]) for r in cams if lfc(r))}
    macs = collections.defaultdict(set)
    for r in dec:
        macs[r["mac"]].add(r["msg"]["header"]["stationID"])
    res["kennungen"] = {"macs": len(macs), "mac_zufall": sum(1 for m in macs if int(m[:2], 16) & 2),
                        "mac_mit_mehreren_ids": sum(1 for v in macs.values() if len(v) > 1),
                        "mac_gleich_gn_adresse": sum(1 for r in dec if r["gn_addr"][4:] == r["mac"]), "von": len(dec),
                        "basic_header": dict(collections.Counter(r["basic"] for r in recs))}
    # Reichweite
    ds = []
    for r in cams:
        if r["ok"]:
            b = bc(r)["referencePosition"]
            r["dist"] = dist_m(r["own"][0], r["own"][1], b["latitude"] / 1e7, b["longitude"] / 1e7); ds.append(r["dist"])
    if ds:
        ds.sort()
        res["reichweite_m"] = {"n": len(ds), "median": round(st.median(ds)), "p90": round(ds[int(.9 * len(ds))]), "p99": round(ds[int(.99 * len(ds))]), "max": round(ds[-1])}
    # Verkettung ueber Position/Zeit
    tr = collections.defaultdict(list)
    for r in cams:
        tr[r["msg"]["header"]["stationID"]].append(r)
    for v in tr.values():
        v.sort(key=lambda r: r["ts"])
    ll = lambda r: (bc(r)["referencePosition"]["latitude"] / 1e7, bc(r)["referencePosition"]["longitude"] / 1e7)
    links = []
    for x, vx in tr.items():
        for y, vy in tr.items():
            if x == y:
                continue
            dt = vy[0]["ts"] - vx[-1]["ts"]
            if 0 < dt <= 20 and clus[x] & clus[y] and dist_m(*ll(vx[-1]), *ll(vy[0])) <= (hf(vx[-1])["speed"]["speedValue"] / 100 + 2) * dt + 30:
                links.append((x, y))
    res["verkettung"] = {"stationen": len(tr), "kandidaten": len(links),
                         "beobachtung_s_median": round(st.median(v[-1]["ts"] - v[0]["ts"] for v in tr.values()), 1),
                         "beobachtung_s_max": round(max(v[-1]["ts"] - v[0]["ts"] for v in tr.values()))}

    # ---------- DENM ----------
    den = [r for r in dec if r["type"] == "DENM"]
    ev = collections.OrderedDict()
    for r in den:
        m = r["msg"]["denm"]; ak = m["management"]["actionID"]
        ev.setdefault((ak["originatingStationID"], ak["sequenceNumber"]), []).append(r)
    evs = []
    for k, v in ev.items():
        m = v[0]["msg"]["denm"]; ep = m["management"]["eventPosition"]
        pub = keep(ep["latitude"] / 1e7, ep["longitude"] / 1e7)
        e = {"ursache": m["situation"]["eventType"]["causeCode"], "unterursache": m["situation"]["eventType"]["subCauseCode"],
             "qualitaet": m["situation"]["informationQuality"], "relevanz": m["management"]["relevanceDistance"],
             "richtung": m["management"]["relevanceTrafficDirection"], "gueltig_s": m["management"]["validityDuration"],
             "pakete": len(v), "dauer_s": round(v[-1]["ts"] - v[0]["ts"]), "spur_punkte": [len(t) for t in m["location"].get("traces", [])],
             "ereignisgeschw_kmh": round(m["location"].get("eventSpeed", {}).get("speedValue", 0) * 0.036), "alacarte": list(m.get("alacarte", {}))}
        if pub:
            e["xy_km"] = [round(c, 2) for c in xy(ep["latitude"] / 1e7, ep["longitude"] / 1e7)]
        evs.append(e)
    res["denm"] = {"pakete": len(den), "ereignisse": evs, "innerhalb_sperrzone": sum(1 for e in evs if "xy_km" not in e)}
    json.dump(res, open(os.path.join(a.out, "auswertung.json"), "w"), indent=1, ensure_ascii=False)

    # ---------- Bilder ----------
    # 1 Strecke mit Paketdichte
    fig, ax = plt.subplots(figsize=(6.4, 5.4))
    xs, ys = zip(*[xy(p[1], p[2]) for p in fk])
    sc = ax.scatter(xs, ys, c=[p[4] for p in fk], s=10, cmap="viridis_r", vmin=0, vmax=60)
    for e in evs:
        if "xy_km" in e:
            ax.scatter(*e["xy_km"], marker="^", s=70, c=C2, edgecolor="k", zorder=5)
    ax.scatter([], [], marker="^", s=70, c=C2, edgecolor="k", label="Gefahrenmeldung (DENM)")
    plt.colorbar(sc, label="Pakete je 10 s (alle Typen)")
    ax.set_aspect("equal"); ax.set_xlabel("km (relativ)"); ax.set_ylabel("km (relativ)")
    ax.set_title("Strecke ohne Start/Ziel (Sperrzone %.0f km), relative Koordinaten" % a.trim_km, fontsize=9)
    ax.legend(loc="lower left", fontsize=8); fig.tight_layout(); fig.savefig(os.path.join(a.out, "strecke.png"), dpi=130); plt.close(fig)
    # 2 Reichweite
    if ds:
        fig, ax = plt.subplots(figsize=(6.4, 3.4))
        ax.hist(ds, bins=range(0, 1000, 50), color=C1)
        ax.axvline(st.median(ds), color=C2, ls="--"); ax.text(st.median(ds) + 10, ax.get_ylim()[1] * .9, "Median %d m" % st.median(ds), color=C2)
        ax.set_xlabel("Abstand Sender–Empfänger [m]"); ax.set_ylabel("CAM-Pakete"); ax.set_title("Reichweite der PCB-Antenne im Auto")
        fig.tight_layout(); fig.savefig(os.path.join(a.out, "reichweite.png"), dpi=130); plt.close(fig)
    # 3 Geschwindigkeit
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    ax.hist(sp, bins=range(0, 130, 5), color=C3); ax.set_xlabel("Geschwindigkeit laut CAM [km/h]"); ax.set_ylabel("CAM-Pakete")
    ax.set_title("Wie schnell waren die gehörten Fahrzeuge?"); fig.tight_layout(); fig.savefig(os.path.join(a.out, "geschwindigkeit.png"), dpi=130); plt.close(fig)
    # 4 Pakete je Zeit (nur Fahrtzeitraum, Uhrzeit relativ)
    t0 = fk[0][0]
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.bar([(p[0] - t0) / 60 for p in fk], [p[4] for p in fk], width=0.2, color=C1)
    ax.set_xlabel("Minuten seit Beginn der Reststrecke"); ax.set_ylabel("Pakete je 10 s"); ax.set_title("Empfang im Fahrtverlauf")
    fig.tight_layout(); fig.savefig(os.path.join(a.out, "verlauf.png"), dpi=130); plt.close(fig)
    # 5 Pannenfahrzeug: Abstand und Warnblinker ueber Zeit
    pan = [e for e in den if e["msg"]["denm"]["situation"]["eventType"]["causeCode"] == 94]
    if pan:
        sid = pan[0]["msg"]["header"]["stationID"]
        pc = [r for r in cams if r["msg"]["header"]["stationID"] == sid and "dist" in r]
        if pc:
            t0 = min(r["ts"] for r in pc + pan)
            fig, ax = plt.subplots(figsize=(7, 3.2))
            haz = [bool(lfc(r)) and lfc(r)[1]["exteriorLights"][0][0] & 0x30 == 0x30 for r in pc]
            ax.scatter([r["ts"] - t0 for r, h in zip(pc, haz) if not h], [r["dist"] for r, h in zip(pc, haz) if not h], c=C1, label="CAM ohne Warnblinker")
            ax.scatter([r["ts"] - t0 for r, h in zip(pc, haz) if h], [r["dist"] for r, h in zip(pc, haz) if h], c=C2, marker="D", label="CAM mit Warnblinker")
            for r in pan:
                ax.axvline(r["ts"] - t0, color="#aaa", lw=.6)
            ax.plot([], [], color="#aaa", label="DENM „stehendes Fahrzeug“ (Ursache 94)")
            ax.set_xlabel("Sekunden"); ax.set_ylabel("Abstand zu meinem Auto [m]"); ax.legend(fontsize=8); ax.set_title("Pannenfahrzeug: CAM und DENM im Vergleich")
            fig.tight_layout(); fig.savefig(os.path.join(a.out, "pannenfahrzeug.png"), dpi=130); plt.close(fig)
    print(json.dumps(res, indent=1, ensure_ascii=False)[:6000])


if __name__ == "__main__":
    main()
