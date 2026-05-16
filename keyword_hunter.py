#!/usr/bin/env python3
"""
🔍 ZenceFil Keyword Camera Hunter v1.0
========================================
Kamera isimlerinde/içeriklerinde belirli kelimeler geçen
IP kameraları tespit eder.

Hedef Kelimeler: ev, oda, otel, hotel, gizli, hidden,
room, home, bedroom, lobby, reception, bebek, çocuk...

3 Kaynak:
  1) Insecam tag araması (ev, otel, gizli, vb.)
  2) Mevcut online_findings.txt IP'lerinin içerik analizi
  3) TR ISP subnet taraması + içerik keyword kontrolü

Sonuçlar → keyword_cameras.txt (etiketli)
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
import warnings
warnings.filterwarnings("ignore")

# ============================================================
OUTPUT_FILE = "keyword_cameras.txt"
ONLINE_FILE = "online_findings.txt"
file_lock = threading.Lock()
seen_lock = threading.Lock()
seen_urls = set()

stats = {"found": 0, "checked": 0, "start": time.time()}
stats_lock = threading.Lock()

UA = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# ============================================================
# 🎯 TARGET KEYWORDS (Turkish + English)
# ============================================================
KEYWORDS = {
    # Otel / Hotel (User Request: "otel ve hotel olarak ara")
    "otel": ["otel", "hotel", "motel", "hostel", "pansiyon", "apart", "konaklama",
             "lobby", "lobi", "reception", "resepsiyon", "suit", "suite", "misafir", "guest"],
}

# Flatten all keywords for matching
ALL_KEYWORDS = []
for category, words in KEYWORDS.items():
    for w in words:
        ALL_KEYWORDS.append((w.lower(), category))

# Insecam search tags (Filtered for Hotel/Otel focus)
INSECAM_TAGS = [
    # Hotel / Accommodation
    "Otel", "Hotel", "Motel", "Hostel", "Pansiyon", "Apart", "Konaklama",
    "Lobby", "Lobi", "Reception", "Resepsiyon", "Suit", "Suite",
    "Resort", "Tatil", "Holiday", "Tourism", "Turizm",
    "Entrance", "Giris", "Hall", "Koridor", "Restaurant", "Restoran",
    "Bar", "Cafe", "Pool", "Havuz", "Spa", "Gym", "Fitness",
    "Otopark", "Parking", "Garage", "Garaj", "Valet",
    # Specific Locations
    "Istanbul", "Antalya", "Bodrum", "Marmaris", "Fethiye", "Cesme", 
    "Alanya", "Side", "Belek", "Kemer", "Kusadasi", "Cappadocia", "Kapadokya"
]

# ============================================================
# 🇹🇷 TR FILTER — Tüm Türk ISP Blokları
# ============================================================
TR_PREFIXES = [
    # Turk Telekom (TTNET)
    "78.160.", "78.161.", "78.162.", "78.163.", "78.164.", "78.165.",
    "78.166.", "78.167.", "78.168.", "78.169.", "78.170.", "78.171.",
    "78.172.", "78.173.", "78.174.", "78.175.", "78.176.", "78.177.",
    "78.178.", "78.179.", "78.180.", "78.181.", "78.182.", "78.183.",
    "78.184.", "78.185.", "78.186.", "78.187.", "78.188.", "78.189.",
    "78.190.", "78.191.",
    "81.212.", "81.213.", "81.214.", "81.215.",
    "85.96.", "85.97.", "85.98.", "85.99.", "85.100.", "85.101.",
    "85.102.", "85.103.", "85.104.", "85.105.", "85.106.", "85.107.",
    "85.108.", "85.109.", "85.110.", "85.111.",
    # Superonline / Turkcell
    "88.224.", "88.225.", "88.226.", "88.227.", "88.228.", "88.229.",
    "88.230.", "88.231.", "88.232.", "88.233.", "88.234.", "88.235.",
    "88.236.", "88.237.", "88.238.", "88.239.", "88.240.", "88.241.",
    "88.242.", "88.243.", "88.244.", "88.245.", "88.246.", "88.247.",
    "88.248.", "88.249.", "88.250.", "88.251.", "88.252.", "88.253.",
    "88.254.", "88.255.",
    "88.212.", "88.213.", "88.214.", "88.215.",
    # Superonline
    "176.214.", "176.215.", "176.216.", "176.217.", "176.218.", "176.219.",
    "176.220.", "176.221.", "176.222.", "176.223.", "176.224.", "176.225.",
    "176.226.", "176.227.", "176.228.", "176.229.", "176.230.", "176.231.",
    "176.232.", "176.233.", "176.234.", "176.235.", "176.236.", "176.237.",
    "176.238.", "176.239.",
    "31.223.",
    # Vodafone TR
    "46.1.", "46.196.", "46.197.",
    # Turkcell
    "95.0.", "95.1.", "95.2.", "95.3.", "95.4.", "95.5.",
    "95.6.", "95.7.", "95.8.", "95.9.", "95.10.", "95.11.",
    "95.12.", "95.13.", "95.14.", "95.15.",
    # Other TR ISPs
    "5.24.", "5.25.", "5.26.", "5.27.",
    "5.44.", "5.45.", "5.46.", "5.47.",
    "37.130.", "37.131.",
    "159.146.",
    "193.140.",
    "194.27.",
    "195.174.", "195.175.",
    "212.154.", "212.155.", "212.156.", "212.157.", "212.158.", "212.159.",
    "212.174.", "212.175.",
    "213.14.", "213.15.",
    "213.153.",
    "31.145.", "31.206.",
    "46.106.", "46.154.",
]

def is_tr_ip(ip):
    return any(ip.startswith(p) for p in TR_PREFIXES)

# ============================================================
# 📝 SAVE (Labeled)
# ============================================================
def save_finding(url, matched_keyword, category):
    with seen_lock:
        if url in seen_urls:
            return False
        seen_urls.add(url)
    
    entry = f"[{category.upper()}] {url} | keyword: \"{matched_keyword}\""
    
    with file_lock:
        with open(OUTPUT_FILE, "a") as f:
            f.write(entry + "\n")
        # Also add to main findings
        with open(ONLINE_FILE, "a") as f:
            f.write(url + "\n")
    
    with stats_lock:
        stats["found"] += 1
    
    elapsed = time.time() - stats["start"]
    print(f"  🏷️ [{category.upper()}] {url}")
    print(f"      Keyword: \"{matched_keyword}\" | #{stats['found']} | {elapsed:.0f}s")
    return True

# ============================================================
# 🔍 CHECK CONTENT FOR KEYWORDS
# ============================================================
def check_url_keywords(url):
    """Fetch URL and check content for target keywords."""
    with stats_lock:
        stats["checked"] += 1
    
    try:
        resp = requests.get(url, timeout=5, verify=False, stream=True,
                          headers={"User-Agent": random.choice(UA)},
                          allow_redirects=True)
        
        if resp.status_code >= 400:
            return None
        
        # Read headers + page title + first 4KB
        headers_str = str(resp.headers).lower()
        body = resp.raw.read(4096).decode("utf-8", errors="ignore").lower()
        
        # Extract <title> if present
        title_match = re.search(r'<title[^>]*>(.*?)</title>', body, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""
        
        # Combine everything for keyword search
        searchable = f"{headers_str} {body} {title}"
        
        # Check each keyword
        for keyword, category in ALL_KEYWORDS:
            if keyword in searchable:
                save_finding(url, keyword, category)
                return (url, keyword, category)
        
    except:
        pass
    return None

# ============================================================
# 🌐 SOURCE 1: Insecam Deep Tag Search
# ============================================================
def scrape_insecam_tags():
    """Search Insecam for cameras with specific tags."""
    found_urls = []
    ip_pattern = re.compile(r'https?://\d+\.\d+\.\d+\.\d+(?::\d+)?/?')
    session = requests.Session()
    
    vectors = []
    for tag in INSECAM_TAGS:
        for page in range(1, 30):
            vectors.append(f"http://www.insecam.org/en/bytag/{tag}/?page={page}")
        # Also try with /TR/ suffix
        for page in range(1, 20):
            vectors.append(f"http://www.insecam.org/en/bytag/{tag}/TR/?page={page}")
    
    # By country pages
    for page in range(1, 50):
        vectors.append(f"http://www.insecam.org/en/bycountry/TR/?page={page}")
    
    random.shuffle(vectors)
    
    def fetch(url):
        try:
            resp = session.get(url, timeout=12, headers={
                'User-Agent': random.choice(UA),
                'Referer': 'http://www.insecam.org/'
            })
            if resp.status_code == 200:
                ips = ip_pattern.findall(resp.text)
                for ip_url in ips:
                    if "insecam.org" not in ip_url:
                        found_urls.append(ip_url)
        except:
            pass
    
    print(f"  🌐 Insecam: {len(vectors)} sayfa taranıyor ({len(INSECAM_TAGS)} tag)...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as ex:
        ex.map(fetch, vectors)
    
    return list(set(found_urls))

# ============================================================
# 🎯 SOURCE 2: TR ISP Subnet Scan + Keyword Check
# ============================================================
TR_RANGES = [
    # Turk Telekom
    (78, range(160,192)), (81, range(212,216)),
    (85, range(96,112)),
    # Superonline / Turkcell
    (88, range(212,256)), (95, range(0,16)),
    # Superonline
    (176, range(214,240)), (31, [223]),
    # Vodafone
    (46, [1, 196, 197]),
    # Other
    (5, range(24,48)), (37, [130,131]),
    (159, [146]), (193, [140]), (194, [27]),
    (195, range(174,176)),
    (212, range(154,176)), (213, [14,15,153]),
]

FAST_PORTS = [80, 81, 8080, 8081, 554, 8000, 88, 85, 37777]

def random_tr_ip():
    first, seconds = random.choice(TR_RANGES)
    second = random.choice(seconds)
    third = random.randint(0, 255)
    fourth = random.randint(1, 254)
    return f"{first}.{second}.{third}.{fourth}"

def probe_and_check(ip):
    """Fast port check + keyword content analysis."""
    for port in FAST_PORTS:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.8)
            if sock.connect_ex((ip, port)) == 0:
                sock.close()
                url = f"http://{ip}:{port}/"
                check_url_keywords(url)
                return
            sock.close()
        except:
            pass

# ============================================================
# 🚀 MAIN
# ============================================================
def print_banner():
    keyword_list = ", ".join(list(KEYWORDS.keys()))
    print(f"""
