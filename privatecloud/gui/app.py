import os
import secrets
import subprocess
import json
from flask import Flask, render_template, jsonify, request, session, abort

from ..backup import list_backups as get_backup_list, create_backup as do_backup, restore_backup as do_restore
from ..metrics import get_cluster_summary, get_node_metrics, get_pod_metrics, get_longhorn_metrics
from ...cli import destroy

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

auth_enabled = False
gui_username = None
gui_password = None


def check_auth():
    if not auth_enabled:
        return True
    if session.get("authenticated"):
        return True
    return False


@app.before_request
def require_auth():
    if check_auth():
        return None
    if request.path == "/login":
        return None
    return render_template("login.html"), 401


@app.route("/")
def dashboard():
    from ...doctor import check_tools
    status = get_cluster_status()
    backups = get_backup_list()
    return render_template("dashboard.html", status=status, backups=backups)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        user = data.get("username") or data.get("u")
        pwd = data.get("password") or data.get("p")
        if user == gui_username and pwd == gui_password:
            session["authenticated"] = True
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Invalid credentials"}), 401
    return render_template("login.html"), 401


@app.route("/logout")
def logout():
    session.clear()
    return jsonify({"success": True})


@app.route("/api/status")
def api_status():
    return jsonify(get_cluster_status())


@app.route("/api/metrics")
def api_metrics():
    return jsonify(get_cluster_summary())


@app.route("/api/backup", methods=["POST"])
def api_backup():
    result = do_backup()
    return jsonify({"success": bool(result), "output": result or "Backup created"})


@app.route("/api/restore", methods=["POST"])
def api_restore():
    data = request.get_json() if request.is_json else {}
    backup_name = data.get("backup")
    if not backup_name:
        return jsonify({"success": False, "output": "No backup name provided"})
    success = do_restore(backup_name)
    return jsonify({"success": success, "output": "Restore complete" if success else "Restore failed"})


@app.route("/api/destroy", methods=["POST"])
def api_destroy():
    try:
        destroy(auto_yes=True)
        return jsonify({"success": True, "output": "Cluster destroyed"})
    except Exception as e:
        return jsonify({"success": False, "output": str(e)})


def get_cluster_status():
    try:
        import subprocess
        nodes = subprocess.run(["kubectl", "get", "nodes", "-o", "name"], capture_output=True, text=True)
        pods = subprocess.run(["kubectl", "get", "pods", "--all-namespaces", "--no-headers"], capture_output=True, text=True)
        return {
            "healthy": nodes.returncode == 0,
            "node_count": len([n for n in nodes.stdout.strip().split("\n") if n]),
            "pod_count": len([p for p in pods.stdout.strip().split("\n") if p]),
        }
    except Exception:
        return {"healthy": False, "node_count": 0, "pod_count": 0}


def run_gui(host="127.0.0.1", port=5000, auth=False, username=None, password=None):
    global auth_enabled, gui_username, gui_password
    
    auth_enabled = auth
    gui_username = username or os.environ.get("PRIVATECLOUD_GUI_USER", "admin")
    gui_password = password or os.environ.get("PRIVATECLOUD_GUI_PASS", "changeme")
    
    if auth:
        print(f"🔐 GUI authentication enabled (user: {gui_username})")
    print(f"🌐 Starting GUI at http://{host}:{port}")
    app.run(host=host, port=port, debug=False)