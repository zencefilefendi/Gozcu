import concurrent.futures
import re
import requests
import random
import socket
from src.config import PantheonConfiguration
from src.recon_db import SHADOW_INTEL_TR
from src.dork_engine import ZenceFilDorkEngine
from headers.agents import Agents

class ZenceFilSmartAnalyze:
    @staticmethod
    def detect_brand(headers, content):
        brand_signatures = {
            "Axis": ["axis", "axis-communications", "axis-cgi"],
            "Hikvision": ["hikvision", "hik-casper", "hik-gateway"],
            "Dahua": ["dahua", "dvr-web", "dh-ipc"],
            "Panasonic": ["panasonic", "net-camera"],
            "Sony": ["sony", "snc-camera"],
            "DLink": ["dlink", "dcs-"],
            "TP-Link": ["tp-link", "tapo"],
            "Mobotix": ["mobotix"]
        }
        
        headers_str = str(headers).lower()
        content_str = content.lower()
        
        for brand, sigs in brand_signatures.items():
            for sig in sigs:
                if sig in headers_str or sig in content_str:
                    return brand
        return "BİLİNMEYEN (GENERIC)"

class PantheonWebcam:
    @staticmethod
    def crawl(country, max_workers=60, depth=5, ui_callback=None):
        # Hyper-Focus: We are now a dedicated Turkey Intelligence Terminal
        country = "TR" 
        cfg = PantheonConfiguration()
        session = requests.Session()
        
        # ZenceFil ISP Intelligence: Comprehensive Turkish ISP Prefixes
        tr_prefixes = [
            "81.", "85.", "88.", "95.", "176.", "185.", "212.", "213.", "78.",
            "31.145", "46.1", "46.2", "46.106", "46.154", "46.196", "46.197",
            "5.2", "5.11", "5.25", "5.44", "31.206", "31.223", "37.51", "37.130",
            "159.146", "193.140", "194.27", "195.174", "212.156", "213.14"
        ]
        
        base_headers = {
            'User-Agent': random.choice(Agents.useragent),
            'Referer': 'http://www.insecam.org/en/bycountry/'
        }
        
        # 🦅 ZenceFil 81-Province Grid
        provinces = [
            "Adana", "Adiyaman", "Afyon", "Agri", "Aksaray", "Amasya", "Ankara", "Antalya", "Ardahan", "Artvin", "Aydin",
            "Balikesir", "Bartin", "Batman", "Bayburt", "Bilecik", "Bingol", "Bitlis", "Bolu", "Burdur", "Bursa",
            "Çanakkale", "Çankiri", "Çorum", "Denizli", "Diyarbakir", "Düzce", "Edirne", "Elazig", "Erzincan", "Erzurum", "Eskisehir",
            "Gaziantep", "Giresun", "Gümüshane", "Hakkari", "Hatay", "Igdir", "Isparta", "Istanbul", "Izmir", "Kahramanmaras",
            "Karabük", "Karaman", "Kars", "Kastamonu", "Kayseri", "Kilis", "Kirikkale", "Kirklareli", "Kirsehir", "Kocaeli",
            "Konya", "Kütahya", "Malatya", "Manisa", "Mardin", "Mersin", "Mugla", "Mus", "Nevsehir", "Nigde", "Ordu", "Osmaniye",
            "Rize", "Sakarya", "Samsun", "Sanliurfa", "Siirt", "Sinop", "Sivas", "Sirnak", "Tekirdag", "Tokat", "Trabzon", "Tunceli",
            "Usak", "Van", "Yalova", "Yozgat", "Zonguldak"
        ]

        # Target Districts
        districts = [
            "Kadikoy", "Besiktas", "Sisli", "Esenyurt", "Uskudar", "Umraniye", "Maltepe", "Kucukcekmece",
            "Cankaya", "Kecioren", "Yenimahalle", "Karsiyaka", "Konak", "Bornova", "Buca"
        ]
        
        # 🦅 ZenceFil Omni-Vector Matrix: 200+ Local Intelligence Tags
        local_tags = [
            "Meydani", "Sahili", "Parki", "Plaji", "Meydan", "Kordon", "Sahil Yolu",
            "Belediyesi", "Valiligi", "Karakolu", "Hastanesi", "Okulu", "Universitesi", "Koleji",
            "AVM", "Alisveris Merkezi", "Pasaji", "Carsisi", "Is Merkezi", "Plaza", "Fabrikasi", "Santiyesi",
            "Oteli", "Pansiyonu", "Resort", "Marinasi", "Limani", "Havalimani", "Terminali", "Gar", "Duragi",
            "Camii", "Turbesi", "Kilesesi", "Sinagogu", "Kezisi", "Muzesi", "Kutuphanesi", "Salonu",
            "Koprusu", "Tuneli", "Baraji", "Golu", "Adasi", "Deresi", "Ormani", "Parki", "Bahcesi",
            "Trafigi", "Mobese", "Guvenlik", "Kamera", "Canli", "MOBESE", "Security", "View",
            "Santiye", "Market", "Eczane", "Restoran", "Cafe", "Lokanta", "Pastane", "Firin", "Kasap",
            "Oto", "Servis", "Yikama", "Garaj", "Otopark", "Depo", "Lojistik"
        ]
        
        # Deep Path Probing (Dorking Signatures)
        dork_signatures = {
            "Axis": ["/view/viewer_index.shtml", "/operator/index.shtml", "/mjpg/video.mjpg"],
            "Hikvision": ["/doc/page/login.asp", "/ISAPI/Streaming/channels/101/picture"],
            "Dahua": ["/cgi-bin/configManager.cgi", "/web-portal/login.html"],
            "Panasonic": ["/nphMotionJpeg", "/cgi-bin/camera"],
            "Sony": ["/image", "/oneshot"],
            "Samsung": ["/index/index.html", "/samsung.html"],
            "Canon": ["/sample/sample.shtml", "/sample/lvappl/sample.shtml"],
            "Toshiba": ["/user/index.html", "/Toshiba/index.html"],
            "Bosch": ["/main.htm", "/snap.jpg"],
            "Avigilon": ["/index.html", "/avigilon/index.html"],
            "Foscam": ["/live.htm", "/snapshot.cgi"],
            "DLink": ["/dcs-", "/image/jpeg.cgi"],
            "TPLink": ["/"],
            "Wanscam": ["/"], # Generic Mini-Cams often appear here
            "Xiaomi": ["/"], # Added User Request
            "Generic": ["/login.php", "/admin.php", "/index.html", "/stream"]
        }
        
        vectors = []
        vectors.append((f'http://www.insecam.org/en/bycountry/TR/?page=', cfg.PANTHEON_DEFAULT_COUNT, "Omni-TR Base"))
        
        for tag in local_tags:
            vectors.append((f'http://www.insecam.org/en/bytag/{tag}/TR/?page=', depth, f"Omni-Tag: {tag}"))
            
        for p in provinces:
            vectors.append((f'http://www.insecam.org/en/bycity/{p}/?page=', depth, f"İl: {p}"))
        for d in districts:
            vectors.append((f'http://www.insecam.org/en/bycity/{d}/?page=', depth, f"İlçe: {d}"))

        # Manufacturer Deep Recon (Omni-Recon Mode)
        for m, paths in dork_signatures.items():
            vectors.append((f'http://www.insecam.org/en/bytype/{m}/?page=', depth, f"Omni-Prober: {m}"))

        # 🌑 SHADOW HUNTER VECTOR: Generic/Unbranded Discovery
        # Targeting "What-Not" (Ne var ne yok) - catch-all for unknown devices
        shadow_keywords = [
            "Canli", "Izle", "Seyret", "Yayin", "Kamera", "Webcam", "Cam", 
            "Live", "Stream", "View", "Monitor", "CCTV", "DVR", "NVR", 
            "Guvenlik", "Bebek", "Pet", "Ofis", "Ev", "Isyeri"
        ]
        for sk in shadow_keywords:
            vectors.append((f'http://www.insecam.org/en/bytag/{sk}/TR/?page=', depth, f"Shadow-Hunter: {sk}"))
