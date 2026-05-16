#!/usr/bin/env python3
"""
🚀 ZenceFil TURBO Axis Scanner (AsyncIO)
==========================================
Geleneksel threading yavaştır. AsyncIO ile saniyede
binlerce istek atarak gerçek zamanlı sonuç alacağız.

Özellikler:
- AsyncIO + Aiohttp: Non-blocking I/O
- Rate Limit Yok: Saniyede 1000+ Tarama
- Akıllı Timeout: 0.5s (Cevap vermeyen ölüdür)
- Hedef: Türk ISP Blokları + Bilinen Kamera Portları

Kullanım: python3 turbo_axis_scanner.py
"""

import asyncio
import aiohttp
import random
import ipaddress
import os
import time
import sys

# ============================================================
# CONFIG
# ============================================================
OUTPUT_FILE = "axis_cameras.txt"
CONCURRENCY = 2000  # 💥 2000 Eşzamanlı İstek!
TIMEOUT = 0.5       # Çok agresif timeout

# Türk ISP Blokları (Özet)
TR_NETS = [
    "78.186.0.0/16", "88.224.0.0/15", "95.0.0.0/12", 
    "176.214.0.0/15", "46.196.0.0/15", "85.96.0.0/13",
    "81.212.0.0/14", "212.156.0.0/14", "195.174.0.0/16"
]

# Axis Fingerprints
AXIS_PATHS = ["/", "/view/view.shtml", "/indexFrame.shtml"]
AXIS_SIGS = ["axis", "Axis Communications", "Live View / - AXIS"]

# Stats
stats = {"scanned": 0, "axis": 0, "start": time.time()}

# ============================================================
# 🎲 IP GENERATOR
# ============================================================
def get_random_tr_ip():
    """Rastgele bir Türk IP'si üretir."""
    net = random.choice(TR_NETS)
    network = ipaddress.IPv4Network(net)
    # Bu network içinden rastgele bir IP seç
    random_int = random.randint(0, network.num_addresses - 1)
    return str(network[0] + random_int)

# ============================================================
# 🎯 ASYNC SCANNER
# ============================================================
async def check_ip(session, ip, port=80):
    url = f"http://{ip}:{port}/"
    try:
        async with session.get(url, timeout=TIMEOUT, allow_redirects=True) as resp:
            stats["scanned"] += 1
            
            # 1. Hızlı Header Kontrolü
            server = resp.headers.get("Server", "").lower()
            auth = resp.headers.get("WWW-Authenticate", "").lower()
            
            if "axis" in server or "axis" in auth:
                return url, "Header: Axis"
            
            # 2. Hızlı Body Kontrolü (İlk 1KB)
            body = await resp.content.read(1024)
            body_str = body.decode("utf-8", errors="ignore").lower()
            
            for sig in AXIS_SIGS:
                if sig.lower() in body_str:
                    return url, f"Body: {sig}"
                    
            # 3. Title Check
            if "<title>" in body_str and "axis" in body_str.split("<title>")[1].split("</title>")[0]:
                return url, "Title: Axis"
                
    except:
        pass
    return None, None

async def worker(queue, session):
    while True:
        ip = await queue.get()
        # En yaygın portlar: 80, 8080
        for port in [80, 8080]:
            url, evidence = await check_ip(session, ip, port)
            if url:
                print(f"  🎯 BULUNDU: {url} ({evidence})")
                with open(OUTPUT_FILE, "a") as f:
                    f.write(f"{url} # {evidence}\n")
                stats["axis"] += 1
        queue.task_done()

async def main():
    print(f"""
    🚀 ZenceFil TURBO Axis Scanner başlatılıyor...
    🔥 Hedef: {len(TR_NETS)} Türk ISP Bloğu
    ⚡ Hız: {CONCURRENCY} Thread (AsyncIO)
    📂 {OUTPUT_FILE}
    """)
    
    # Queue doldurucu
    queue = asyncio.Queue()
    
    # 2000 IP'yi sürekli kuyruğa ekle
    async def queue_filler():
        while True:
            if queue.qsize() < CONCURRENCY * 2:
                for _ in range(100):
                    queue.put_nowait(get_random_tr_ip())
            await asyncio.sleep(0.1)
            
    # Status reporter
    async def reporter():
        while True:
            await asyncio.sleep(10)
            elapsed = time.time() - stats["start"]
            rate = stats["scanned"] / elapsed
            print(f"  📊 Hız: {rate:.0f} scan/s | Toplam: {stats['scanned']} | Axis: {stats['axis']}")

    # Bağlantı havuzu
    connector = aiohttp.TCPConnector(limit=None, ttl_dns_cache=300)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Worker'ları başlat
        tasks = []
        for _ in range(CONCURRENCY):
            task = asyncio.create_task(worker(queue, session))
            tasks.append(task)
            
        asyncio.create_task(queue_filler())
        asyncio.create_task(reporter())
        
        # Sonsuza kadar çalış
        await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Durduruldu.")
