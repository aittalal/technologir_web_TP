import json
import os
from flask import Flask, jsonify, request, abort

app = Flask(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# ─── Helpers ───────────────────────────────────────────────────────────────────

def load_data(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)

def save_data(filename, data):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def next_id(items):
    if not items:
        return 1
    return max(item["id"] for item in items) + 1


# ─── Webservers ────────────────────────────────────────────────────────────────

@app.route("/webservers", methods=["GET"])
def get_webservers():
    return jsonify(load_data("webservers.json"))

@app.route("/webservers/<int:id>", methods=["GET"])
def get_webserver(id):
    items = load_data("webservers.json")
    item = next((x for x in items if x["id"] == id), None)
    if item is None:
        abort(404)
    return jsonify(item)

@app.route("/webservers", methods=["POST"])
def add_webserver():
    data = request.get_json()
    items = load_data("webservers.json")
    new_item = {
        "id": next_id(items),
        "name": data.get("name", ""),
        "root": data.get("root", "/var/www/html"),
        "index": data.get("index", "index.html"),
        "error_page": data.get("error_page", "/error-page.html")
    }
    items.append(new_item)
    save_data("webservers.json", items)
    return jsonify(new_item), 201

@app.route("/webservers/<int:id>", methods=["DELETE"])
def delete_webserver(id):
    items = load_data("webservers.json")
    items = [x for x in items if x["id"] != id]
    save_data("webservers.json", items)
    return jsonify({"message": "deleted"}), 200


# ─── Reverse Proxies ───────────────────────────────────────────────────────────

@app.route("/reverseproxies", methods=["GET"])
def get_reverseproxies():
    return jsonify(load_data("reverseproxies.json"))

@app.route("/reverseproxies/<int:id>", methods=["GET"])
def get_reverseproxy(id):
    items = load_data("reverseproxies.json")
    item = next((x for x in items if x["id"] == id), None)
    if item is None:
        abort(404)
    return jsonify(item)

@app.route("/reverseproxies", methods=["POST"])
def add_reverseproxy():
    data = request.get_json()
    items = load_data("reverseproxies.json")
    new_item = {
        "id": next_id(items),
        "name": data.get("name", ""),
        "server1": data.get("server1", ""),
        "server2": data.get("server2", ""),
        "lb_method": data.get("lb_method", "")
    }
    items.append(new_item)
    save_data("reverseproxies.json", items)
    return jsonify(new_item), 201

@app.route("/reverseproxies/<int:id>", methods=["DELETE"])
def delete_reverseproxy(id):
    items = load_data("reverseproxies.json")
    items = [x for x in items if x["id"] != id]
    save_data("reverseproxies.json", items)
    return jsonify({"message": "deleted"}), 200


# ─── Load Balancers ────────────────────────────────────────────────────────────

@app.route("/loadbalancers", methods=["GET"])
def get_loadbalancers():
    return jsonify(load_data("loadbalancer.json"))

@app.route("/loadbalancers/<int:id>", methods=["GET"])
def get_loadbalancer(id):
    items = load_data("loadbalancer.json")
    item = next((x for x in items if x["id"] == id), None)
    if item is None:
        abort(404)
    return jsonify(item)

@app.route("/loadbalancers", methods=["POST"])
def add_loadbalancer():
    data = request.get_json()
    items = load_data("loadbalancer.json")
    new_item = {
        "id": next_id(items),
        "name": data.get("name", ""),
        "ip_bind": data.get("ip_bind", ""),
        "pass": data.get("pass", "")
    }
    items.append(new_item)
    save_data("loadbalancer.json", items)
    return jsonify(new_item), 201

@app.route("/loadbalancers/<int:id>", methods=["DELETE"])
def delete_loadbalancer(id):
    items = load_data("loadbalancer.json")
    items = [x for x in items if x["id"] != id]
    save_data("loadbalancer.json", items)
    return jsonify({"message": "deleted"}), 200
