#!/usr/bin/env python3
"""
🦅 ZenceFil Multi-Source Intelligence Hunter v2.0
====================================================
DAHİCE PLAN: Rastgele port taraması yerine, AKILLI arama yapar.

3 Katmanlı Strateji:
  1) Google Dorking → Marka login sayfaları + TR keyword'leri
  2) Çoklu Kamera Agregator Siteler → Insecam + alternatifleri
  3) Brand Fingerprinting → HTTP Header/Content analizi ile doğrulama

Her bulunan ONLINE kamera anında online_findings.txt'ye yazılır.

Kullanım: python3 zencefil_hunter.py
"""

import requests
import re
import random
import concurrent.futures
import threading
import time
import socket
import os
import sys
from urllib.parse import quote_plus

# ============================================================
# 🛡️ CONFIG
# ============================================================
OUTPUT_FILE = "online_findings.txt"
file_lock = threading.Lock()
seen_lock = threading.Lock()
seen_ips = set()

stats = {"found": 0, "checked": 0, "start": time.time()}
stats_lock = threading.Lock()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
]

def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8",
    }

# ============================================================
# 🇹🇷 TURKISH IP PREFIX WHITELIST
# ============================================================
TR_IP_PREFIXES = [
    # Turk Telekom
    "78.16", "78.17", "78.18", "78.19",
    "81.21", "85.9", "85.10", "85.11",
    "88.2", "95.0", "95.1", "95.2", "95.3", "95.4", "95.5", "95.6", "95.7", "95.8", "95.9",
    # Superonline  
    "176.21", "176.22", "176.23", "31.223",
    # Vodafone TR
    "46.1.", "46.196", "46.197",
    # Other TR ISPs
    "5.2", "5.44", "37.13", "37.51",
    "159.146", "193.140", "194.27",
    "195.174", "195.175",
    "212.15", "212.174", "212.175",
    "213.14", "213.15", "213.153",
    # Additional TR Ranges
    "31.145", "31.206", "46.106", "46.154",
    "176.234", "176.235", "176.236",
]

def is_tr_ip(url):
    """Check if URL contains a Turkish IP address."""
    try:
        ip = url.replace("http://", "").replace("https://", "").split(":")[0].split("/")[0]
        return any(ip.startswith(prefix) for prefix in TR_IP_PREFIXES)
    except:
        return False

# ============================================================
# 📝 FILE WRITER (Thread-Safe, Real-Time, TR-Only)
# ============================================================
def save_finding(url):
    """Save a verified TURKISH online camera to file immediately."""
    # 🇹🇷 TR IP Filter: Only save Turkish IPs
    if not is_tr_ip(url):
        return False
    
    with seen_lock:
        if url in seen_ips:
            return False
        seen_ips.add(url)
    
    with file_lock:
        with open(OUTPUT_FILE, "a") as f:
            f.write(f"{url}\n")
    
    with stats_lock:
        stats["found"] += 1
    
    elapsed = time.time() - stats["start"]
    print(f"  🇹🇷 [TR-ONLINE] {url}  (#{stats['found']} | {elapsed:.0f}s)")
    return True

