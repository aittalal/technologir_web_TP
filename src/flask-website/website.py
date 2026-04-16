import re
import requests
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response

app = Flask(__name__)
app.secret_key = "change-this-secret-key-in-production"

API_URL = "http://localhost:5000"

USERS = {
    "admin": "admin123",
    "user":  "password"
}

# ─── Helpers de validation ─────────────────────────────────────────────────────

def is_valid_hostname(hostname):
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    return bool(re.match(pattern, hostname)) and len(hostname) <= 253

def is_valid_ip(ip):
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip):
        return False
    return all(0 <= int(part) <= 255 for part in ip.split('.'))

def is_valid_url(url):
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, url))

def is_valid_unix_path(path):
    return path.startswith('/') and len(path) > 1

# ─── Authentification ──────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            flash("Veuillez vous connecter pour accéder à cette page.", "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated

@app.route("/login", methods=["GET", "POST"])
def login():
    if "username" in session:
        return redirect(url_for("start"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if username in USERS and USERS[username] == password:
            session["username"] = username
            flash(f"Bienvenue, {username} !", "success")
            next_url = request.args.get("next") or url_for("start")
            return redirect(next_url)
        else:
            error = "Nom d'utilisateur ou mot de passe incorrect."
    return render_template("auth/login.html", error=error)

@app.route("/logout")
def logout():
    username = session.pop("username", None)
    if username:
        flash(f"Au revoir, {username} !", "info")
    return redirect(url_for("login"))

# ─── Accueil ───────────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def start():
    return render_template("start.html")

# ─── Webservers ────────────────────────────────────────────────────────────────

@app.route("/webservers")
@login_required
def webservers_list():
    items = requests.get(f"{API_URL}/webservers").json()
    return render_template("webservers/list.html", items=items)

@app.route("/webservers/<int:id>")
@login_required
def webservers_detail(id):
    item = requests.get(f"{API_URL}/webservers/{id}").json()
    return render_template("webservers/detail.html", item=item)

@app.route("/webservers/<int:id>/download")
@login_required
def webservers_download(id):
    item = requests.get(f"{API_URL}/webservers/{id}").json()
    config = f"""http {{
    server {{
        root {item['root']};

        location / {{
            index {item['index']};
        }}

        error_page 404 403 500 503 {item['error_page']};
        location = {item['error_page']} {{
            root /var/www/error;
            internal;
        }}
    }}
}}
"""
    filename = f"nginx-webserver-{item['name'].replace(' ', '_').lower()}.conf"
    return Response(config, mimetype="text/plain",
        headers={"Content-Disposition": f"attachment; filename={filename}"})

@app.route("/webservers/add", methods=["GET", "POST"])
@login_required
def webservers_add():
    errors = {}
    form_data = {}
    if request.method == "POST":
        name       = request.form.get("name", "").strip()
        root       = request.form.get("root", "").strip()
        index      = request.form.get("index", "").strip()
        error_page = request.form.get("error_page", "").strip()
        form_data  = {"name": name, "root": root, "index": index, "error_page": error_page}
        if not name:
            errors["name"] = "Le nom est obligatoire."
        elif len(name) > 100:
            errors["name"] = "Le nom ne doit pas dépasser 100 caractères."
        if not root:
            errors["root"] = "Le répertoire racine est obligatoire."
        elif not is_valid_unix_path(root):
            errors["root"] = "Le chemin doit être absolu (commencer par /)."
        if not index:
            errors["index"] = "Le fichier index est obligatoire."
        if not error_page:
            errors["error_page"] = "La page d'erreur est obligatoire."
        elif not is_valid_unix_path(error_page):
            errors["error_page"] = "Le chemin doit être absolu (commencer par /)."
        if not errors:
            requests.post(f"{API_URL}/webservers", json=form_data)
            flash("Serveur web ajouté avec succès !", "success")
            return redirect(url_for("webservers_list"))
    return render_template("webservers/add.html", errors=errors, form_data=form_data)

@app.route("/webservers/<int:id>/delete", methods=["POST"])
@login_required
def webservers_delete(id):
    requests.delete(f"{API_URL}/webservers/{id}")
    flash("Serveur web supprimé.", "info")
    return redirect(url_for("webservers_list"))

# ─── Reverse Proxies ───────────────────────────────────────────────────────────

@app.route("/reverseproxies")
@login_required
def reverseproxies_list():
    items = requests.get(f"{API_URL}/reverseproxies").json()
    return render_template("reverseproxies/list.html", items=items)

@app.route("/reverseproxies/<int:id>")
@login_required
def reverseproxies_detail(id):
    item = requests.get(f"{API_URL}/reverseproxies/{id}").json()
    return render_template("reverseproxies/detail.html", item=item)

@app.route("/reverseproxies/<int:id>/download")
@login_required
def reverseproxies_download(id):
    item = requests.get(f"{API_URL}/reverseproxies/{id}").json()
    lb_line = f"        {item['lb_method']}\n" if item.get('lb_method') else ""
    config = f"""http {{
    upstream backend {{
{lb_line}        server {item['server1']};
        server {item['server2']};
    }}

    server {{
        location / {{
            proxy_pass http://backend;
        }}
    }}
}}
"""
    filename = f"nginx-reverseproxy-{item['name'].replace(' ', '_').lower()}.conf"
    return Response(config, mimetype="text/plain",
        headers={"Content-Disposition": f"attachment; filename={filename}"})

@app.route("/reverseproxies/add", methods=["GET", "POST"])
@login_required
def reverseproxies_add():
    errors = {}
    form_data = {}
    if request.method == "POST":
        name      = request.form.get("name", "").strip()
        server1   = request.form.get("server1", "").strip()
        server2   = request.form.get("server2", "").strip()
        lb_method = request.form.get("lb_method", "")
        form_data = {"name": name, "server1": server1, "server2": server2, "lb_method": lb_method}
        if not name:
            errors["name"] = "Le nom est obligatoire."
        elif len(name) > 100:
            errors["name"] = "Le nom ne doit pas dépasser 100 caractères."
        if not server1:
            errors["server1"] = "Le serveur 1 est obligatoire."
        elif not is_valid_hostname(server1):
            errors["server1"] = "Hostname invalide (ex: server1.domain.tld)."
        if not server2:
            errors["server2"] = "Le serveur 2 est obligatoire."
        elif not is_valid_hostname(server2):
            errors["server2"] = "Hostname invalide (ex: server2.domain.tld)."
        if server1 and server2 and server1 == server2:
            errors["server2"] = "Les deux serveurs doivent être différents."
        if not errors:
            requests.post(f"{API_URL}/reverseproxies", json=form_data)
            flash("Reverse proxy ajouté avec succès !", "success")
            return redirect(url_for("reverseproxies_list"))
    return render_template("reverseproxies/add.html", errors=errors, form_data=form_data)

@app.route("/reverseproxies/<int:id>/delete", methods=["POST"])
@login_required
def reverseproxies_delete(id):
    requests.delete(f"{API_URL}/reverseproxies/{id}")
    flash("Reverse proxy supprimé.", "info")
    return redirect(url_for("reverseproxies_list"))

# ─── Load Balancers ────────────────────────────────────────────────────────────

@app.route("/loadbalancers")
@login_required
def loadbalancers_list():
    items = requests.get(f"{API_URL}/loadbalancers").json()
    return render_template("loadbalancers/list.html", items=items)

@app.route("/loadbalancers/<int:id>")
@login_required
def loadbalancers_detail(id):
    item = requests.get(f"{API_URL}/loadbalancers/{id}").json()
    return render_template("loadbalancers/detail.html", item=item)

@app.route("/loadbalancers/<int:id>/download")
@login_required
def loadbalancers_download(id):
    item = requests.get(f"{API_URL}/loadbalancers/{id}").json()
    config = f"""http {{
    server {{
        location / {{
            proxy_bind {item['ip_bind']};
            proxy_pass {item['pass']};
        }}
    }}
}}
"""
    filename = f"nginx-loadbalancer-{item['name'].replace(' ', '_').lower()}.conf"
    return Response(config, mimetype="text/plain",
        headers={"Content-Disposition": f"attachment; filename={filename}"})

@app.route("/loadbalancers/add", methods=["GET", "POST"])
@login_required
def loadbalancers_add():
    errors = {}
    form_data = {}
    if request.method == "POST":
        name    = request.form.get("name", "").strip()
        ip_bind = request.form.get("ip_bind", "").strip()
        pass_   = request.form.get("pass", "").strip()
        form_data = {"name": name, "ip_bind": ip_bind, "pass": pass_}
        if not name:
            errors["name"] = "Le nom est obligatoire."
        elif len(name) > 100:
            errors["name"] = "Le nom ne doit pas dépasser 100 caractères."
        if not ip_bind:
            errors["ip_bind"] = "L'adresse IP est obligatoire."
        elif not is_valid_ip(ip_bind):
            errors["ip_bind"] = "Adresse IPv4 invalide (ex: 192.168.1.1)."
        if not pass_:
            errors["pass"] = "L'URL de proxy pass est obligatoire."
        elif not is_valid_url(pass_):
            errors["pass"] = "URL invalide. Elle doit commencer par http:// ou https://."
        if not errors:
            requests.post(f"{API_URL}/loadbalancers", json={"name": name, "ip_bind": ip_bind, "pass": pass_})
            flash("Load balancer ajouté avec succès !", "success")
            return redirect(url_for("loadbalancers_list"))
    return render_template("loadbalancers/add.html", errors=errors, form_data=form_data)

@app.route("/loadbalancers/<int:id>/delete", methods=["POST"])
@login_required
def loadbalancers_delete(id):
    requests.delete(f"{API_URL}/loadbalancers/{id}")
    flash("Load balancer supprimé.", "info")
    return redirect(url_for("loadbalancers_list"))

# ─── Page de déploiement ───────────────────────────────────────────────────────

@app.route("/setup")
@login_required
def setup():
    webservers     = requests.get(f"{API_URL}/webservers").json()
    reverseproxies = requests.get(f"{API_URL}/reverseproxies").json()
    loadbalancers  = requests.get(f"{API_URL}/loadbalancers").json()
    return render_template("setup.html",
        webservers=webservers,
        reverseproxies=reverseproxies,
        loadbalancers=loadbalancers)

@app.route("/setup/download-compose")
@login_required
def setup_download_compose():
    webservers     = requests.get(f"{API_URL}/webservers").json()
    reverseproxies = requests.get(f"{API_URL}/reverseproxies").json()
    loadbalancers  = requests.get(f"{API_URL}/loadbalancers").json()
    services = ""
    port = 8080
    for ws in webservers:
        sname = ws['name'].replace(' ', '_').lower()
        services += f"""
  webserver_{sname}:
    image: nginx:latest
    container_name: webserver_{sname}
    ports:
      - "{port}:80"
    volumes:
      - ./configs/nginx-webserver-{sname}.conf:/etc/nginx/nginx.conf:ro
      - {ws['root']}:{ws['root']}:ro
    restart: unless-stopped
"""
        port += 1
    for rp in reverseproxies:
        sname = rp['name'].replace(' ', '_').lower()
        services += f"""
  reverseproxy_{sname}:
    image: nginx:latest
    container_name: reverseproxy_{sname}
    ports:
      - "{port}:80"
    volumes:
      - ./configs/nginx-reverseproxy-{sname}.conf:/etc/nginx/nginx.conf:ro
    restart: unless-stopped
"""
        port += 1
    for lb in loadbalancers:
        sname = lb['name'].replace(' ', '_').lower()
        services += f"""
  loadbalancer_{sname}:
    image: nginx:latest
    container_name: loadbalancer_{sname}
    ports:
      - "{port}:80"
    volumes:
      - ./configs/nginx-loadbalancer-{sname}.conf:/etc/nginx/nginx.conf:ro
    restart: unless-stopped
"""
        port += 1
    compose = f"""# docker-compose.yml généré par Web Configurator
# Placez vos fichiers .conf dans le dossier ./configs/

version: '3.8'

services:{services}
"""
    return Response(compose, mimetype="text/plain",
        headers={"Content-Disposition": "attachment; filename=docker-compose.yml"})
