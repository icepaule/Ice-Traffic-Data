"""Auto-Knoten ueber LoRaWAN: ChirpStack-Uplink-Events -> Home-Assistant-Entities.
ChirpStack decodiert die Nutzlast (v1 25 Byte, v2 36 Byte mit Funkstrecke) (firmware/lora-car-node/chirpstack-codec.js) und liefert sie als 'object'."""
import base64
import json
import datetime as _dt

APP_NAME = "IceTraffic"
BASE = "ice_traffic/car"
DEV = {"identifiers": ["ice_traffic_car"], "name": "Ice-Traffic-Data Auto-Knoten", "manufacturer": "DIY",
       "model": "XIAO ESP32S3 + Wio-SX1262"}
SENSORS = [  # key, Name, Einheit, Icon
    ("cam", "CAM (letztes Intervall)", None, "mdi:car-connected"),
    ("denm", "DENM (letztes Intervall)", None, "mdi:alert"),
    ("spatem", "SPATEM (letztes Intervall)", None, "mdi:traffic-light"),
    ("mapem", "MAPEM (letztes Intervall)", None, "mdi:map-marker-path"),
    ("secured", "Signierte Pakete (letztes Intervall)", None, "mdi:shield-key"),
    ("speed_kmh", "Geschwindigkeit", "km/h", "mdi:speedometer"),
    ("satellites", "GNSS-Satelliten", None, "mdi:satellite-variant"),
    ("sniffer_rssi_avg", "ITS-G5 Feldstärke Mittel (letztes Intervall)", "dBm", "mdi:signal"),
    ("sniffer_rssi_max", "ITS-G5 Feldstärke max (letztes Intervall)", "dBm", "mdi:signal-cellular-3"),
    ("sniffer_rx_err", "Sniffer Fehlerpakete (letztes Intervall)", None, "mdi:alert-circle-outline"),
    ("sniffer_unicast", "Sniffer Unicast-Pakete (letztes Intervall)", None, "mdi:account-arrow-right"),
    ("sniffer_dropped", "Sniffer verworfen (letztes Intervall)", None, "mdi:tray-remove"),
    ("frames_lost", "Pakete nicht gespeichert (letztes Intervall)", None, "mdi:database-remove"),
    ("rssi", "LoRa RSSI", "dBm", "mdi:signal"),
    ("snr", "LoRa SNR", "dB", "mdi:signal-variant"),
]


def handle_event(payload: bytes):
    """Gibt (state, location|None) zurueck oder None, wenn das Event nicht zum Auto-Knoten gehoert."""
    e = json.loads(payload.decode())
    if (e.get("deviceInfo") or {}).get("applicationName") != APP_NAME:
        return None
    obj = e.get("object")
    if not isinstance(obj, dict):
        return None
    rx = (e.get("rxInfo") or [{}])[0]
    state = {k: obj.get(k) for k in ("cam", "denm", "spatem", "mapem", "secured", "other", "speed_kmh", "satellites",
                                     "gps_fix", "denm_new", "uptime_min", "sniffer_rssi_avg", "sniffer_rssi_min",
                                     "sniffer_rssi_max", "sniffer_rx_err", "sniffer_unicast", "sniffer_dropped", "frames_lost")}
    state.update(rssi=rx.get("rssi"), snr=rx.get("snr"), time=e.get("time"), fcnt=e.get("fCnt"))
    try:
        state["bytes"] = len(base64.b64decode(e.get("data") or ""))
    except ValueError:
        state["bytes"] = None
    state["sf"] = (((e.get("txInfo") or {}).get("modulation") or {}).get("lora") or {}).get("spreadingFactor")
    state["bridge_alive"] = obj.get("bridge_alive")
    loc = None
    if obj.get("gps_fix") and obj.get("latitude") is not None:
        loc = {"latitude": obj["latitude"], "longitude": obj["longitude"], "gps_accuracy": 25}
    return state, loc


def discovery_messages():
    msgs = []
    for key, name, unit, icon in SENSORS:
        cfg = {"name": name, "unique_id": f"ice_traffic_car_{key}", "object_id": f"ice_traffic_car_{key}",
               "state_topic": f"{BASE}/state", "value_template": "{{ value_json.%s }}" % key, "icon": icon,
               "state_class": "measurement", "expire_after": 900, "device": DEV}
        if unit:
            cfg["unit_of_measurement"] = unit
        msgs.append((f"homeassistant/sensor/ice_traffic_car_{key}/config", json.dumps(cfg)))
    msgs.append(("homeassistant/sensor/ice_traffic_car_last_uplink/config", json.dumps(
        {"name": "Letzter Uplink", "unique_id": "ice_traffic_car_last_uplink", "object_id": "ice_traffic_car_last_uplink",
         "state_topic": f"{BASE}/state", "value_template": "{{ value_json.time }}", "device_class": "timestamp", "device": DEV})))
    msgs.append(("homeassistant/device_tracker/ice_traffic_car/config", json.dumps(
        {"name": "Auto", "unique_id": "ice_traffic_car_tracker", "object_id": "ice_traffic_car",
         "json_attributes_topic": f"{BASE}/location", "source_type": "gps", "device": DEV})))
    return msgs


class LoraListener:
    """Haengt sich an den MQTT-Client des HaPublisher (gleicher Broker wie ChirpStack)."""
    def __init__(self, client, core=None):
        self.c = client
        self.core = core
        client.message_callback_add("application/+/device/+/event/up", self._on_msg)

    def on_connect(self):
        self.c.subscribe("application/+/device/+/event/up", qos=1)
        for topic, payload in discovery_messages():
            self.c.publish(topic, payload, retain=True)

    def _on_msg(self, _c, _u, m):
        try:
            r = handle_event(m.payload)
            if not r:
                return
            state, loc = r
            if self.core is not None:
                self.core.add_car_uplink(state, loc, _ts(state.get("time")))
            self.c.publish(f"{BASE}/state", json.dumps(state), retain=True)
            if loc:
                self.c.publish(f"{BASE}/location", json.dumps(loc), retain=True)
        except Exception as e:  # noqa: BLE001
            print("lora listener:", e, flush=True)


def _ts(t):
    """ChirpStack-Zeit (RFC 3339, evtl. Nanosekunden) -> Epoch; None bei Fehler."""
    try:
        t = t.rstrip("Z")
        if "." in t:
            a, b = t.split(".")
            t = a + "." + b[:6].split("+")[0]
        return _dt.datetime.fromisoformat(t).replace(tzinfo=_dt.timezone.utc).timestamp()
    except Exception:  # noqa: BLE001
        return None