# ============================================================
# ✅ VERIFY: Gerçekten kamera mı? (Smart Check)
# ============================================================
def verify_camera(url, timeout=4):
    """
    Verify if a URL is actually an online camera/IoT device.
    Checks HTTP response and looks for camera-related signatures.
    """
    with stats_lock:
        stats["checked"] += 1
    
    camera_signatures = [
        "camera", "webcam", "viewer", "video", "stream", "mjpg", "jpeg",
        "login", "dvr", "nvr", "cctv", "hikvision", "dahua", "axis",
        "foscam", "ipcam", "netcam", "surveillance", "monitor",
        "live view", "snapshot", "channel", "recording",
        "onvif", "rtsp", "p2p", "ddns", "ptz",
        # Turkish
        "kamera", "canli", "izle", "guvenlik", "goruntu",
        # Brand specific
        "fury", "qromax", "rxr", "yoosee", "neutron", "haikon",
        "goahead", "boa", "thttpd", "mini_httpd", "jaws",
        "web service", "digest", "realm",
    ]
    
    try:
        resp = requests.get(url, headers=get_headers(), timeout=timeout, 
                          allow_redirects=True, verify=False, stream=True)
        
        if resp.status_code < 400:
            # Check headers for camera signatures
            headers_str = str(resp.headers).lower()
            
            # Read only first 2KB of content
            content = resp.raw.read(2048).decode("utf-8", errors="ignore").lower()
            combined = headers_str + content
            
            # Check if it looks like a camera/IoT device
            for sig in camera_signatures:
                if sig in combined:
                    save_finding(url)
                    return True
            
            # Even without signatures, if port is non-standard and responds, it's interesting
            if any(f":{p}/" in url for p in ["81","82","83","84","85","88","554","8000","8080","8081","8090","8888","37777","34567"]):
                save_finding(url)
                return True
                
    except:
        pass
    return False

# ============================================================
# 🔍 SOURCE 1: Google Dorking (Marka + Keyword Search)
# ============================================================

# Brand-specific Google dorks
BRAND_DORKS = [
    # Hikvision
    'intitle:"Hikvision" "Turkey"',
    'inurl:"/doc/page/login.asp" "Turkey"',
    'intitle:"NVR" inurl:"login" site:tr',
    'intitle:"DVR" inurl:"login" site:tr',
    # Dahua  
    'intitle:"Web Service" inurl:"/login" "Dahua"',
    'inurl:"/cgi-bin/configManager" site:tr',
    # Fury / Generic XMeye
    'intitle:"DVR" "Fury" inurl:"login"',
    'intitle:"XMeye" inurl:"login" "Turkey"',
    'intitle:"CMS" inurl:"/login" site:tr',
    # TP-Link / Tapo
    'intitle:"TP-LINK" inurl:"userLogin" site:tr',
    'intitle:"Tapo" inurl:"/login"',
    # Yoosee / V380
    'intitle:"Yoosee" inurl:"/index"',
    'intitle:"V380" inurl:"/index"',
    '"JAWS/1.0" site:tr',
    # Generic Camera Keywords (Turkish)
    'inurl:"/view/viewer_index" "Turkiye"',
    'intitle:"IP Camera" "Turkey"',
    'intitle:"Network Camera" site:tr',
    'intitle:"Webcam" inurl:"/view" site:tr',
    # Ev / Oda / Otel (Home / Room / Hotel)
    'intitle:"kamera" "ev" inurl:"login"',
    'intitle:"camera" "otel" site:tr',
    'intitle:"live" "cam" site:tr',
    '"GoAhead-Webs" site:tr',
    '"Boa/0.94" site:tr',
    '"thttpd" "camera" site:tr',
    # Qromax / RXR / Neutron
    'intitle:"Qromax" inurl:"login"',
    'intitle:"RXR" "camera"',
    'intitle:"Neutron" inurl:"login"',
    'intitle:"Haikon" inurl:"login"',
    # Xiaomi
    '"Xiaomi" "camera" "Turkey"',
    '"Mi Home" "camera" site:tr',
]

# Location/context keywords
TR_KEYWORDS = [
    "ev kamerası", "oda kamerası", "otel kamerası", "bebek kamerası",
    "güvenlik kamerası canlı", "işyeri kamerası", "mağaza kamerası",
    "apart kamera", "pansiyon kamera", "ofis kamera canlı",
    "ip kamera türkiye canlı", "canlı kamera izle türkiye",
    "dvr login turkey", "nvr login türkiye",
    "mobese canlı", "trafik kamerası canlı",
]

