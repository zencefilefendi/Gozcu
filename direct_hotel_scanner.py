#!/usr/bin/env python3
"""
🏨 ZenceFil Direct Hotel Camera Scanner v3.0
==============================================
Insecam'a GEREK YOK. Kendimiz tespit ediyoruz.

Strateji:
  1. Türk ISP IP bloklarını doğrudan tara (socket)
  2. Açık port bulununca HTTP isteği gönder
  3. HTTP yanıtını analiz et:
     - <title> içinde "hotel", "otel", "lobby" var mı?
     - WWW-Authenticate realm'inde otel ismi var mı?
     - Server header'ında tanınan kamera markası var mı?
     - Cihaz adında (device name) otel kelimesi var mı?
  4. Eşleşenleri hotel_cameras.txt'e yaz

Neden çalışır?
  - Kamera yöneticileri cihaz adını genellikle lokasyona göre koyar
    Örn: "Hotel Lobby Cam", "Otel Giris", "Reception 1"
  - WWW-Authenticate realm'i çoğu zaman cihaz adını içerir
  - Bu bilgiler HTTP header'larında görünür, sayfa yüklenmeden!

Kullanım: python3 direct_hotel_scanner.py
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
OUTPUT_FILE = "hotel_cameras.txt"
ALL_FINDINGS = "online_findings.txt"
file_lock = threading.Lock()
seen_lock = threading.Lock()
seen_ips = set()

stats = {"scanned": 0, "open": 0, "hotel": 0, "start": time.time()}
stats_lock = threading.Lock()

UA = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
]

# ============================================================
# 🏨 HOTEL KEYWORDS — HTTP yanıtında aranacak
# ============================================================
HOTEL_KEYWORDS = [
    # 🏨 Otel / Hotel
    b"otel", b"hotel", b"motel", b"pansiyon", b"apart",
    b"lobi", b"lobby", b"resepsiyon", b"reception",
    b"koridor", b"corridor", b"giris", b"entrance",
    b"tatil", b"resort", b"konaklama", b"misafir",
    b"suite", b"suit", b"oda no", b"room no",
    b"restoran", b"restaurant",
    b"hotel lobby", b"hotel reception", b"hotel cam",
    b"lobby cam", b"reception cam",
    b"guest room", b"check in", b"check-in",
    b"front desk", b"concierge",
    # 🛁 Spa / Havuz
    b"spa", b"hamam", b"sauna", b"havuz", b"pool",
    b"wellness", b"jacuzzi", b"fitness", b"gym",
    b"spa cam", b"pool cam", b"havuz kamera",
    # 🏠 Ev / Home
    b"ev kamera", b"ev cam", b"home cam", b"home camera",
    b"evim", b"my home", b"house cam",
    b"salon", b"mutfak", b"kitchen", b"living room",
    b"bahce", b"garden", b"balkon", b"balcony",
    # 🛏️ Oda / Room
    b"oda", b"room", b"bedroom", b"yatak odasi",
    b"banyo", b"bathroom", b"wc cam",
    b"oda kamera", b"room camera", b"room cam",
    # 👁️ Gizli / Hidden
    b"gizli", b"hidden", b"spy", b"secret",
    b"gizli kamera", b"hidden cam", b"spy cam",
    b"nanny cam", b"dadi", b"bebek",
    b"private", b"ozel", b"gizli izle",
    # 📍 TR Tatil Şehirleri
    b"antalya", b"bodrum", b"marmaris", b"alanya",
    b"fethiye", b"kemer", b"belek", b"side",
    b"kusadasi", b"cesme", b"didim", b"mugla",
    b"istanbul", b"ankara", b"izmir", b"bursa",
]

# ============================================================
# 🇹🇷 TÜRK ISP IP BLOKLARI — Tam Liste
# ============================================================
TR_RANGES = [
    # Turk Telekom (TTNET) — En büyük ISP
    (78, range(160, 192)),
    (81, range(212, 216)),
    (85, range(96, 112)),
    # Superonline
    (88, range(212, 256)),
    (176, range(214, 240)),
    (31, [223]),
    # Turkcell Superonline
    (95, range(0, 16)),
    # Vodafone TR
    (46, [1, 196, 197]),
    # Diğer TR ISP'ler
    (5, range(24, 48)),
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

# Kamera portları — önce en yaygın olanlar
CAMERA_PORTS = [80, 8080, 554, 81, 8081, 8000, 8001, 88, 85, 443,
                37777, 34567, 9000, 50001, 60001, 8888, 8090]

# ============================================================
# 🔍 FAST PORT CHECK
# ============================================================
def port_open(ip, port, timeout=0.7):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((ip, port)) == 0
        s.close()
        return result
    except:
        return False

# ============================================================
# 🏨 HOTEL DETECTION — HTTP yanıtını analiz et
# ============================================================
def analyze_for_hotel(ip, port):
    """
    HTTP yanıtını analiz ederek otel kamerası olup olmadığını tespit et.
    Sayfa içeriğini değil, HEADER'ları önce kontrol et (hızlı).
    """
    url = f"http://{ip}:{port}/"
    
    try:
        resp = requests.get(
            url, timeout=4, verify=False, stream=True,
            headers={"User-Agent": random.choice(UA)},
            allow_redirects=True
        )
        
        if resp.status_code >= 500:
            return None, None
        
        # ── 1. HEADER ANALİZİ (en hızlı) ──
        headers_raw = str(resp.headers).lower().encode()
        
        # WWW-Authenticate realm genellikle cihaz adını içerir
        auth_header = resp.headers.get("WWW-Authenticate", "").lower()
        
        # ── 2. SAYFA İÇERİĞİ (ilk 3KB) ──
        body = resp.raw.read(3072)
        body_lower = body.lower()
        
        # ── 3. TITLE ÇIKAR ──
        title_match = re.search(rb'<title[^>]*>(.*?)</title>', body_lower, re.DOTALL)
        title = title_match.group(1).strip() if title_match else b""
        
        # ── 4. KEYWORD KONTROL ──
        searchable = headers_raw + body_lower + title + auth_header.encode()
        
        for kw in HOTEL_KEYWORDS:
            if kw in searchable:
                return url, kw.decode("utf-8", errors="ignore")
        
    except:
        pass
    
    return None, None

# ============================================================
# 📝 SAVE
# ============================================================
def save_hotel(url, keyword):
    with seen_lock:
        if url in seen_ips:
            return False
        seen_ips.add(url)
    
    with file_lock:
        with open(OUTPUT_FILE, "a") as f:
            f.write(f"{url}  # keyword: {keyword}\n")
        with open(ALL_FINDINGS, "a") as f:
            f.write(f"{url}\n")
    
    with stats_lock:
        stats["hotel"] += 1
    
    elapsed = time.time() - stats["start"]
    print(f"  🏨 HOTEL: {url}")
    print(f"      Keyword: \"{keyword}\" | #{stats['hotel']} | {elapsed:.0f}s")
    return True

# ============================================================
# 🎯 SCAN SINGLE IP
# ============================================================
def scan_ip(ip):
    with stats_lock:
        stats["scanned"] += 1
    
    for port in CAMERA_PORTS:
        if port_open(ip, port):
            with stats_lock:
                stats["open"] += 1
            
            # Önce online_findings'e ekle (tüm açık kameralar)
            base_url = f"http://{ip}:{port}/"
            with seen_lock:
                already = base_url in seen_ips
            
            if not already:
                with file_lock:
                    with open(ALL_FINDINGS, "a") as f:
                        f.write(f"{base_url}\n")
            
            # Sonra otel analizi yap
            hotel_url, keyword = analyze_for_hotel(ip, port)
            if hotel_url:
                save_hotel(hotel_url, keyword)
            
            return  # Bu IP'de bir port bulduk, devam et

# ============================================================
# 🎲 RANDOM TR IP GENERATOR
# ============================================================
def random_tr_ip():
    first, seconds = random.choice(TR_RANGES)
    second = random.choice(list(seconds))
    third = random.randint(0, 255)
    fourth = random.randint(1, 254)
    return f"{first}.{second}.{third}.{fourth}"

# ============================================================
# 📊 STATUS REPORTER
# ============================================================
def status_reporter():
    while True:
        time.sleep(20)
        elapsed = time.time() - stats["start"]
        rate = stats["scanned"] / elapsed if elapsed > 0 else 0
        print(f"\n  📊 [{elapsed:.0f}s] "
              f"Tarandı: {stats['scanned']} ({rate:.0f}/s) | "
              f"Açık Port: {stats['open']} | "
              f"🏨 Hotel: {stats['hotel']}\n")

# ============================================================
# 🚀 MAIN
# ============================================================
def print_banner():
    total_ranges = sum(len(list(r)) for _, r in TR_RANGES)
    print(f"""
