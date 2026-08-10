import os
import csv
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET


def fetch_xml(url, user, pw, retries=3, delay=10):
    mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    mgr.add_password(None, url, user, pw)
    opener = urllib.request.build_opener(urllib.request.HTTPBasicAuthHandler(mgr))
    last_err = None
    for poging in range(1, retries + 1):
        try:
            data = opener.open(url, timeout=60).read()
            ET.fromstring(data)  # valideert meteen de XML
            return data
        except ET.ParseError as e:
            last_err = f"ongeldige XML: {e}"
        except Exception as e:
            last_err = f"{e}"
        print(f"Poging {poging}/{retries} mislukt \u2014 {last_err}")
        if poging < retries:
            time.sleep(delay)
    sys.exit(f"XML ophalen mislukt na {retries} pogingen: {last_err}")


def main():
    try:
        url = os.environ["JOBE_URL"]
        user = os.environ["JOBE_USER"]
        pw = os.environ["JOBE_PASS"]
    except KeyError as e:
        sys.exit(f"Secret ontbreekt: {e}. Zet JOBE_URL/JOBE_USER/JOBE_PASS in de repo-secrets.")

    data = fetch_xml(url, user, pw)

    root = ET.fromstring(data)
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
        sys.exit("Geen producten in XML \u2014 niets geschreven (feed leeg?).")

    with open("jobe_stock.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ean", "stock"])
        w.writerows(rows)
    print(f"{len(rows)} regels weggeschreven.")


if __name__ == "__main__":
    main()