def search_google(dork, max_results=20):
    """Search Google for camera-related pages."""
    found_urls = []
    ip_pattern = re.compile(r'https?://(\d+\.\d+\.\d+\.\d+)(?::(\d+))?')
    
    try:
        query = quote_plus(dork)
        search_url = f"https://www.google.com/search?q={query}&num={max_results}"
        
        resp = requests.get(search_url, headers=get_headers(), timeout=10)
        if resp.status_code == 200:
            # Extract IP-based URLs from search results
            matches = ip_pattern.findall(resp.text)
            for ip, port in matches:
                if port:
                    found_urls.append(f"http://{ip}:{port}/")
                else:
                    found_urls.append(f"http://{ip}/")
    except:
        pass
    
    return found_urls

# ============================================================
# 🌐 SOURCE 2: Camera Aggregator Sites
# ============================================================
def scrape_insecam_deep():
    """Deep scrape Insecam for Turkey cameras across all vectors."""
    found = []
    ip_pattern = re.compile(r'https?://\d+\.\d+\.\d+\.\d+(?::\d+)?/?')
    session = requests.Session()
    
    # All possible Insecam search vectors
    vectors = []
    
    # By country
    for page in range(1, 50):
        vectors.append(f"http://www.insecam.org/en/bycountry/TR/?page={page}")
    
    # By manufacturer
    manufacturers = ["Axis", "Hikvision", "Dahua", "Panasonic", "Sony", "DLink", 
                     "TP-Link", "Foscam", "Samsung", "Canon", "Toshiba", "Bosch"]
    for m in manufacturers:
        for page in range(1, 20):
            vectors.append(f"http://www.insecam.org/en/bytype/{m}/?page={page}")
    
    # By tag (Turkish keywords)
    tags = [
        "Turkey", "Istanbul", "Ankara", "Izmir", "Antalya", "Bursa",
        "Kamera", "Canli", "Webcam", "Live", "CCTV", "DVR", "Security",
        "Ev", "Otel", "Ofis", "Market", "Eczane", "Cafe", "Restoran",
        "Mobese", "Trafik", "Guvenlik", "Bebek", "Pet",
        "Fury", "Qromax", "Yoosee", "RXR", "Xiaomi", "Neutron",
        "Haikon", "Goldmaster", "Spy", "Mini", "Hidden"
    ]
    for tag in tags:
        for page in range(1, 10):
            vectors.append(f"http://www.insecam.org/en/bytag/{tag}/?page={page}")
    
    # By city (Turkish cities)
    cities = [
        "Istanbul", "Ankara", "Izmir", "Antalya", "Bursa", "Adana",
        "Gaziantep", "Konya", "Mersin", "Diyarbakir", "Kayseri",
        "Eskisehir", "Samsun", "Trabzon", "Mugla", "Hatay"
    ]
    for city in cities:
        for page in range(1, 15):
            vectors.append(f"http://www.insecam.org/en/bycity/{city}/?page={page}")
    
    random.shuffle(vectors)
    
    def fetch(url):
        try:
            headers = {
                'User-Agent': random.choice(USER_AGENTS),
                'Referer': 'http://www.insecam.org/en/bycountry/'
            }
            resp = session.get(url, headers=headers, timeout=12)
            if resp.status_code == 200:
                ips = ip_pattern.findall(resp.text)
                for ip_url in ips:
                    if "insecam.org" not in ip_url:
                        found.append(ip_url)
        except:
            pass
    
    print(f"  🌐 Insecam Deep Scrape: {len(vectors)} sayfa taranıyor...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as ex:
        ex.map(fetch, vectors)
    
    return list(set(found))

# ============================================================
# 🎯 SOURCE 3: Direct Brand Fingerprint Probing
# ============================================================

# Known TR ISP Ranges with high camera density
TR_RANGES = [
    ("78.160.0.0", "78.191.255.255"),
    ("81.212.0.0", "81.215.255.255"),
    ("85.96.0.0", "85.111.255.255"),
    ("88.224.0.0", "88.255.255.255"),
    ("95.0.0.0", "95.15.255.255"),
    ("176.214.0.0", "176.239.255.255"),
    ("31.223.0.0", "31.223.255.255"),
    ("46.1.0.0", "46.1.255.255"),
    ("46.196.0.0", "46.197.255.255"),
    ("5.24.0.0", "5.27.255.255"),
    ("212.154.0.0", "212.159.255.255"),
    ("213.14.0.0", "213.15.255.255"),
    ("195.174.0.0", "195.175.255.255"),
]

# Brand-specific URL paths that confirm camera type
BRAND_PATHS = {
    "Hikvision": ["/doc/page/login.asp", "/ISAPI/System/deviceInfo"],
    "Dahua": ["/cgi-bin/configManager.cgi?action=getConfig&name=Network", "/RPC2_Login"],
    "Fury/XMeye": ["/Login.htm", "/DVR.htm"],
    "TP-Link": ["/userLogin.html"],
    "Generic DVR": ["/login.htm", "/web/"],
    "GoAhead": ["/system.html", "/system.ini"],
    "JAWS": ["/index.html"],
    "Axis": ["/view/viewer_index.shtml", "/mjpg/video.mjpg"],
    "Panasonic": ["/nphMotionJpeg", "/cgi-bin/camera"],
    "Foscam": ["/live.htm", "/cgi-bin/CGIProxy.fcgi"],
}

# All ports to check per IP
ALL_PORTS = [80, 81, 82, 83, 84, 85, 88, 443, 554, 
             8000, 8001, 8080, 8081, 8090, 8443, 8888,
             9000, 37777, 34567, 50001, 60001]

def ip_to_int(ip):
    parts = ip.split(".")
    return (int(parts[0]) << 24) + (int(parts[1]) << 16) + (int(parts[2]) << 8) + int(parts[3])

def int_to_ip(num):
    return f"{(num >> 24) & 255}.{(num >> 16) & 255}.{(num >> 8) & 255}.{num & 255}"

def random_tr_ip():
    start_ip, end_ip = random.choice(TR_RANGES)
    start_int = ip_to_int(start_ip)
    end_int = ip_to_int(end_ip)
    return int_to_ip(random.randint(start_int, end_int))


def smart_probe_ip(ip):
    """
    Smart probe: First check if any camera port is open (fast socket),
    then try brand-specific paths to confirm it's a camera.
    """
    open_ports = []
    
    # Phase 1: Fast port scan (socket only, 1s timeout)
    for port in ALL_PORTS:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            if sock.connect_ex((ip, port)) == 0:
                open_ports.append(port)
            sock.close()
        except:
            pass
    
    if not open_ports:
        return
    
    # Phase 2: Brand fingerprinting on open ports
    for port in open_ports:
        base_url = f"http://{ip}:{port}"
        
        # Try brand-specific paths
        for brand, paths in BRAND_PATHS.items():
            for path in paths:
                target = f"{base_url}{path}"
                try:
                    resp = requests.get(target, headers=get_headers(), timeout=3, 
                                      verify=False, allow_redirects=True, stream=True)
                    if resp.status_code < 400:
                        content = resp.raw.read(1024).decode("utf-8", errors="ignore").lower()
                        headers_str = str(resp.headers).lower()
                        
                        # Confirm it's a camera
                        if any(kw in content + headers_str for kw in [
                            "camera", "dvr", "nvr", "login", "video", "stream", 
                            "viewer", "snapshot", "channel", "ipc", "goahead",
                            "jaws", "boa", "hikvision", "dahua", "fury", "xmeye"
                        ]):
                            save_finding(f"{base_url}/")
                            return  # Found camera, move on
                except:
                    pass
        
        # Phase 3: Generic check on base URL
        try:
            resp = requests.get(f"{base_url}/", headers=get_headers(), timeout=3,
                              verify=False, allow_redirects=True, stream=True)
            if resp.status_code < 400:
                content = resp.raw.read(2048).decode("utf-8", errors="ignore").lower()
                headers_str = str(resp.headers).lower()
                
                if any(kw in content + headers_str for kw in [
                    "camera", "dvr", "nvr", "login", "video", "stream",
                    "viewer", "snapshot", "goahead", "jaws", "boa",
                    "hikvision", "dahua", "fury", "xmeye", "kamera",
                    "onvif", "rtsp", "p2p", "surveillance", "cctv"
                ]):
                    save_finding(f"{base_url}/")
                    return
        except:
            pass


# ============================================================
# 🚀 MAIN ORCHESTRATOR
# ============================================================
def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║  🦅 ZenceFil Multi-Source Intelligence Hunter v2.0          ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║  Katman 1: Google Dorking (Marka + Ev/Oda/Otel)            ║
║  Katman 2: Insecam Deep Scrape (Tüm Vektörler)            ║
║  Katman 3: Smart Brand Fingerprinting (TR ISP Tarama)      ║
║  ────────────────────────────────────────────────────────── ║
║  Sonuçlar → online_findings.txt (Anlık yazılır)            ║
║  Ctrl+C ile durdurun                                        ║
╚══════════════════════════════════════════════════════════════╝
    """)


def status_reporter():
    """Print status every 20 seconds."""
    while True:
        time.sleep(20)
        elapsed = time.time() - stats["start"]
        print(f"\n  📊 [{elapsed:.0f}s] Kontrol: {stats['checked']} | Bulunan: {stats['found']} kamera\n")


def main():
    print_banner()
    
    # Load existing findings to avoid duplicates
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            for line in f:
                seen_ips.add(line.strip())
        print(f"  📂 Mevcut {len(seen_ips)} kayıt yüklendi (tekrar edilmeyecek)")
    
    # Start status reporter
    threading.Thread(target=status_reporter, daemon=True).start()
    
    # ═══════════════════════════════════════════
    # ARKA PLAN: Insecam Deep Scrape (Paralel)
    # ═══════════════════════════════════════════
    def background_insecam():
        print(f"\n  🌐 ARKA PLAN: Insecam Deep Scrape başlatıldı...")
        insecam_results = scrape_insecam_deep()
        print(f"  🎯 Insecam: {len(insecam_results)} IP → Doğrulanıyor...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
            ex.map(verify_camera, insecam_results)
        print(f"  ✅ Insecam tamamlandı. Toplam: {stats['found']} kamera")
    
    threading.Thread(target=background_insecam, daemon=True).start()
    
    try:
        # ═══════════════════════════════════════════
        # ANA MOTOR: Smart Brand Fingerprinting (Sonsuz)
        # ═══════════════════════════════════════════
        print(f"\n  🎯 ANA MOTOR: Smart TR Brand Fingerprinting")
        print(f"  🌍 {len(TR_RANGES)} Türk ISP bloğu | {len(ALL_PORTS)} port | {len(BRAND_PATHS)} marka")
        print(f"  🇹🇷 SADECE Türk IP'leri kaydedilecek!")
        print("  " + "─" * 55)
        
        batch = 0
        while True:
            batch += 1
            ips = [random_tr_ip() for _ in range(300)]
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=150) as ex:
                ex.map(smart_probe_ip, ips)
            
            if batch % 3 == 0:
                print(f"  🔄 Batch #{batch}: Toplam bulunan: {stats['found']} TR kamera")
    
    except KeyboardInterrupt:
        elapsed = time.time() - stats["start"]
        print(f"\n\n  🛑 Tarama durduruldu.")
        print(f"  📊 SONUÇ: {stats['checked']} kontrol | {stats['found']} ONLINE TR kamera")
        print(f"  ⏱️  Süre: {elapsed:.0f} saniye")
        print(f"  📁 Kayıt: {os.path.abspath(OUTPUT_FILE)}")


if __name__ == "__main__":
    main()
