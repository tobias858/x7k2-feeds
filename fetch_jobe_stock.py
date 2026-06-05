"""
fetch_jobe_stock.py — haalt dagelijks JoBe Sports voorraad op en publiceert naar GitHub.

Configuratie via .env in de projectroot:
  JOBE_URL       XML-feed URL
  JOBE_USER      Basic-auth gebruikersnaam
  JOBE_PASS      Basic-auth wachtwoord
  GITHUB_TOKEN   Personal Access Token (github_pat_...)
  GITHUB_REPO    Bijv. tobias858/watersportsonline-feeds
  GITHUB_FILE    Bestandsnaam in de repo, bijv. jobe_stock.csv
"""

import os
import csv
import json
import base64
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

# --- .env laden ---
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

URL          = os.environ.get("JOBE_URL",    "https://joe.jobesports.com/beheer/cron/stock/stock_EUR.xml")
USER         = os.environ.get("JOBE_USER",   "1200735")
PASS         = os.environ.get("JOBE_PASS",   "ijben")
GH_TOKEN     = os.environ.get("GITHUB_TOKEN", "")
GH_REPO      = os.environ.get("GITHUB_REPO",  "tobias858/watersportsonline-feeds")
GH_FILE      = os.environ.get("GITHUB_FILE",  "jobe_stock.csv")
LOCAL_CSV    = str(Path(__file__).parent.parent / "werkbestanden" / "jobe_stock.csv")


def fetch_xml(url, user, password, retries=3, delay=10):
    mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    mgr.add_password(None, url, user, password)
    opener = urllib.request.build_opener(urllib.request.HTTPBasicAuthHandler(mgr))
    for poging in range(1, retries + 1):
        try:
            with opener.open(url, timeout=30) as resp:
                data = resp.read()
            ET.fromstring(data)  # valideer XML direct
            return data
        except ET.ParseError as e:
            print(f"  Poging {poging}/{retries} — ongeldige XML: {e}")
        except Exception as e:
            print(f"  Poging {poging}/{retries} — fout: {e}")
        if poging < retries:
            print(f"  Wacht {delay}s voor volgende poging...")
            time.sleep(delay)
    raise RuntimeError(f"XML ophalen mislukt na {retries} pogingen")


def parse_stock(xml_bytes):
    root = ET.fromstring(xml_bytes)
    rows = []
    for p in root.findall("product"):
        ean = p.findtext("ean", "").strip()
        stock = p.findtext("stock", "0").strip()
        try:
            stock_val = max(0, int(stock))
        except (ValueError, TypeError):
            stock_val = 0
        rows.append({"ean": ean, "stock": stock_val})
    return rows


def write_csv(rows, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ean", "stock"])
        writer.writeheader()
        writer.writerows(rows)


def github_upload(local_path, token, repo, filename):
    api = f"https://api.github.com/repos/{repo}/contents/{filename}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }

    # Huidige SHA ophalen (nodig voor update)
    sha = None
    req = urllib.request.Request(api, headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            sha = json.loads(r.read())["sha"]
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise

    content = base64.b64encode(Path(local_path).read_bytes()).decode()
    datum = datetime.now().strftime("%Y-%m-%d %H:%M")
    body = {
        "message": f"stock update {datum}",
        "content": content,
    }
    if sha:
        body["sha"] = sha

    data = json.dumps(body).encode()
    req = urllib.request.Request(api, data=data, headers=headers, method="PUT")
    with urllib.request.urlopen(req) as r:
        result = json.loads(r.read())
    return result["content"]["download_url"]


def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{ts}] XML ophalen...")
    xml_bytes = fetch_xml(URL, USER, PASS)

    rows = parse_stock(xml_bytes)
    print(f"[{ts}] {len(rows)} regels verwerkt.")

    write_csv(rows, LOCAL_CSV)
    print(f"[{ts}] Lokaal opgeslagen: {LOCAL_CSV}")

    if GH_TOKEN:
        print(f"[{ts}] Uploaden naar GitHub {GH_REPO}/{GH_FILE}...")
        url = github_upload(LOCAL_CSV, GH_TOKEN, GH_REPO, GH_FILE)
        print(f"[{ts}] Klaar! CSV beschikbaar op:")
        print(f"       https://raw.githubusercontent.com/{GH_REPO}/main/{GH_FILE}")
    else:
        print(f"[{ts}] Geen GITHUB_TOKEN gevonden — alleen lokaal opgeslagen.")


if __name__ == "__main__":
    main()
