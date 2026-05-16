#!/usr/bin/env python3
"""
🎯 ZenceFil Axis Camera TR Scanner v1.0
=========================================
Tüm Türk ISP bloklarında SADECE Axis kameralarını tespit eder.

Axis Fingerprint'leri:
  - HTTP Server header: "Axis"
  - URL path: /view/view.shtml, /view/viewer_index.shtml
  - Title: "Live View / - AXIS", "AXIS"
  - WWW-Authenticate realm: "AXIS"
  - Response body: "Axis Communications"

Sonuç: axis_cameras.txt
"""

import socket
import requests
import re
import random
import concurrent.futures
import threading
import time
import os
import warnings
warnings.filterwarnings("ignore")

# ============================================================
OUTPUT_FILE = "axis_cameras.txt"
ALL_FILE = "online_findings.txt"
file_lock = threading.Lock()
seen_lock = threading.Lock()
seen_ips = set()

stats = {"scanned": 0, "open": 0, "axis": 0, "start": time.time()}
stats_lock = threading.Lock()

UA = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120"]

# ============================================================
# 🎯 AXIS FINGERPRINTS
# ============================================================
AXIS_SIGNATURES = [
    b"axis",
    b"AXIS",
    b"Axis Communications",
    b"Live View / - AXIS",
    b"view/view.shtml",
    b"viewer_index.shtml",
    b"indexFrame.shtml",
    b"axis-cgi",
    b"/axis-cgi/",
    b"Axis Video",
    b"AXIS Camera",
    b"axis camera",
]

AXIS_PATHS = [
    "/",
    "/view/view.shtml",
    "/view/viewer_index.shtml",
    "/indexFrame.shtml",
    "/axis-cgi/jpg/image.cgi",
]

AXIS_PORTS = [80, 8080, 443, 8443, 8000, 81]

# ============================================================
# 🇹🇷 TÜRK ISP BLOKLARI
# ============================================================
TR_RANGES = [
    (78, range(160, 192)),   # Turk Telekom
    (81, range(212, 216)),   # Turk Telekom
    (85, range(96, 112)),    # Turk Telekom
    (88, range(212, 256)),   # Superonline / Turkcell
    (95, range(0, 16)),      # Turkcell
    (176, range(214, 240)),  # Superonline
    (31, [223]),             # Superonline
    (46, [1, 196, 197]),     # Vodafone TR
    (5, range(24, 48)),      # Diğer
    (37, [130, 131]),
    (159, [146]),
    (193, [140]),
    (194, [27]),
    (195, range(174, 176)),
    (212, range(154, 176)),
    (213, [14, 15, 153]),
    (31, [145, 206]),
    (46, [106, 154]),
]

def random_tr_ip():
    first, seconds = random.choice(TR_RANGES)
    second = random.choice(list(seconds))
    third = random.randint(0, 255)
    fourth = random.randint(1, 254)
    return f"{first}.{second}.{third}.{fourth}"

# ============================================================
# 🔍 PORT CHECK
# ============================================================
def port_open(ip, port, timeout=0.7):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        r = s.connect_ex((ip, port)) == 0
        s.close()
        return r
    except:
        return False

# ============================================================
# 🎯 AXIS DETECTION
# ============================================================
def is_axis(ip, port):
    """Check if this IP:port is an Axis camera."""
    for path in AXIS_PATHS:
        url = f"http://{ip}:{port}{path}"
        try:
            resp = requests.get(url, timeout=4, verify=False,
                              headers={"User-Agent": UA[0]},
                              allow_redirects=True)

            # Check Server header first (fastest)
            server = resp.headers.get("Server", "").lower()
            if "axis" in server:
                return url, f"Server: {resp.headers.get('Server')}"

            # Check WWW-Authenticate
            auth = resp.headers.get("WWW-Authenticate", "").lower()
            if "axis" in auth:
                return url, f"Auth: {auth[:50]}"

            # Check body (first 2KB)
            body = resp.raw.read(2048).lower()
            for sig in AXIS_SIGNATURES:
                if sig.lower() in body:
                    return url, f"Body: {sig.decode()}"

        except:
            pass
    return None, None

# ============================================================
# 📝 SAVE
# ============================================================
def save_axis(url, evidence):
    with seen_lock:
        if url in seen_ips:
            return False
        seen_ips.add(url)

    with file_lock:
        with open(OUTPUT_FILE, "a") as f:
            f.write(f"{url}  # {evidence}\n")
        with open(ALL_FILE, "a") as f:
            f.write(f"{url}\n")

    with stats_lock:
        stats["axis"] += 1

    elapsed = time.time() - stats["start"]
    print(f"  🎯 AXIS: {url}")
    print(f"      Kanıt: {evidence} | #{stats['axis']} | {elapsed:.0f}s")
    return True

# ============================================================
# 🔎 SCAN SINGLE IP
# ============================================================
def scan_ip(ip):
    with stats_lock:
        stats["scanned"] += 1

    for port in AXIS_PORTS:
        if port_open(ip, port):
            with stats_lock:
                stats["open"] += 1
            url, evidence = is_axis(ip, port)
            if url:
                save_axis(url, evidence)
            return  # found open port, move on

# ============================================================
# 📊 STATUS
# ============================================================
def status_reporter():
    while True:
        time.sleep(15)
        elapsed = time.time() - stats["start"]
        rate = stats["scanned"] / elapsed if elapsed > 0 else 0
        print(f"\n  📊 [{elapsed:.0f}s] "
              f"Tarandı: {stats['scanned']} ({rate:.0f}/s) | "
              f"Açık: {stats['open']} | "
              f"🎯 Axis: {stats['axis']}\n")

# ============================================================
# 🚀 MAIN
# ============================================================
def main():
    print("""
╔════════════════════════════════════════════════════════════════╗
║  🎯 ZenceFil Axis Camera TR Scanner v1.0                      ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                                                                ║
║  Tüm TR ISP bloklarında SADECE Axis kameraları                ║
║  Fingerprint: Server header, /view/view.shtml, realm          ║
║                                                                ║
║  📁 axis_cameras.txt                                           ║
║  Ctrl+C ile durdurun                                           ║
╚════════════════════════════════════════════════════════════════╝
    """)

    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            for line in f:
                url = line.strip().split("#")[0].strip()
                if url:
                    seen_ips.add(url)
        print(f"  📂 Mevcut {len(seen_ips)} Axis kamera yüklendi")

    threading.Thread(target=status_reporter, daemon=True).start()

    print(f"  🚀 Tarama başlıyor — 300 IP/batch × 150 thread\n")

    try:
        batch = 0
        while True:
            batch += 1
            ips = [random_tr_ip() for _ in range(300)]
            with concurrent.futures.ThreadPoolExecutor(max_workers=150) as ex:
                ex.map(scan_ip, ips)
            if batch % 5 == 0:
                print(f"  🔄 Batch #{batch} | Axis: {stats['axis']}")

    except KeyboardInterrupt:
        elapsed = time.time() - stats["start"]
        print(f"\n  🛑 Durduruldu. {stats['axis']} Axis kamera bulundu.")
        print(f"  ⏱️  Süre: {elapsed:.0f}s | 📁 {os.path.abspath(OUTPUT_FILE)}")
        if stats["axis"] > 0:
            print("\n  🎯 BULUNAN AXIS KAMERALAR:")
            with open(OUTPUT_FILE) as f:
                for line in f:
                    print(f"     {line.strip()}")


if __name__ == "__main__":
    main()
