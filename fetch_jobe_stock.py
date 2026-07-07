"""fetch_jobe_stock.py — GitHub Actions versie.

Leest JOBE_URL / JOBE_USER / JOBE_PASS uit de omgeving (repo-secrets) en
schrijft jobe_stock.csv in de working directory (= repo-root in Actions).

Bewust GEEN hardcoded credentials en GEEN GitHub API-push:
de workflow-stap committet het CSV-bestand zelf.
"""

import os
import csv
import sys
import urllib.request
import xml.etree.ElementTree as ET


def main():
    try:
        url = os.environ["JOBE_URL"]
        user = os.environ["JOBE_USER"]
        pw = os.environ["JOBE_PASS"]
    except KeyError as e:
        sys.exit(f"Secret ontbreekt: {e}. Zet JOBE_URL/JOBE_USER/JOBE_PASS in de repo-secrets.")

    mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    mgr.add_password(None, url, user, pw)
    opener = urllib.request.build_opener(urllib.request.HTTPBasicAuthHandler(mgr))
    data = opener.open(url, timeout=60).read()

    root = ET.fromstring(data)  # valideert meteen de XML
    rows = []
    for p in root.findall("product"):
        ean = (p.findtext("ean") or "").strip()
        s = (p.findtext("stock") or "0").strip()
        try:
            v = max(0, int(s))
        except (ValueError, TypeError):
            v = 0
        rows.append((ean, v))

    if not rows:
        sys.exit("Geen producten in XML — niets geschreven (feed leeg?).")

    with open("jobe_stock.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ean", "stock"])
        w.writerows(rows)
    print(f"{len(rows)} regels weggeschreven.")


if __name__ == "__main__":
    main()
