import os
import subprocess
from flask import Flask, render_template, jsonify, request
from datetime import datetime

from ..backup import list_backups as get_backup_list, create_backup as do_backup, restore_backup as do_restore

app = Flask(__name__)


def get_cluster_status():
    try:
        nodes = subprocess.run(["kubectl", "get", "nodes", "-o", "name"], capture_output=True, text=True)
        pods = subprocess.run(["kubectl", "get", "pods", "--all-namespaces", "--no-headers"], capture_output=True, text=True)
        return {
            "healthy": nodes.returncode == 0,
            "node_count": len([n for n in nodes.stdout.strip().split("\n") if n]),
            "pod_count": len([p for p in pods.stdout.strip().split("\n") if p]),
        }
    except Exception:
        return {"healthy": False, "node_count": 0, "pod_count": 0}


def list_backups():
    try:
        return get_backup_list()
    except Exception:
        return []


@app.route("/")
def dashboard():
    backups = list_backups()
    status = get_cluster_status()
    return render_template("dashboard.html", status=status, backups=backups)


@app.route("/api/status")
def api_status():
    return jsonify(get_cluster_status())


@app.route("/api/backup", methods=["POST"])
def api_backup():
    result = do_backup()
    return jsonify({"success": bool(result), "output": result or "Backup created"})


@app.route("/api/restore", methods=["POST"])
def api_restore():
    backup_name = request.json.get("backup") if request.is_json else None
    if not backup_name:
        return jsonify({"success": False, "output": "No backup name provided"})
    success = do_restore(backup_name)
    return jsonify({"success": success, "output": "Restore complete" if success else "Restore failed"})


@app.route("/api/destroy", methods=["POST"])
def api_destroy():
    from ..cli import destroy
    success = destroy(auto_yes=True)
    return jsonify({"success": True, "output": "Cluster destroyed"})


def run_gui(host="127.0.0.1", port=5000):
    app.run(host=host, port=port, debug=False)