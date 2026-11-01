"""Demo ohne Hardware: sendet synthetische Fahrzeuge und eine wechselnde Ampel an den lokalen Broker.
Nutzung:  ITS_ASN_DIR=decoder/asn python3 decoder/tools_demo.py [broker-host] [port]   (Standard 127.0.0.1 1885)
Die Daten sind ERFUNDEN (Mitte Muenchen) und dienen nur dazu, Dashboard/Home-Assistant vorab zu pruefen."""
import math
import sys
import time

import paho.mqtt.publish as pub

from its_decoder import synth
from its_decoder.schemas import load

host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
port = int(sys.argv[2]) if len(sys.argv) > 2 else 1885
S = load()
states = ["stop-And-Remain", "protected-Movement-Allowed", "permissive-clearance", "protected-clearance"]
t0 = time.time()
print("Demo laeuft, Strg+C beendet.")
while True:
    t = time.time() - t0
    msgs = []
    for i in range(3):
        lat = 48.1735 + 0.002 * math.sin(t / 30 + i)
        lon = 11.5460 + 0.003 * math.cos(t / 30 + i)
        msgs.append(synth.frame(2001, synth.cam(S, 1000 + i, lat, lon, 8 + 3 * i, (t * 10 + 120 * i) % 360), lat, lon))
    msgs.append(synth.frame(2004, synth.spatem(S, 77, 1001, 3, states[int(t / 8) % 4])))
    msgs.append(synth.frame(2003, synth.mapem(S, 77, 1001, 48.1735, 11.5460)))
    msgs.append(synth.frame(2002, synth.denm(S, 4711, 48.1752, 11.5489, cause=1, sub=0)))
    pub.multiple([{"topic": "its/demo/packet", "payload": m} for m in msgs] + [{"topic": "its/demo/status", "payload": "online", "retain": True}],
                 hostname=host, port=port)
    time.sleep(1)
