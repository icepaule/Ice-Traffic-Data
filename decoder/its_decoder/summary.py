"""Kompakte, kartentaugliche Zusammenfassungen der dekodierten Nachrichten."""


def _g(d, *path, default=None):
    for k in path:
        if isinstance(d, dict) and k in d:
            d = d[k]
        else:
            return default
    return d


def _sid(m):
    h = m["header"]
    return h.get("stationID", h.get("stationId"))


def _deg(v):
    return None if v in (None, 900000001, 1800000001) else v / 1e7


def cam(m):
    c = m["cam"]["camParameters"]
    pos = _g(c, "basicContainer", "referencePosition", default={})
    hf = _g(c, "highFrequencyContainer", default=("", {}))[1]
    return {
        "station": _sid(m),
        "stype": _g(c, "basicContainer", "stationType"),
        "lat": _deg(pos.get("latitude")), "lon": _deg(pos.get("longitude")),
        "speed": (_g(hf, "speed", "speedValue", default=16383) or 0) * 0.01,
        "heading": (_g(hf, "heading", "headingValue", default=0) or 0) * 0.1,
    }


def denm(m):
    d = m["denm"]
    ev = _g(d, "situation", "eventType", default={})
    pos = _g(d, "management", "eventPosition", default={})
    return {
        "station": _sid(m),
        "action": _g(d, "management", "actionID"),
        "cause": ev.get("causeCode"), "subcause": ev.get("subCauseCode"),
        "lat": _deg(pos.get("latitude")), "lon": _deg(pos.get("longitude")),
        "validity_s": _g(d, "management", "validityDuration", default=600),
    }


def spatem(m):
    out = []
    for i in _g(m, "spat", "intersections", default=[]):
        groups = []
        for s in i.get("states", []):
            sts = s.get("state-time-speed", [{}])
            ev = sts[0].get("eventState") if sts else None
            groups.append({"sg": s.get("signalGroup"), "state": ev,
                           "min_end": _g(sts[0], "timing", "minEndTime") if sts else None})
        st = i.get("status")
        st = st[0].hex() if isinstance(st, tuple) and st and isinstance(st[0], (bytes, bytearray)) else str(st)
        out.append({"id": _g(i, "id", "id"), "status": st, "groups": groups})
    return {"station": _sid(m), "intersections": out}


def mapem(m):
    out = []
    for i in _g(m, "map", "intersections", default=[]):
        ref = i.get("refPoint", {})
        out.append({"id": _g(i, "id", "id"), "name": i.get("name"),
                    "lat": (ref.get("lat") or 0) / 1e7, "lon": (ref.get("long") or 0) / 1e7,
                    "lanes": len(i.get("laneSet", []))})
    return {"station": _sid(m), "intersections": out}


SUMMARIZERS = {"CAM": cam, "DENM": denm, "SPATEM": spatem, "MAPEM": mapem}
