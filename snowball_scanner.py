#!/usr/bin/env python3
"""
🦅 ZenceFil SNOWBALL Discovery Engine v3.0
=============================================
DAHİCE PLAN: Rastgele IP taramak yetersiz kaldı.

KARTOPU STRATEJİSİ (Snowball):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Bilinen kameraları "tohum" (seed) olarak kullan
2. Her tohumun /24 subnet komşularını tara (256 IP)
3. Yeni kamera bulununca, ONUN da /24 bloğunu kuyruğa ekle
4. Zincirleme reaksiyon: Her keşif → yeni keşiflere yol açar

NEDEN ÇALIŞIR?
- Kameralar kümelenmiş olur (aynı ISP, aynı mahalle, aynı bina)
- Bir apartman/iş merkezinde 1 kamera varsa, komşularında da vardır
- ISP'ler belirli /24 bloklarını CCTV altyapısına tahsis eder

HIZLI TARAMA:
- Sadece 3 kritik port: 80, 8080, 554 (hız odaklı)
- Socket timeout: 0.8s (agresif)
- 200 thread paralel
- HTTP header analizi ile kamera doğrulama

Kullanım: python3 snowball_scanner.py
"""

import socket
import requests
import concurrent.futures
import threading
import time
import random
import os
import sys

# ============================================================
# CONFIG
# ============================================================
OUTPUT_FILE = "online_findings.txt"
file_lock = threading.Lock()
seen_lock = threading.Lock()
seen_ips = set()        # Already checked individual IPs
seen_subnets = set()    # Already scanned /24 blocks
subnet_queue = []       # Queue of /24 subnets to scan
queue_lock = threading.Lock()

stats = {"scanned": 0, "found": 0, "subnets": 0, "start": time.time()}
stats_lock = threading.Lock()

# Only 3 critical camera ports for SPEED
FAST_PORTS = [80, 8080, 554]

# Extended ports for deeper scan of confirmed hosts
DEEP_PORTS = [81, 82, 83, 84, 85, 88, 443, 8000, 8001, 8081, 8090, 8888, 37777, 34567, 9000, 50001, 60001]

# Camera detection keywords
CAM_KEYWORDS = [
    b"camera", b"webcam", b"dvr", b"nvr", b"cctv", b"hikvision", b"dahua",
    b"login", b"video", b"stream", b"viewer", b"snapshot", b"axis",
    b"foscam", b"goahead", b"boa", b"jaws", b"thttpd", b"mini_httpd",
    b"onvif", b"rtsp", b"ipc", b"surveillance", b"net cam",
    b"fury", b"qromax", b"yoosee", b"neutron", b"haikon", b"xmeye",
    b"kamera", b"canli", b"izle", b"guvenlik",
    b"realm=", b"digest", b"web service", b"p2p", b"ddns",
    b"channel", b"recording", b"playback", b"ptz",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
]

# ============================================================
# 🇹🇷 TR IP PREFIX WHITELIST
# ============================================================
TR_PREFIXES = [
    "78.16", "78.17", "78.18", "78.19",
    "81.21", "85.9", "85.10", "85.11",
    "88.2", "95.",
    "176.21", "176.22", "176.23", "31.223",
    "46.1", "46.19", "46.2",
    "5.2", "5.4", "37.1", "37.5",
    "159.146", "193.140", "194.27",
    "195.17", "212.1", "212.17", "213.1",
    "31.14", "31.20", "46.10", "46.15",
]

def is_tr_ip(ip):
    return any(ip.startswith(p) for p in TR_PREFIXES)

# ============================================================
# 📝 SAVE (Thread-Safe, Deduplicated, TR-Only)
# ============================================================
def save_finding(url, source=""):
    ip = url.replace("http://","").replace("https://","").split(":")[0].split("/")[0]
    
    if not is_tr_ip(ip):
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
    print(f"  🇹🇷 [{source}] {url}  (#{stats['found']} | {elapsed:.0f}s)")
    
    # 🧊 SNOWBALL: Add this IP's /24 subnet to the queue!
    subnet = ".".join(ip.split(".")[:3])
    with queue_lock:
        if subnet not in seen_subnets:
            subnet_queue.append(subnet)
            print(f"      ⛓️ Yeni subnet kuyruğa eklendi: {subnet}.0/24")
    
    return True

