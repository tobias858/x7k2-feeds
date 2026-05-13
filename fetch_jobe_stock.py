import os, csv, urllib.request, xml.etree.ElementTree as ET

URL  = os.environ["JOBE_URL"]
USER = os.environ["JOBE_USER"]
PASS = os.environ["JOBE_PASS"]

mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
mgr.add_password(None, URL, USER, PASS)
opener = urllib.request.build_opener(urllib.request.HTTPBasicAuthHandler(mgr))
with opener.open(URL, timeout=30) as r:
    xml_bytes = r.read()

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

with open("jobe_stock.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["ean", "stock"])
    writer.writeheader()
    writer.writerows(rows)

print(f"{len(rows)} regels geschreven naar jobe_stock.csv")
