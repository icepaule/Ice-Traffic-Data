import os
import threading
import time

import paho.mqtt.client as mqtt
from flask import Flask, jsonify, send_from_directory

from . import autobahn
from .core import Core
from .ha import HaPublisher
from .schemas import load

BROKER = os.environ.get("MQTT_HOST", "mosquitto")
PORT = int(os.environ.get("MQTT_PORT", "1883"))
DB = os.environ.get("ITS_DB", "/data/its.db")


def make_app(core):
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), "static"))

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/poi.json")
    def poi():
        return send_from_directory(app.static_folder, "poi.json", mimetype="application/json")

    @app.get("/api/autobahn")
    def ab():
        return jsonify(autobahn.snapshot())

    @app.get("/api/state")
    def state():
        return jsonify(core.snapshot())

    return app


def main():
    core = Core(load(), DB)
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    c.username_pw_set(os.environ.get("MQTT_USER") or None, os.environ.get("MQTT_PASS") or None)

    def on_connect(cl, *_):
        cl.subscribe([("its/+/packet", 0), ("its/+/status", 0)])

    def on_message(cl, _u, m):
        node, kind = m.topic.split("/")[1:3]
        if kind == "status":
            core.set_node_status(node, m.payload.decode(errors="ignore"))
        else:
            core.feed(node, bytes(m.payload))

    c.on_connect, c.on_message = on_connect, on_message
    c.connect_async(BROKER, PORT)
    c.loop_start()

    def janitor():
        while True:
            time.sleep(3600)
            core.prune()

    threading.Thread(target=janitor, daemon=True).start()
    if os.environ.get("HA_MQTT_HOST"):
        HaPublisher(core, os.environ["HA_MQTT_HOST"], os.environ.get("HA_MQTT_USER") or None,
                    os.environ.get("HA_MQTT_PASS") or None, int(os.environ.get("HA_MQTT_PORT", "1883"))).start()
    autobahn.start()
    make_app(core).run("0.0.0.0", int(os.environ.get("WEB_PORT", "8097")))


if __name__ == "__main__":
    main()