# ============================================================
# 🔍 FAST PORT CHECK (Socket Only)
# ============================================================
def fast_port_check(ip, port, timeout=0.8):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False

# ============================================================
# 🎯 CAMERA VERIFY (HTTP Header + Content)
# ============================================================
def verify_is_camera(ip, port):
    """Check if an IP:port is actually a camera via HTTP."""
    url = f"http://{ip}:{port}/"
    try:
        resp = requests.get(url, timeout=3, verify=False, stream=True,
                          headers={"User-Agent": random.choice(USER_AGENTS)},
                          allow_redirects=True)
        
        if resp.status_code >= 400:
            return None
        
        # Read headers + first 2KB
        raw_headers = str(resp.headers).lower().encode()
        raw_body = resp.raw.read(2048)
        combined = raw_headers + raw_body.lower()
        
        for kw in CAM_KEYWORDS:
            if kw in combined:
                return url
        
        # Non-standard port is already suspicious if it responds
        if port not in [80, 443]:
            return url
            
    except:
        pass
    return None

# ============================================================
# 🧊 SCAN A SINGLE IP (Fast 3-Port + Verify)
# ============================================================
def scan_single_ip(ip):
    with stats_lock:
        stats["scanned"] += 1
    
    for port in FAST_PORTS:
        if fast_port_check(ip, port):
            result = verify_is_camera(ip, port)
            if result:
                save_finding(result, f"Port {port}")
                
                # Deep scan: check other ports too
                for dp in DEEP_PORTS:
                    if fast_port_check(ip, dp, timeout=0.5):
                        deep_result = verify_is_camera(ip, dp)
                        if deep_result:
                            save_finding(deep_result, f"Deep:{dp}")
                return  # Found on this IP, move on

# ============================================================
# 🧊 SCAN ENTIRE /24 SUBNET
# ============================================================
def scan_subnet(subnet_prefix):
    """Scan all 256 IPs in a /24 subnet."""
    with stats_lock:
        stats["subnets"] += 1
    
    with queue_lock:
        seen_subnets.add(subnet_prefix)
    
    ips = [f"{subnet_prefix}.{i}" for i in range(1, 255)]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
        ex.map(scan_single_ip, ips)

# ============================================================
# 🌱 SEED IPS: Starting Points
# ============================================================
SEED_IPS = [
    # From our previous discoveries
    "78.186.26.188", "78.186.67.194", "95.9.143.108", "95.9.96.3",
    "213.153.223.2", "81.213.28.143", "88.249.83.194", "212.154.81.65",
    "195.175.57.190", "85.99.249.21", "95.6.39.37", "81.213.140.154",
    "88.212.33.173", "95.154.28.198", "95.169.71.161",
    # Known Turkish camera-dense subnets (ISP infrastructure blocks)
    "78.186.100.1", "78.186.150.1", "78.186.200.1",
    "78.189.50.1", "78.189.100.1", "78.189.150.1", "78.189.200.1",
    "85.105.50.1", "85.105.100.1", "85.105.150.1",
    "88.247.50.1", "88.247.100.1", "88.247.150.1",
    "95.2.50.1", "95.2.100.1", "95.2.150.1", "95.2.200.1",
    "95.5.50.1", "95.5.100.1", "95.5.150.1",
    "95.7.50.1", "95.7.100.1", "95.7.150.1",
    "95.8.50.1", "95.8.100.1", "95.12.50.1",
    "176.216.50.1", "176.216.100.1", "176.234.50.1", "176.234.100.1",
    "212.156.50.1", "212.156.100.1", "212.174.50.1", "212.174.100.1",
    "31.223.50.1", "31.223.100.1", "31.223.150.1",
    "46.196.50.1", "46.196.100.1",
    "5.25.50.1", "5.25.100.1", "5.26.50.1", "5.26.100.1",
]

