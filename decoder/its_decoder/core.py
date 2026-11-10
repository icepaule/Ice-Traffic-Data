"""Verarbeitung: Frame -> Typ -> ASN.1 -> Summary -> Zustand + SQLite."""
import json
import sqlite3
import threading
import time
from collections import Counter, deque

from . import gn, summary


def _jsonable(o):
    if isinstance(o, (bytes, bytearray)):
        return o.hex()
    if isinstance(o, tuple) and len(o) == 2 and isinstance(o[0], (bytes, bytearray)):
        return o[0].hex()
    if isinstance(o, tuple):
        return [_jsonable(x) for x in o]
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_jsonable(x) for x in o]
    return o


class Core:
    def __init__(self, schemas, db_path=":memory:", retention_s=7 * 86400):
        self.sch = schemas
        self.lock = threading.Lock()
        self.stats = Counter()
        self.stations = {}   # station id -> letzte CAM
        self.denms = {}      # (station, action) -> DENM
        self.signals = {}    # intersection id -> SPAT
        self.maps = {}       # intersection id -> MAP
        self.gn_seen = {}    # gn addr -> letzte Position (auch ohne CAM)
        self.nodes = {}      # node -> (status, ts) aus its/<node>/status
        self.sniffer = {}    # node -> letzte Sniffer-Meldung aus its/<node>/stats (Zaehler, Feldstaerke)
        self.recent = deque(maxlen=200)
        self.rate = deque(maxlen=600)  # Ankunftszeiten
        self.retention = retention_s
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.execute("create table if not exists msgs(ts real, node text, type text, station int, body text)")
        self.db.execute("create index if not exists i_ts on msgs(ts)")
        self.db.execute("create table if not exists car(ts real, fcnt int, lat real, lon real, state text)")
        self.db.execute("create index if not exists i_car_ts on car(ts)")

    def feed(self, node, frame, now=None):
        now = now or time.time()
        with self.lock:
            self.stats["frames"] += 1
            self.rate.append(now)
            g = gn.parse_frame(frame, self.sch.get("SEC"))
            if g.secured:
                self.stats["secured"] += 1
            if g.lat is not None and g.gn_addr:
                self.gn_seen[g.gn_addr] = {"lat": g.lat, "lon": g.lon, "ts": now, "mac": g.src_mac}
            t = g.msg_type
            if not t or not g.payload:
                self.stats["undecoded"] += 1
                self.recent.appendleft({"ts": now, "type": t or "?", "note": "; ".join(g.notes)})
                return None
            self.stats[t] += 1
            if t not in self.sch or t not in summary.SUMMARIZERS:
                return None
            try:
                msg = self.sch[t].decode(t, g.payload)
            except Exception as e:  # noqa: BLE001
                self.stats["decode_error_" + t] += 1
                self.recent.appendleft({"ts": now, "type": t, "note": f"ASN.1-Fehler: {str(e)[:80]}"})
                return None
            s = summary.SUMMARIZERS[t](msg)
            s.update(ts=now, node=node, secured=g.secured)
            self._store(t, s)
            self.db.execute("insert into msgs values(?,?,?,?,?)",
                            (now, node, t, s.get("station"), json.dumps(_jsonable(msg))))
            self.recent.appendleft({"ts": now, "type": t, "station": s.get("station")})
            return t, s

    def set_node_status(self, node, payload):
        with self.lock:
            self.nodes[node] = (payload, time.time())

    def set_node_stats(self, node, payload):
        """Sniffer-Meldung der Bridge (JSON): rx_err, unicast, dropped (kumulativ), pkts, rssi, rssi_min, rssi_max, noise je 10 s.
        Die aeltere Temperatur-Meldung ({"temp": ..}) wird ignoriert."""
        try:
            d = json.loads(payload)
        except ValueError:
            return
        if not isinstance(d, dict) or "rx_err" not in d:
            return
        keep = ("rx_err", "unicast", "dropped", "pkts", "rssi", "rssi_min", "rssi_max", "noise")
        now = time.time()
        new = {k: d[k] for k in keep if isinstance(d.get(k), (int, float))}
        with self.lock:
            old = self.sniffer.get(node, {})
            rk = ("rssi", "rssi_min", "rssi_max", "noise")
            if "rssi" in new:  # Feldstaerke nur in Fenstern mit Paketen: sonst letzten Wert behalten (mit eigenem Zeitstempel)
                new["rssi_ts"] = now
            else:
                new.update({k: old[k] for k in rk + ("rssi_ts",) if k in old})
            self.sniffer[node] = {**new, "ts": now}

    def add_car_uplink(self, state, loc, ts=None):
        """LoRaWAN-Uplink des Auto-Knotens (aus lora.handle_event) speichern: Beacon, Position, Zaehler."""
        ts = ts or time.time()
        with self.lock:
            self.db.execute("insert into car values(?,?,?,?,?)",
                            (ts, state.get("fcnt"), loc["latitude"] if loc else None, loc["longitude"] if loc else None,
                             json.dumps(state)))
            self.db.commit()

    CAR_BEACON_S = 60  # Uplink-Intervall des Auto-Knotens (Lebenszeichen)

    def _car_snapshot(self, now, window=86400, max_pts=600):
        rows = self.db.execute("select ts,fcnt,lat,lon,state from car where ts > ? order by ts", (now - window,)).fetchall()
        if not rows:
            return None
        last = rows[-1]
        st = json.loads(last[4])
        age = now - last[0]
        # Beacon: erwartet alle 60 s; verpasste Uplinks aus Luecken im Frame-Zaehler (Zaehlerruecksprung = Neustart, nicht gezaehlt)
        missed, prev = 0, None
        sent_b = rx = up = 0
        tot = {k: 0 for k in ("cam", "denm", "spatem", "mapem", "secured", "other", "sniffer_rx_err", "sniffer_unicast", "sniffer_dropped", "frames_lost")}
        for ts, fc, _la, _lo, js in rows:
            d = json.loads(js)
            up += 1
            sent_b += d.get("bytes") or 0
            for k in tot:
                v = d.get(k)
                if isinstance(v, (int, float)):
                    tot[k] += v
            if prev is not None and fc is not None and 1 < fc - prev < 1000:
                missed += fc - prev - 1
            prev = fc if fc is not None else prev
        rx = sum(tot[k] for k in ("cam", "denm", "spatem", "mapem", "other"))
        pts = [[r[2], r[3], r[0]] for r in rows if r[2] is not None]
        step = max(1, len(pts) // max_pts)
        fix = [r for r in rows if r[2] is not None]
        pos = {"lat": fix[-1][2], "lon": fix[-1][3], "age": round(now - fix[-1][0], 1)} if fix else None
        status = "online" if age < 2.5 * self.CAR_BEACON_S else "ueberfaellig" if age < 10 * self.CAR_BEACON_S else "offline"
        return {
            "status": status, "age": round(age, 1), "interval_s": self.CAR_BEACON_S, "last_ts": last[0], "fcnt": last[1],
            "rssi": st.get("rssi"), "snr": st.get("snr"), "sf": st.get("sf"), "satellites": st.get("satellites"),
            "gps_fix": st.get("gps_fix"), "speed_kmh": st.get("speed_kmh"), "uptime_min": st.get("uptime_min"),
            "bridge_alive": st.get("bridge_alive"), "pos": pos,
            "track": pts[::step] + ([pts[-1]] if pts and (len(pts) - 1) % step else []),
            "window_h": window // 3600,
            "sent": {"uplinks": up, "payload_bytes": sent_b, "missed": missed},
            "received": {"frames": int(rx), **{k: int(tot[k]) for k in ("cam", "denm", "spatem", "mapem", "other", "secured", "sniffer_rx_err", "sniffer_unicast", "sniffer_dropped", "frames_lost")}},
            "last": {k: st.get(k) for k in ("cam", "denm", "spatem", "mapem", "other", "sniffer_rssi_avg", "sniffer_rssi_max", "sniffer_rx_err")},
        }

    def node_online(self):
        with self.lock:
            return any(v[0] == "online" for v in self.nodes.values())

    def _store(self, t, s):
        if t == "CAM":
            self.stations[s["station"]] = s
        elif t == "DENM":
            self.denms[(s["station"], json.dumps(s["action"], default=str))] = s
        elif t == "SPATEM":
            for i in s["intersections"]:
                self.signals[i["id"]] = {**i, "ts": s["ts"]}
        elif t == "MAPEM":
            for i in s["intersections"]:
                self.maps[i["id"]] = {**i, "ts": s["ts"]}

    def snapshot(self, max_age=120):
        now = time.time()
        with self.lock:
            fresh = lambda d: {k: v for k, v in d.items() if now - v["ts"] < max_age}  # noqa: E731
            r = [t for t in self.rate if now - t < 60]
            return {
                "now": now, "stats": dict(self.stats), "pkts_per_min": len(r),
                "stations": list(fresh(self.stations).values()),
                "denms": list(fresh(self.denms).values()),
                "signals": list(self.signals.values()),
                "maps": list(self.maps.values()),
                "gn": list(fresh(self.gn_seen).values()),
                "recent": list(self.recent)[:30],
                "car": self._car_snapshot(now),
                "sniffer": {k: {**v, "age": round(now - v["ts"], 1), **({"rssi_age": round(now - v["rssi_ts"], 1)} if "rssi_ts" in v else {})} for k, v in self.sniffer.items()},
            }

    def prune(self):
        with self.lock:
            self.db.execute("delete from msgs where ts < ?", (time.time() - self.retention,))
            self.db.execute("delete from car where ts < ?", (time.time() - self.retention,))
            self.db.commit()