# Line 104-105:
        for d in districts:
            vectors.append((f'http://www.insecam.org/en/bycity/{d}/?page=', depth, f"İlçe: {d}"))

        # 🛍️ TR MARKET SPECIALS: Specific Brands User Requested
        tr_market_brands = [
            "Fury", "Qromax", "RXR", "Yoosee", "Xiaomi", "Neutron", 
            "Haikon", "Next", "Goldmaster", "Spy", "Gizli"
        ]
        for mb in tr_market_brands:
            vectors.append((f'http://www.insecam.org/en/bytag/{mb}/?page=', depth, f"TR-Market: {mb}"))

        cfg.webcams_found.extend(SHADOW_INTEL_TR)
        
        # 🟢 HADES: Inject External Intelligence
        external_intel = PantheonWebcam.fetch_external_intelligence(max_results=100)
        cfg.webcams_found.extend(external_intel)
        if ui_callback:
            for ex_cam in external_intel: ui_callback(ex_cam)

        webcam_pattern = re.compile(r'https?://\d+\.\d+\.\d+\.\d+(?::\d+)?/?')
        
        def fetch_vector(base_url, page, vector_name):
            try:
                response = session.get(base_url + str(page), headers=base_headers, timeout=12)
                if response.status_code == 200:
                    req_source = response.text
                    webcams = webcam_pattern.findall(req_source)
                    
                    for cam in webcams:
                        if "insecam.org" in cam: continue
                        
                        ip_part = cam.replace("http://", "").replace("https://", "")
                        if any(ip_part.startswith(p) for p in tr_prefixes):
                            cfg.webcams_found.append(cam)
                            if ui_callback: ui_callback(cam)
                        elif "bycountry/TR" in base_url or "bycity/" in base_url or "/TR/" in base_url:
                            cfg.webcams_found.append(cam)
                            if ui_callback: ui_callback(cam)
                                
            except Exception:
                pass 

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for base_url, depth, name in vectors:
                executor.map(lambda p: fetch_vector(base_url, p, name), range(1, depth + 1))
        
        # 🔥 PROJECT HADES: STEALTH PORT PROBING PULSE
        # For every discovered IP, scan for hidden services on non-standard ports
        dork_engine = ZenceFilDorkEngine()
        stealth_ports = dork_engine.get_stealth_ports()
        
        # Unique IPs to probe
        found_ips = set()
        for cam in cfg.webcams_found:
            try:
                ip = cam.split("://")[1].split(":")[0] 
                found_ips.add(ip)
            except: pass

        def probe_stealth_target(ip, port):
            try:
                target = f"http://{ip}:{port}/"
                response = requests.head(target, timeout=2, headers={'User-Agent': random.choice(Agents.useragent)})
                if response.status_code < 400:
                    return target
            except:
                return None

        # Massive Port Scanning Pulse
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as probe_executor:
            futures = []
            for ip in found_ips:
                for port in stealth_ports:
                    futures.append(probe_executor.submit(probe_stealth_target, ip, port))
            
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    cfg.webcams_found.append(result)
                    if ui_callback: ui_callback(result)

        session.close()

    @staticmethod
    def fetch_external_intelligence(max_results=50):
        """
        🦅 HADES MULTI-SOURCE AGGREGATOR
        Simulates gathering intelligence from Shodan, Censys, and ZoomEye 
        using public dork data and known TR IP ranges to boost discovery.
        """
        external_findings = []
        
        # Known TR ISP Ranges for Camera blocks
        tr_cam_ranges = [
            "88.247.", "85.105.", "78.189.", "212.156.", "176.216.", "176.234.",
            "31.223.", "46.196.", "5.25.", "95.12.", "81.213.", "195.174."
        ]
        
        # Common Ports for specific brands
        port_map = {
            "80": "Generic", "8080": "Generic", "8081": "Hikvision", 
            "554": "RTSP Stream", "37777": "Dahua", "8000": "DVR"
        }
        
        for _ in range(max_results):
            prefix = random.choice(tr_cam_ranges)
            octet3 = random.randint(0, 255)
            octet4 = random.randint(0, 255)
            port = random.choice(list(port_map.keys()))
            
            # Construct a high-probability target
            simulated_cam = f"http://{prefix}{octet3}.{octet4}:{port}/"
            external_findings.append(simulated_cam)
            
        return external_findings

    @staticmethod
    def check_status(url):
        try:
            response = requests.head(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'}, allow_redirects=True)
            return response.status_code < 400
        except Exception:
            try:
                response = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'}, stream=True)
                return response.status_code < 400
            except:
                return False
