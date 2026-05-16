#!/usr/bin/env python3
"""
🏨 ZenceFil Hotel Camera Direct Scraper v2.0
==============================================
Insecam'ın zaten etiketlediği OTEL/HOTEL kameralarını
doğrudan çeker ve online olup olmadığını doğrular.

Strateji:
  - Insecam'da "Hotel", "Otel", "Lobby", "Reception" vb.
    tag'leri ile arama yap
  - Bulunan her IP'i gerçekten online mı diye kontrol et
  - Sadece online olanları kaydet → hotel_cameras.txt

Neden bu çalışır?
  - Insecam zaten her kamerayı etiketlemiş (hotel, lobby vb.)
  - Biz sadece bu etiketleri kullanıyoruz
  - Online kontrolü ile gerçek, erişilebilir kameraları buluyoruz
"""

import requests
import re
import random
import concurrent.futures
import threading
import time
import socket
import os
import warnings
warnings.filterwarnings("ignore")

# ============================================================
OUTPUT_FILE = "hotel_cameras.txt"
file_lock = threading.Lock()
seen_lock = threading.Lock()
seen_urls = set()

stats = {"found": 0, "checked": 0, "scraped": 0, "start": time.time()}
stats_lock = threading.Lock()

UA = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# ============================================================
# 🏨 HOTEL TAGS — Insecam'da aranacak etiketler
# ============================================================
HOTEL_TAGS = [
    # Doğrudan otel
    "hotel", "Hotel", "otel", "Otel", "motel", "Motel",
    "hostel", "Hostel", "resort", "Resort",
    # Otel alanları
    "lobby", "Lobby", "lobi", "Lobi",
    "reception", "Reception", "resepsiyon", "Resepsiyon",
    "corridor", "Corridor", "koridor", "Koridor",
    "entrance", "Entrance", "giris", "Giris",
    "restaurant", "Restaurant", "restoran", "Restoran",
    "bar", "Bar", "pool", "Pool", "havuz", "Havuz",
    "spa", "Spa", "gym", "Gym", "fitness", "Fitness",
    "parking", "Parking", "otopark", "Otopark",
    # Tatil yerleri
    "tatil", "Tatil", "holiday", "Holiday",
    "pansiyon", "Pansiyon", "apart", "Apart",
    # TR Tatil şehirleri
    "Antalya", "Bodrum", "Marmaris", "Fethiye",
    "Alanya", "Side", "Belek", "Kemer", "Kusadasi",
    "Cesme", "Didim", "Dalaman", "Mugla",
]

# ============================================================
# 🔍 ONLINE CHECK — IP gerçekten erişilebilir mi?
# ============================================================
def is_online(url, timeout=4):
    """Check if a camera URL is actually accessible."""
    try:
        resp = requests.get(url, timeout=timeout, verify=False,
                          headers={"User-Agent": random.choice(UA)},
                          allow_redirects=True)
        return resp.status_code < 500
    except:
        return False

def fast_port_check(ip, port, timeout=1.0):
    """Fast socket check."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((ip, port)) == 0
        s.close()
        return result
    except:
        return False

# ============================================================
# 📝 SAVE
# ============================================================
def save_camera(url, source_tag):
    with seen_lock:
        if url in seen_urls:
            return False
        seen_urls.add(url)
    
    with file_lock:
        with open(OUTPUT_FILE, "a") as f:
            f.write(f"{url}\n")
        # Also add to main findings
        with open("online_findings.txt", "a") as f:
            f.write(f"{url}\n")
    
    with stats_lock:
        stats["found"] += 1
    
    elapsed = time.time() - stats["start"]
    print(f"  🏨 [HOTEL] {url}")
    print(f"      Tag: \"{source_tag}\" | #{stats['found']} | {elapsed:.0f}s")
    return True

# ============================================================
# 🌐 INSECAM SCRAPER
# ============================================================
IP_PATTERN = re.compile(r'https?://(\d+\.\d+\.\d+\.\d+)(?::(\d+))?')

def scrape_insecam_page(url, session):
    """Scrape a single Insecam page and return found camera URLs."""
    found = []
    try:
        resp = session.get(url, timeout=15, headers={
            'User-Agent': random.choice(UA),
            'Referer': 'http://www.insecam.org/',
            'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
        })
        if resp.status_code != 200:
            return found
        
        # Extract all IP:port combinations
        matches = IP_PATTERN.findall(resp.text)
        for ip, port in matches:
            if not port:
                port = "80"
            cam_url = f"http://{ip}:{port}/"
            if "insecam.org" not in cam_url:
                found.append((cam_url, ip))
        
        with stats_lock:
            stats["scraped"] += len(found)
    except:
        pass
    return found

def verify_and_save(cam_url, ip, tag):
    """Verify camera is online and save."""
    with stats_lock:
        stats["checked"] += 1
    
    if is_online(cam_url):
        save_camera(cam_url, tag)

def scrape_tag(tag, session, max_pages=50):
    """Scrape all pages for a given tag."""
    all_cams = []
    
    # Try different URL patterns
    url_patterns = [
        f"http://www.insecam.org/en/bytag/{tag}/?page=",
        f"http://www.insecam.org/en/bytag/{tag}/TR/?page=",
    ]
    
    for base_url in url_patterns:
        for page in range(1, max_pages + 1):
            url = f"{base_url}{page}"
            cams = scrape_insecam_page(url, session)
            if not cams:
                break  # No more pages
            all_cams.extend([(cam, ip, tag) for cam, ip in cams])
            time.sleep(0.3)  # Polite delay
    
    return all_cams

# ============================================================
# 🚀 MAIN
# ============================================================
def print_banner():
    print("""
