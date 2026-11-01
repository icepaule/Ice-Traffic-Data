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
        self.recent = deque(maxlen=200)
        self.rate = deque(maxlen=600)  # Ankunftszeiten
        self.retention = retention_s
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.execute("create table if not exists msgs(ts real, node text, type text, station int, body text)")
        self.db.execute("create index if not exists i_ts on msgs(ts)")

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
            }

    def prune(self):
        with self.lock:
            self.db.execute("delete from msgs where ts < ?", (time.time() - self.retention,))
            self.db.commit()
