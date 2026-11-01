"""Home-Assistant-Anbindung per MQTT-Discovery (Broker von HA, getrennt vom ITS-Broker)."""
import json
import threading
import time

import paho.mqtt.client as mqtt

DEV = {"identifiers": ["ice_traffic_data"], "name": "Ice-Traffic-Data", "manufacturer": "Ice", "model": "ITS-G5 Empfaenger"}
BASE = "ice_traffic"
# key, Name, Einheit, Icon, state_class
SENSORS = [
    ("pkts_per_min", "Pakete pro Minute", "pkt/min", "mdi:access-point", "measurement"),
    ("stations", "Sichtbare Fahrzeuge (CAM)", None, "mdi:car-connected", "measurement"),
    ("denms", "Aktive Gefahrenmeldungen (DENM)", None, "mdi:alert", "measurement"),
    ("intersections", "Kreuzungen mit Ampeldaten (SPATEM)", None, "mdi:traffic-light", "measurement"),
    ("maps", "Bekannte Kreuzungen (MAPEM)", None, "mdi:map-marker-path", "measurement"),
    ("frames", "Frames gesamt", None, "mdi:counter", "total_increasing"),
    ("undecoded", "Nicht dekodiert", None, "mdi:help-box", "total_increasing"),
    ("last_seen_s", "Letztes Paket vor", "s", "mdi:clock-outline", "measurement"),
]


class HaPublisher:
    def __init__(self, core, host, user=None, pw=None, port=1883):
        self.core = core
        self.c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if user:
            self.c.username_pw_set(user, pw)
        self.c.will_set(f"{BASE}/availability", "offline", retain=True)
        self.c.on_connect = self._on_connect
        self.c.connect_async(host, port)
        self.c.loop_start()

    def _on_connect(self, cl, *_):
        cl.publish(f"{BASE}/availability", "online", retain=True)
        for key, name, unit, icon, sc in SENSORS:
            cfg = {"name": name, "unique_id": f"ice_traffic_{key}", "object_id": f"ice_traffic_{key}",
                   "state_topic": f"{BASE}/state", "value_template": "{{ value_json.%s }}" % key,
                   "availability_topic": f"{BASE}/availability", "icon": icon, "state_class": sc, "device": DEV}
            if unit:
                cfg["unit_of_measurement"] = unit
            cl.publish(f"homeassistant/sensor/ice_traffic_{key}/config", json.dumps(cfg), retain=True)
        cfg = {"name": "Empfaenger online", "unique_id": "ice_traffic_receiver", "object_id": "ice_traffic_receiver",
               "state_topic": f"{BASE}/state", "value_template": "{{ value_json.receiver }}",
               "payload_on": "ON", "payload_off": "OFF", "device_class": "connectivity",
               "availability_topic": f"{BASE}/availability", "device": DEV}
        cl.publish("homeassistant/binary_sensor/ice_traffic_receiver/config", json.dumps(cfg), retain=True)
        # DENM-Text als eigener Sensor (Attribute: Liste)
        cfg = {"name": "Letzte Gefahrenmeldung", "unique_id": "ice_traffic_last_denm", "object_id": "ice_traffic_last_denm",
               "state_topic": f"{BASE}/state", "value_template": "{{ value_json.last_denm }}",
               "json_attributes_topic": f"{BASE}/denm", "availability_topic": f"{BASE}/availability",
               "icon": "mdi:alert-octagon", "device": DEV}
        cl.publish("homeassistant/sensor/ice_traffic_last_denm/config", json.dumps(cfg), retain=True)

    def state(self):
        s = self.core.snapshot()
        now = s["now"]
        last = s["recent"][0]["ts"] if s["recent"] else None
        age = int(now - last) if last else -1
        denms = s["denms"]
        return {
            "pkts_per_min": s["pkts_per_min"],
            "stations": len(s["stations"]), "denms": len(denms),
            "intersections": len([i for i in s["signals"] if now - i["ts"] < 120]),
            "maps": len(s["maps"]), "frames": s["stats"].get("frames", 0),
            "undecoded": s["stats"].get("undecoded", 0), "last_seen_s": age,
            "receiver": "ON" if 0 <= age < 120 or self.core.node_online() else "OFF",
            "last_denm": (f"cause {denms[0]['cause']}/{denms[0]['subcause']}" if denms else "keine"),
        }, denms

    def loop(self, every=10):
        while True:
            try:
                st, denms = self.state()
                self.c.publish(f"{BASE}/state", json.dumps(st), retain=True)
                self.c.publish(f"{BASE}/denm", json.dumps({"events": denms[:10]}, default=str), retain=True)
            except Exception:  # noqa: BLE001
                pass
            time.sleep(every)

    def start(self):
        threading.Thread(target=self.loop, daemon=True).start()
