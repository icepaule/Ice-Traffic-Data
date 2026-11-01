import os
import threading
import time

import paho.mqtt.client as mqtt
from flask import Flask, jsonify, send_from_directory

from .core import Core
from .schemas import load

BROKER = os.environ.get("MQTT_HOST", "mosquitto")
PORT = int(os.environ.get("MQTT_PORT", "1883"))
DB = os.environ.get("ITS_DB", "/data/its.db")


def make_app(core):
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), "static"))

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/api/state")
    def state():
        return jsonify(core.snapshot())

    return app


def main():
    core = Core(load(), DB)
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    c.username_pw_set(os.environ.get("MQTT_USER") or None, os.environ.get("MQTT_PASS") or None)

    def on_connect(cl, *_):
        cl.subscribe("its/+/packet")

    def on_message(cl, _u, m):
        node = m.topic.split("/")[1]
        core.feed(node, bytes(m.payload))

    c.on_connect, c.on_message = on_connect, on_message
    c.connect_async(BROKER, PORT)
    c.loop_start()

    def janitor():
        while True:
            time.sleep(3600)
            core.prune()

    threading.Thread(target=janitor, daemon=True).start()
    make_app(core).run("0.0.0.0", int(os.environ.get("WEB_PORT", "8097")))


if __name__ == "__main__":
    main()