╔════════════════════════════════════════════════════════════════╗
║  🔍 ZenceFil Keyword Camera Hunter v1.0                       ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                                                                ║
║  Hedef: Kamera içeriğinde şu kelimeler geçen IP'ler:          ║
║  {keyword_list:<60} ║
║                                                                ║
║  Kaynak 1: Insecam tag araması                                 ║
║  Kaynak 2: Mevcut IP'lerin içerik analizi                      ║
║  Kaynak 3: TR ISP tarama + keyword kontrolü                   ║
║                                                                ║
║  📁 keyword_cameras.txt (etiketli sonuçlar)                    ║
║  Ctrl+C ile durdurun                                           ║
╚════════════════════════════════════════════════════════════════╝
    """)


def status_reporter():
    while True:
        time.sleep(15)
        elapsed = time.time() - stats["start"]
        print(f"\n  📊 [{elapsed:.0f}s] Kontrol: {stats['checked']} | "
              f"Keyword Eşleşme: {stats['found']} kamera\n")


def main():
    print_banner()
    
    # Load existing
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            for line in f:
                if "] http" in line:
                    url_part = line.split("] ")[1].split(" |")[0].strip()
                    seen_urls.add(url_part)
    
    threading.Thread(target=status_reporter, daemon=True).start()
    
    # ═══════════════════════════════════════════
    # ARKA PLAN 1: Insecam Tag Araması (Paralel)
    # ═══════════════════════════════════════════
    def background_insecam():
        print("  🌐 ARKA PLAN: Insecam Hotel Tag Araması başlatıldı...")
        insecam_urls = scrape_insecam_tags()
        print(f"  🎯 Insecam: {len(insecam_urls)} IP → İçerik analizi...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=40) as ex:
            ex.map(check_url_keywords, insecam_urls)
        print(f"  ✅ Insecam tamamlandı. Toplam: {stats['found']}")
    
    threading.Thread(target=background_insecam, daemon=True).start()
    
    # ═══════════════════════════════════════════
    # ARKA PLAN 2: Mevcut IP'lerin İçerik Analizi
    # ═══════════════════════════════════════════
    def background_existing():
        existing_urls = []
        if os.path.exists(ONLINE_FILE):
            with open(ONLINE_FILE, "r") as f:
                for line in f:
                    url = line.strip()
                    if url and url.startswith("http"):
                        existing_urls.append(url)
        existing_urls = list(set(existing_urls))
        if existing_urls:
            print(f"  � ARKA PLAN: {len(existing_urls)} mevcut IP içerik analizi...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=40) as ex:
                ex.map(check_url_keywords, existing_urls)
    
    threading.Thread(target=background_existing, daemon=True).start()
    
    try:
        # ═══════════════════════════════════════════
        # ANA MOTOR: TR ISP Tarama (Hemen Başlar!)
        # ═══════════════════════════════════════════
        print("  � ANA MOTOR: Otel/Hotel Keyword Taraması (Sonsuz Mod)")
        print(f"  🇹🇷 {len(TR_RANGES)} TR ISP bloğu | Hedef: otel, hotel, lobby, resepsiyon...")
        print("  " + "─" * 55)
        
        batch = 0
        while True:
            try:
                batch += 1
                ips = [random_tr_ip() for _ in range(300)]
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=150) as ex:
                    ex.map(probe_and_check, ips)
                
                if batch % 3 == 0:
                    print(f"  🔄 Batch #{batch}: Otel eşleşme: {stats['found']}")
            except Exception as e:
                print(f"  ⚠️ Batch hatası: {e} — devam ediliyor...")
                time.sleep(1)
    
    except KeyboardInterrupt:
        elapsed = time.time() - stats["start"]
        print(f"\n\n  🛑 Tarama durduruldu.")
        print(f"  📊 SONUÇ: {stats['checked']} kontrol | {stats['found']} keyword eşleşme")
        print(f"  ⏱️  Süre: {elapsed:.0f} saniye")
        print(f"  📁 Etiketli kayıt: {os.path.abspath(OUTPUT_FILE)}")
        
        # Print summary
        if os.path.exists(OUTPUT_FILE):
            print(f"\n  📋 BULUNAN KAMERALAR:")
            with open(OUTPUT_FILE, "r") as f:
                for line in f:
                    print(f"     {line.strip()}")


if __name__ == "__main__":
    main()
