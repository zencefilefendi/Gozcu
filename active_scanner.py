#!/usr/bin/env python3
"""
🦅 ZenceFil Active ISP Scanner v1.0
====================================
Dahice Plan: Insecam'e bağımlı kalmak yerine, doğrudan Türk ISP IP bloklarını
tarayarak açık kamera portlarını tespit eder.

Her bulunan ONLINE hedef anında online_findings.txt'ye yazılır.

Kullanım: python3 active_scanner.py
"""

import socket
import random
import concurrent.futures
import threading
import time
import os
import sys

# ============================================================
# 🦅 TURKISH ISP IP RANGES (CIDR -> Prefix)
# These are real, allocated Turkish ISP blocks
# ============================================================
TR_ISP_RANGES = [
    # Turk Telekom
    ("78.160.0.0", "78.191.255.255"),
    ("81.212.0.0", "81.215.255.255"),
    ("85.96.0.0", "85.111.255.255"),
    ("88.224.0.0", "88.255.255.255"),
    ("95.0.0.0", "95.15.255.255"),
    # Superonline
    ("176.214.0.0", "176.239.255.255"),
    ("31.223.0.0", "31.223.255.255"),
    # Vodafone TR
    ("46.1.0.0", "46.1.255.255"),
    ("46.196.0.0", "46.197.255.255"),
    # Other TR ISPs
    ("5.24.0.0", "5.27.255.255"),
    ("5.44.0.0", "5.47.255.255"),
    ("212.154.0.0", "212.159.255.255"),
    ("213.14.0.0", "213.15.255.255"),
    ("159.146.0.0", "159.146.255.255"),
    ("195.174.0.0", "195.175.255.255"),
    ("37.130.0.0", "37.131.255.255"),
]

# Common camera/IoT ports
CAMERA_PORTS = [80, 81, 82, 83, 84, 85, 88, 8000, 8080, 8081, 8090, 8888, 554, 37777, 34567]

# Output file
OUTPUT_FILE = "online_findings.txt"

# Thread-safe lock for file writing
file_lock = threading.Lock()

# Stats
stats = {
    "scanned": 0,
    "found": 0,
    "start_time": time.time()
}
stats_lock = threading.Lock()


def ip_to_int(ip):
    """Convert IP string to integer."""
    parts = ip.split(".")
    return (int(parts[0]) << 24) + (int(parts[1]) << 16) + (int(parts[2]) << 8) + int(parts[3])


def int_to_ip(num):
    """Convert integer to IP string."""
    return f"{(num >> 24) & 255}.{(num >> 16) & 255}.{(num >> 8) & 255}.{num & 255}"


def generate_random_tr_ip():
    """Generate a random IP from Turkish ISP ranges."""
    start_ip, end_ip = random.choice(TR_ISP_RANGES)
    start_int = ip_to_int(start_ip)
    end_int = ip_to_int(end_ip)
    random_int = random.randint(start_int, end_int)
    return int_to_ip(random_int)


def probe_target(ip, port, timeout=1.5):
    """
    Probe a single IP:port combination using socket connect.
    Returns the URL if the port is open, None otherwise.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        
        if result == 0:
            return f"http://{ip}:{port}/"
        return None
    except:
        return None


def scan_ip(ip):
    """Scan a single IP across all camera ports."""
    results = []
    for port in CAMERA_PORTS:
        url = probe_target(ip, port)
        if url:
            results.append(url)
            
            # Write to file immediately (thread-safe)
            with file_lock:
                with open(OUTPUT_FILE, "a") as f:
                    f.write(f"{url}\n")
            
            # Update stats
            with stats_lock:
                stats["found"] += 1
            
            # Print to console in real-time
            elapsed = time.time() - stats["start_time"]
            print(f"  🟢 [ONLINE] {url}  (Toplam: {stats['found']} | Süre: {elapsed:.0f}s)")
    
    with stats_lock:
        stats["scanned"] += 1
    
    return results


def print_banner():
    """Print the scanner banner."""
    print("""
╔══════════════════════════════════════════════════════════╗
║  🦅 ZenceFil Active ISP Scanner v1.0                    ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║  Türk ISP IP Bloklarını Aktif Olarak Tarıyor...         ║
║  Bulunan hedefler: online_findings.txt                  ║
║  Ctrl+C ile durdurun                                    ║
╚══════════════════════════════════════════════════════════╝
    """)


def print_status():
    """Print periodic status updates."""
    while True:
        time.sleep(15)
        elapsed = time.time() - stats["start_time"]
        rate = stats["scanned"] / max(elapsed, 1) * 60  # per minute
        print(f"\n  📊 DURUM: {stats['scanned']} IP tarandı | {stats['found']} hedef bulundu | Hız: {rate:.0f} IP/dk | Süre: {elapsed:.0f}s\n")


def main():
    print_banner()
    
    # Number of concurrent workers
    max_workers = 200
    # Total IPs to scan per batch
    batch_size = 500
    
    # Start status thread
    status_thread = threading.Thread(target=print_status, daemon=True)
    status_thread.start()
    
    print(f"  ⚡ {max_workers} thread ile tarama başlıyor...")
    print(f"  📁 Sonuçlar: {os.path.abspath(OUTPUT_FILE)}")
    print(f"  🎯 Hedef Portlar: {CAMERA_PORTS}")
    print(f"  🌍 TR ISP Blokları: {len(TR_ISP_RANGES)} aralık\n")
    
    try:
        batch_num = 0
        while True:
            batch_num += 1
            # Generate random IPs from TR ranges
            ips = [generate_random_tr_ip() for _ in range(batch_size)]
            
            print(f"  🔄 Batch #{batch_num}: {batch_size} yeni IP taranıyor...")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                executor.map(scan_ip, ips)
            
            print(f"  ✅ Batch #{batch_num} tamamlandı. Toplam bulunan: {stats['found']}")
            
    except KeyboardInterrupt:
        elapsed = time.time() - stats["start_time"]
        print(f"\n\n  🛑 Tarama durduruldu.")
        print(f"  📊 SONUÇ: {stats['scanned']} IP tarandı | {stats['found']} ONLINE hedef bulundu")
        print(f"  ⏱️  Süre: {elapsed:.0f} saniye")
        print(f"  📁 Kayıt: {os.path.abspath(OUTPUT_FILE)}")
        sys.exit(0)


if __name__ == "__main__":
    main()
