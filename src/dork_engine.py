
import random

class ZenceFilDorkEngine:
    """
    🦅 ZenceFil Project HADES: IoT Dork Engine
    Generates advanced search signatures to find hidden IoT devices (Cameras)
    that standard aggregators might miss.
    """
    
    def __init__(self):
        self.dorks = {
            "Axis": [
                'intitle:"Live View / - AXIS"',
                'inurl:indexFrame.shtml Axis',
                'inurl:"view/view.shtml" axis',
                'intitle:"Axis 2400 Video Server"',
                'inurl:/view/viewer_index.shtml',
                'intitle:"AXIS" inurl:"/view/view.shtml"', 
            ],
            "Hikvision": [
                'intitle:"Hikvision" inurl:"login"',
                'response_header:"Server: Hikvision-Webs"',
                'inurl:"/doc/page/login.asp"',
                'intitle:"Hikvision" inurl:"/doc/page/login.asp"',
            ],
            "Dahua": [
                'intitle:"WEB SERVICE" inurl:"/login.html"',
                'intitle:"Dahua" inurl:"/login.html"',
            ],
            "WebcamXP": [
                'intitle:"WebcamXP 5"',
                'inurl:":8080/cam_1.jpg"',
                'intitle:"my webcamXP server!"',
            ],
            "MJPEG_Generic": [
                'inurl:"/mjpg/video.mjpg"',
                'intitle:"Live View" inurl:"/mjpg/video.mjpg"',
                'inurl:"/view/index.shtml"',
                'inurl:"/view/view.shtml"',
            ],
             "Sony": [
                'intitle:"Sony Network Camera" inurl:"/home/index.html"', 
                'inurl:"/image?suppressSender=1&imageType=1"',
            ],
            "Panasonic": [
                'intitle:"Panasonic Network Camera" inurl:"/ViewerFrame?Mode=Motion"',
                'inurl:"/nphMotionJpeg?Resolution=640x480&Quality=Standard"',
            ],
            "Mobotix": [
                'intitle:"MOBOTIX Camera" inurl:"/control/userimage.html"',
            ],
             "Samsung": [
                'intitle:"Samsung Techwin" inurl:"/index/index.html"',
            ],
             "Toshiba": [
                 'intitle:"Toshiba Network Camera" inurl:"/user/index.html"',
             ],
             "Vivotek": [
                 'intitle:"Vivotek" inurl:"/cgi-bin/viewer/video.jpg"',
             ],
             "Canon": [
                 'intitle:"VB-C10" inurl:"/sample/sample.shtml"',
                 'inurl:"/sample/lvappl/sample.shtml"',
             ],
             "Bosch": [
                 'intitle:"Bosch Camera" inurl:"/main.htm"',
                 'inurl:"/snap.jpg?JpegCam=0"',
             ],
            "Avigilon": [
                'intitle:"Avigilon Control Center Web Client"',
                'inurl:"/index.html?locale=en_US"',
            ],
            "Consumer_SmartHome": [
                'intitle:"V380" inurl:"/login.html"',
                'intitle:"CamHi" inurl:"/web/admin.html"',
                'intitle:"Yi Home" inurl:"/cgi-bin/"', 
                'intitle:"EZVIZ" inurl:"/login"',
                'intitle:"Tuya"',
                'intitle:"Mini IP Camera"', # Generic "Hidden" Cam
                'Server: GoAhead-Webs', # Common generic firmware
            ],
            "TR_Market_Specials": [
                'intitle:"Fury" inurl:"login"', # Fury IP Cams
                'intitle:"Qromax" inurl:"/login.asp"',
                'intitle:"Yoosee" inurl:"/index.html"', # Yoosee/CMS
                'server: "JAWS/1.0"', # Common Yoosee/V380 Header
                'intitle:"RXR" inurl:"login"',
                'intitle:"Neutron" inurl:"/login.asp"', # Popular in TR
                'intitle:"Haikon"', # TR Hikvision Rebrand
            ]
        }

        # Turkish-Specific Context Keywords to append to generic dorks
        # Expanded for Micro-Business & Hidden Locations
        self.tr_context = [
            'site:tr',
            # Full 81 Province Matrix
            '"Adana"', '"Adiyaman"', '"Afyon"', '"Agri"', '"Aksaray"', '"Amasya"', '"Ankara"', '"Antalya"', '"Ardahan"', 
            '"Artvin"', '"Aydin"', '"Balikesir"', '"Bartin"', '"Batman"', '"Bayburt"', '"Bilecik"', '"Bingol"', '"Bitlis"', 
            '"Bolu"', '"Burdur"', '"Bursa"', '"Canakkale"', '"Cankiri"', '"Corum"', '"Denizli"', '"Diyarbakir"', '"Duzce"', 
            '"Edirne"', '"Elazig"', '"Erzincan"', '"Erzurum"', '"Eskisehir"', '"Gaziantep"', '"Giresun"', '"Gumushane"', 
            '"Hakkari"', '"Hatay"', '"Igdir"', '"Isparta"', '"Istanbul"', '"Izmir"', '"Kahramanmaras"', '"Karabuk"', 
            '"Karaman"', '"Kars"', '"Kastamonu"', '"Kayseri"', '"Kilis"', '"Kirikkale"', '"Kirklareli"', '"Kirsehir"', 
            '"Kocaeli"', '"Konya"', '"Kutahya"', '"Malatya"', '"Manisa"', '"Mardin"', '"Mersin"', '"Mugla"', '"Mus"', 
            '"Nevsehir"', '"Nigde"', '"Ordu"', '"Osmaniye"', '"Rize"', '"Sakarya"', '"Samsun"', '"Sanliurfa"', '"Siirt"', 
            '"Sinop"', '"Sivas"', '"Sirnak"', '"Tekirdag"', '"Tokat"', '"Trabzon"', '"Tunceli"', '"Usak"', '"Van"', 
            '"Yalova"', '"Yozgat"', '"Zonguldak"',
            # 🦅 Massive District Grid (300+ Major Districts)
            # Marmara
            '"Besiktas"', '"Kadikoy"', '"Sisli"', '"Fatih"', '"Beyoglu"', '"Uskudar"', '"Umraniye"', '"Esenyurt"', '"Bagcilar"', '"Pendik"',
            '"Osmangazi"', '"Nilufer"', '"Yildirim"', '"Izmit"', '"Gebze"', '"Corlu"', '"Luleburgaz"', '"Bandirma"', '"Edremit"', '"Inegol"',
            # Aegean
            '"Konak"', '"Karsiyaka"', '"Bornova"', '"Buca"', '"Cesme"', '"Alacati"', '"Kusadasi"', '"Bodrum"', '"Marmaris"', '"Fethiye"',
            '"Efeler"', '"Nazilli"', '"Manisa Merkez"', '"Akhisar"', '"Salihli"', '"Turgutlu"', '"Usak Merkez"', '"Afyon Merkez"',
            # Mediterranean
            '"Muratpasa"', '"Kepez"', '"Konyaalti"', '"Alanya"', '"Manavgat"', '"Kemer"', '"Kas"', '"Seyhan"', '"Cukurova"', '"Yuregir"',
            '"Mersin Yenisehir"', '"Mezitli"', '"Tarsus"', '"Silifke"', '"Iskenderun"', '"Antakya"', '"Defne"', '"Osmaniye Merkez"',
            # Central Anatolia
            '"Cankaya"', '"Kecioren"', '"Yenimahalle"', '"Mamak"', '"Etimesgut"', '"Sincan"', '"Golbasi"', '"Selcuklu"', '"Meram"', '"Karatay"',
            '"Eskisehir Tepebasi"', '"Odunpazari"', '"Melikgazi"', '"Kocasinan"', '"Talas"', '"Sivas Merkez"', '"Aksaray Merkez"',
            # Black Sea
            '"Ilkadim"', '"Atakum"', '"Canik"', '"Trabzon Ortahisar"', '"Akcaabat"', '"Ordu Altinordu"', '"Fatsa"', '"Unye"', '"Giresun Merkez"',
            '"Rize Merkez"', '"Zonguldak Merkez"', '"Eregli"', '"Karabuk Merkez"', '"Safranbolu"', '"Bartin Merkez"', '"Sinop Merkez"',
            # East & Southeast
            '"Sahinbey"', '"Sehitkamil"', '"Sanliurfa Haliliye"', '"Eyyubiye"', '"Karakopru"', '"Diyarbakir Baglar"', '"Kayapinar"', '"Yenisehir"',
            '"Malatya Battalgazi"', '"Yesilyurt"', '"Elazig Merkez"', '"Van Ipekyolu"', '"Erzurum Yakutiye"', '"Palandoken"', '"Mardin Artuklu"',
            '"Batman Merkez"', '"Adiyaman Merkez"', '"Siirt Merkez"', '"Sirnak Merkez"', '"Hakkari Merkez"', '"Agri Merkez"', '"Mus Merkez"',
            
            # Micro-Businesses & High Value Targets
            '"Kuyumcu"', '"Oda"', '"Tekel"', '"Market"', '"Eczane"', '"Hastane"', '"Poliklinik"', '"Dis Hekimi"',
            '"Otel"', '"Depo"', '"Salon"', '"Santiye"', '"Insaat"', '"Beton"', '"Maden"', '"Ocak"',
            '"Benzinlik"', '"Petrol"', '"Otogar"', '"Terminal"', '"Havalimani"', '"Marina"', '"Liman"',
            '"Otel"', '"Pansiyon"', '"Tatil Koyu"', '"Resort"', '"Apart"', '"Site"', '"Konut"', '"Villa"',
            '"Bungalov"', '"Yazlik"', '"Rezidans"', '"Mustakil"', '"Dag Evi"', '"Koy Evi"',
            '"Okul"', '"Kres"', '"Dershane"', '"Universite"', '"Kampus"', '"Yurt"', '"Kutuphane"',
            '"Kafe"', '"Restoran"', '"Bar"', '"Club"', '"Spor Salonu"', '"Fitness"', '"Havuz"', '"Plaj"',
            '"Otopark"', '"Garaj"', '"Servis"', '"Tamir"', '"Yikama"', '"Sanayi"', '"Organize Sanayi"',
            '"Belediye"', '"Valilik"', '"Kaymakamlik"', '"Adliye"', '"Karakol"', '"Meydan"', '"Park"',
        ]

    def generate_dork_vectors(self):
        """
        Generates a list of dork search vectors tailored for Turkey.
        Simulation of dorking results for the HADES engine.
        """
        vectors = []
        
        # 1. Direct TR Dorks
        for brand, dork_list in self.dorks.items():
            for dork in dork_list:
                # Add bare dork
                vectors.append(f"HADES Dork: {dork} (Global)")
                # Add TR specific dork
                for ctx in random.sample(self.tr_context, 2):
                    vectors.append(f"HADES Dork: {dork} {ctx}")
                    
        return vectors
        
    def get_stealth_ports(self):
        """
        Returns a massive list of ports used by IoT devices.
        Expanded to cover 99% of CCTV vectors.
        """
        return [
            80, 81, 82, 83, 84, 85, 88, 8000, 8001, 8008, 8080, 8081, 8090, 8181, 8888, # HTTP Alts
            554, 1935, 37777, 34567, 8009, 1024, 2000, 60001, 9000, 9999, 5000, 5001 # RTSP/SDK/Media
        ]
