# ZenceFil Gözcü - Project HADES (SOC Terminal)

## Hakkında (About)
Gözcü (ZenceFil Edition), açık ağ kameralarını tespit edip harita üzerinde konumlandıran gelişmiş bir Masaüstü (GUI) OSINT ve IoT SOC (Security Operations Center) aracıdır. 

Bu sürüm, **Zencefil Efendi** tarafından "Project HADES" kod adıyla baştan aşağı yeniden tasarlanmış ve geliştirilmiştir. Derin Dorking motoru, "Stealth Pulse" port tarama yeteneği, asenkron hızlandırılmış tarama mimarisi ve karanlık temalı SOC Dashboard arayüzü ile donatılmıştır.

### Gelişmiş Özellikler (Key Features)
- **Multi-Vector Discovery (Çoklu Vektör Keşfi)**: Belirli ülkelere (örn: TR, IL, IR vb.) ve şehirlere göre yoğunlaştırılmış akıllı dork taramaları.
- **Project HADES Protokolü**: Hedef ağlardaki açık cihazların tespiti için görünmez (stealth) port problaması ve heartbeat analizi.
- **ZenceFil SOC Dashboard**: CustomTkinter ve TkinterMapView ile harmanlanmış modern, hacker tarzı karanlık arayüz (Obsidian Deep Black).
- **ZenceFil Voice Intelligence**: Operasyonel durumları bildiren entegre Mac sesli asistan desteği.
- **Akıllı Marka Tespiti**: Yakalanan kameraların HTTP başlıkları ve içeriklerinden cihaz üreticisini (Axis, Hikvision, Dahua vb.) tahmin edebilme yeteneği.

## Kurulum (Installation)
1. Repoyu klonlayın:
   ```bash
   git clone https://github.com/zencefilefendi/Gozcu.git
   ```
2. Dizin içerisine girin:
   ```bash
   cd Gözcü
   ```
3. Gerekli kütüphaneleri yükleyin:
   ```bash
   pip3 install -r requirements.txt
   ```
   *(Eğer macOS üzerinde CustomTkinter, TkinterMapView gibi eksik kütüphane hataları alırsanız bunları da `pip3 install customtkinter tkintermapview requests pywebview ipapi pycountry urllib3` komutuyla kurabilirsiniz).*

**Çalıştırma:**
```bash
python3 gozcu.py
```

## Etik Kullanım Uyarısı (Ethical Notice)
Bu programın geliştiricisi olan **Zencefil Efendi**, bu veri toplama aracının kötüye kullanımından sorumlu değildir. ZenceFil Gözcü, yalnızca modern arama motorları tarafından zaten indekslenmiş olan kamuya açık bilgileri derler ve sunar. Parola korumalı canlı yayınlara veya sistemlere yetkisiz erişim sağlamaya **çalışmayın** - bu yasa dışıdır. Gözcü yalnızca **eğitim ve güvenlik (SOC) izleme/farkındalık amaçları** için geliştirilmiştir. 

## Lisans (License)
MIT License
Copyright (c) 2026 Zencefil Efendi