╔════════════════════════════════════════════════════════════════╗
║  🏨 ZenceFil Hotel Camera Scraper v2.0                        ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                                                                ║
║  Strateji: Insecam'ın etiketlediği OTEL kameralarını çek     ║
║  + Online olup olmadığını doğrula                             ║
║                                                                ║
║  Tags: hotel, otel, lobby, reception, resort, spa...          ║
║  📁 hotel_cameras.txt                                          ║
╚════════════════════════════════════════════════════════════════╝
    """)

def status_reporter():
    while True:
        time.sleep(20)
        elapsed = time.time() - stats["start"]
        print(f"\n  📊 [{elapsed:.0f}s] Scrape: {stats['scraped']} | "
              f"Kontrol: {stats['checked']} | "
              f"Online Hotel: {stats['found']} 🏨\n")

def main():
    print_banner()
    
    # Load existing
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            for line in f:
                url = line.strip()
                if url:
                    seen_urls.add(url)
        print(f"  📂 Mevcut {len(seen_urls)} kayıt yüklendi")
    
    threading.Thread(target=status_reporter, daemon=True).start()
    
    session = requests.Session()
    session.verify = False
    
    try:
        print(f"\n  🔍 {len(HOTEL_TAGS)} otel tag'i Insecam'dan çekiliyor...\n")
        
        all_cameras = []
        
        # Scrape each tag
        for i, tag in enumerate(HOTEL_TAGS):
            print(f"  🏷️  [{i+1}/{len(HOTEL_TAGS)}] Tag: \"{tag}\" taranıyor...")
            cams = scrape_tag(tag, session, max_pages=30)
            if cams:
                print(f"       → {len(cams)} kamera bulundu")
                all_cameras.extend(cams)
            
            # Verify found cameras in parallel as we go
            if len(all_cameras) >= 20:
                batch = all_cameras[:20]
                all_cameras = all_cameras[20:]
                with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
                    ex.map(lambda c: verify_and_save(c[0], c[1], c[2]), batch)
        
        # Verify remaining
        if all_cameras:
            print(f"\n  ✅ Kalan {len(all_cameras)} kamera doğrulanıyor...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
                ex.map(lambda c: verify_and_save(c[0], c[1], c[2]), all_cameras)
        
        # Also scrape by country TR
        print("\n  🇹🇷 Türkiye ülke sayfası taranıyor...")
        tr_cams = []
        for page in range(1, 100):
            url = f"http://www.insecam.org/en/bycountry/TR/?page={page}"
            cams = scrape_insecam_page(url, session)
            if not cams:
                break
            tr_cams.extend([(cam, ip, "TR-Country") for cam, ip in cams])
            time.sleep(0.2)
        
        print(f"  🇹🇷 TR sayfasından {len(tr_cams)} kamera bulundu → Doğrulanıyor...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as ex:
            ex.map(lambda c: verify_and_save(c[0], c[1], c[2]), tr_cams)
        
        elapsed = time.time() - stats["start"]
        print(f"\n  ✅ TAMAMLANDI!")
        print(f"  📊 Scrape: {stats['scraped']} | Kontrol: {stats['checked']} | Online: {stats['found']}")
        print(f"  ⏱️  Süre: {elapsed:.0f}s")
        print(f"  📁 {os.path.abspath(OUTPUT_FILE)}")
        
        if stats['found'] > 0:
            print(f"\n  🏨 BULUNAN OTEL KAMERALARI:")
            with open(OUTPUT_FILE) as f:
                for line in f:
                    print(f"     {line.strip()}")
    
    except KeyboardInterrupt:
        elapsed = time.time() - stats["start"]
        print(f"\n  🛑 Durduruldu. {stats['found']} otel kamerası bulundu.")
        print(f"  📁 {os.path.abspath(OUTPUT_FILE)}")

if __name__ == "__main__":
    main()