╔════════════════════════════════════════════════════════════════╗
║  🏨 ZenceFil Direct Hotel Camera Scanner v3.0                 ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                                                                ║
║  ✅ Insecam'a GEREK YOK — Kendimiz tespit ediyoruz!           ║
║                                                                ║
║  🇹🇷 {len(TR_RANGES)} TR ISP bloğu ({total_ranges} /24 subnet)               ║
║  🔍 {len(CAMERA_PORTS)} kamera portu                                          ║
║  🏨 {len(HOTEL_KEYWORDS)} otel keyword'ü (header + içerik)                   ║
║                                                                ║
║  📁 hotel_cameras.txt  (otel kameraları)                       ║
║  📁 online_findings.txt (tüm açık kameralar)                   ║
║  Ctrl+C ile durdurun                                           ║
╚════════════════════════════════════════════════════════════════╝
    """)


def main():
    print_banner()
    
    # Load existing
    for fname in [OUTPUT_FILE, ALL_FINDINGS]:
        if os.path.exists(fname):
            with open(fname, "r") as f:
                for line in f:
                    url = line.strip().split("#")[0].strip()
                    if url:
                        seen_ips.add(url)
    print(f"  📂 Mevcut {len(seen_ips)} kayıt yüklendi (tekrar taranmayacak)")
    
    threading.Thread(target=status_reporter, daemon=True).start()
    
    print(f"\n  🚀 Tarama başlıyor... (300 IP/batch × 150 thread)\n")
    
    try:
        batch = 0
        while True:
            batch += 1
            ips = [random_tr_ip() for _ in range(300)]
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=150) as ex:
                ex.map(scan_ip, ips)
            
            if batch % 5 == 0:
                print(f"  🔄 Batch #{batch} | Tarandı: {stats['scanned']} | "
                      f"Açık: {stats['open']} | Hotel: {stats['hotel']}")
    
    except KeyboardInterrupt:
        elapsed = time.time() - stats["start"]
        print(f"\n\n  🛑 Tarama durduruldu.")
        print(f"  📊 Tarandı: {stats['scanned']} IP | "
              f"Açık: {stats['open']} | Hotel: {stats['hotel']}")
        print(f"  ⏱️  Süre: {elapsed:.0f}s")
        
        if stats['hotel'] > 0:
            print(f"\n  🏨 BULUNAN OTEL KAMERALARI:")
            with open(OUTPUT_FILE) as f:
                for line in f:
                    print(f"     {line.strip()}")


if __name__ == "__main__":
    main()