# ============================================================
# 🚀 MAIN
# ============================================================
def print_banner():
    print("""
╔════════════════════════════════════════════════════════════════╗
║  🧊 ZenceFil SNOWBALL Discovery Engine v3.0                   ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                                                                ║
║  DAHİCE PLAN: Kartopu Stratejisi                              ║
║  ┌─────────────────────────────────────────────────────┐      ║
║  │ 1. Bilinen kameralardan başla (tohum)               │      ║
║  │ 2. /24 subnet komşularını tara                      │      ║
║  │ 3. Yeni kamera bul → ONUN bloğunu da kuyruğa ekle  │      ║
║  │ 4. Zincirleme reaksiyon → KARTOPU büyür! ❄️         │      ║
║  └─────────────────────────────────────────────────────┘      ║
║                                                                ║
║  🇹🇷 SADECE Türk IP'leri | 📁 online_findings.txt             ║
║  Ctrl+C ile durdurun                                           ║
╚════════════════════════════════════════════════════════════════╝
    """)

def status_reporter():
    while True:
        time.sleep(15)
        elapsed = time.time() - stats["start"]
        with queue_lock:
            q_size = len(subnet_queue)
        print(f"\n  📊 [{elapsed:.0f}s] Tarandı: {stats['scanned']} IP | "
              f"Bulunan: {stats['found']} kamera | "
              f"Subnetler: {stats['subnets']} tamamlandı | "
              f"Kuyruk: {q_size} bekliyor\n")


def main():
    print_banner()
    
    # Load existing
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    seen_ips.add(line)
        print(f"  📂 Mevcut {len(seen_ips)} kayıt yüklendi")
    
    # Status thread
    threading.Thread(target=status_reporter, daemon=True).start()
    
    # ═══════════════════════════════════════════
    # PHASE 1: SEED - Tohumlardan /24 subnet'leri oluştur
    # ═══════════════════════════════════════════
    print(f"\n  🌱 PHASE 1: {len(SEED_IPS)} tohum IP'den subnet'ler oluşturuluyor...")
    
    for seed_ip in SEED_IPS:
        subnet = ".".join(seed_ip.split(".")[:3])
        if subnet not in seen_subnets:
            subnet_queue.append(subnet)
    
    print(f"  📋 {len(subnet_queue)} benzersiz /24 subnet kuyruğa alındı")
    print(f"  🎯 Toplam hedef: ~{len(subnet_queue) * 254} IP adresi")
    print("  " + "─" * 55)
    
    try:
        # ═══════════════════════════════════════════
        # PHASE 2: SNOWBALL - Subnet'leri tara, yenilerini ekle
        # ═══════════════════════════════════════════
        print(f"\n  🧊 PHASE 2: Kartopu taraması başlıyor...\n")
        
        while True:
            # Get next subnet from queue
            with queue_lock:
                if subnet_queue:
                    current_subnet = subnet_queue.pop(0)
                else:
                    # Queue empty — generate random TR subnets to keep going
                    tr_ranges_flat = [
                        (78, range(160,192)), (81, range(212,216)),
                        (85, range(96,112)), (88, range(224,256)),
                        (95, range(0,16)), (176, range(214,240)),
                        (212, range(154,160)), (213, range(14,16)),
                    ]
                    first, seconds = random.choice(tr_ranges_flat)
                    second = random.choice(seconds)
                    third = random.randint(0, 255)
                    current_subnet = f"{first}.{second}.{third}"
                    
            if current_subnet in seen_subnets:
                continue
            
            print(f"  🔍 Subnet taranıyor: {current_subnet}.0/24 (kuyrukta: {len(subnet_queue)})")
            scan_subnet(current_subnet)
    
    except KeyboardInterrupt:
        elapsed = time.time() - stats["start"]
        print(f"\n\n  🛑 Tarama durduruldu.")
        print(f"  📊 SONUÇ:")
        print(f"     {stats['scanned']} IP tarandı")
        print(f"     {stats['found']} ONLINE TR kamera bulundu")
        print(f"     {stats['subnets']} subnet tamamlandı")
        print(f"  ⏱️  Süre: {elapsed:.0f} saniye")
        print(f"  📁 Kayıt: {os.path.abspath(OUTPUT_FILE)}")


if __name__ == "__main__":
    main()
