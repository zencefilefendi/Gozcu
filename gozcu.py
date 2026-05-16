'''
MIT License

Copyright (c) 2026 Zencefil Efendi

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
'''

import sys
import os
sys.dont_write_bytecode = True

import tkinter as tk
import customtkinter as ctk
import tkintermapview 
import tkinter.font as tkFont
from tkinter import filedialog as fd
from tkinter import messagebox 
import threading 
import webview, webbrowser

import concurrent.futures
import re
import requests
import pycountry
import urllib3
import random

from src.crawler import GozcuWebcam, ZenceFilSmartAnalyze
from src.config import GozcuConfiguration
from src.logger import GozcuLogger
from src.geo import *
from src.voice_assistant import ZenceFilVoice
from headers.agents import Agents

__author__ = "Zencefil Efendi"
__version__ = "3.0 (SOC Dashboard Edition)"

# Appearance Mode & Theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

class ZenceFilDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Settings
        # Window Settings
        self.title(f"ZenceFil Project HADES | v{__version__} | Cyber Intelligence Fusion")
        self.geometry("1400x900")
        self.configure(fg_color="#0b0e14") # Obsidian Deep Black
        
        # Initialize Config
        GozcuConfiguration.GOZCU_DEFAULT_COUNT = 30

        # Grid Configuration (2x3)
        self.grid_columnconfigure(0, weight=0) # Sidebar
        self.grid_columnconfigure(1, weight=1) # Main View
        self.grid_columnconfigure(2, weight=0) # Intelligence Side
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0) # Bottom Console
        
        self.markers = []
        self.setup_ui()
        self.update_slider_label(30)
        # Delay voice notification slightly so it doesn't block GUI rendering on MacOS
        self.after(500, ZenceFilVoice.notify_system_start)
        
        
    def setup_ui(self):
        # 1. Sidebar Frame
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color="#0f1219", border_color="#18E63B", border_width=1)
        self.sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="ZenceFil.", font=ctk.CTkFont(family="Terminal", size=24, weight="bold"), text_color="#18E63B")
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.sub_label = ctk.CTkLabel(self.sidebar_frame, text="IoT SOC TERMINAL", font=ctk.CTkFont(size=10, slant="italic"), text_color="#18E63B")
        self.sub_label.grid(row=1, column=0, padx=20, pady=(0, 20))

        # Country Scrollable Frame in Sidebar
        self.scroll_frame = ctk.CTkScrollableFrame(self.sidebar_frame, label_text="OPERASYON BÖLGESİ", label_font=ctk.CTkFont(size=12, weight="bold"), 
                                                 fg_color="transparent", label_text_color="#18E63B")
        self.scroll_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(2, weight=1)

        self.add_country_buttons()

        # Sidebar Controls
        self.save_btn = ctk.CTkButton(self.sidebar_frame, text="LOG KAYDET", command=self.write_file_handler, fg_color="transparent", 
                                      border_width=1, border_color="#18E63B", text_color="#18E63B", hover_color="#1a202c")
        self.save_btn.grid(row=3, column=0, padx=20, pady=(20, 10))
        
        self.load_btn = ctk.CTkButton(self.sidebar_frame, text="LOG YÜKLE", command=self.load_logfile, fg_color="transparent", 
                                      border_width=1, border_color="#18E63B", text_color="#18E63B", hover_color="#1a202c")
        self.load_btn.grid(row=4, column=0, padx=20, pady=0)

        # TURBO MODE Switch
        self.turbo_var = tk.BooleanVar(value=False)
        self.turbo_switch = ctk.CTkSwitch(self.sidebar_frame, text="TURBO MOD (100+)", variable=self.turbo_var,
                                          progress_color="#18E63B", button_color="#18E63B", text_color="#18E63B",
                                          font=ctk.CTkFont(size=10, weight="bold"))
        self.turbo_switch.grid(row=5, column=0, padx=20, pady=20)

        # 2. Main View (Center)
        self.main_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#0b0e14")
        self.main_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Statistic Cards (Top of Main)
        self.stats_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.stats_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        self.stat_card_targets = self.create_stat_card(self.stats_frame, "TOPLAM HEDEF", "0")
        self.stat_card_targets.grid(row=0, column=0, padx=5)
        
        self.stat_card_online = self.create_stat_card(self.stats_frame, "CANLI SİSTEMLER", "0")
        self.stat_card_online.grid(row=0, column=1, padx=5)
        self.stat_card_online.val_label.configure(text_color="#18E63B") # Bright Green

        self.stat_card_offline = self.create_stat_card(self.stats_frame, "ÇEVRİMDIŞI", "0")
        self.stat_card_offline.grid(row=0, column=2, padx=5)
        self.stat_card_offline.val_label.configure(text_color="#ff4d4d") # Warning Red
        
        self.stat_card_intensity = self.create_stat_card(self.stats_frame, "TARAMA DERİNLİĞİ", "100")
        self.stat_card_intensity.grid(row=0, column=3, padx=5)
        
        # Extreme Deep Scan Support
        self.slider = ctk.CTkSlider(self.stats_frame, from_=10, to=20000, command=self.update_slider_label, button_color="#18E63B", progress_color="#18E63B")
        self.slider.set(20000)
        self.slider.grid(row=0, column=4, padx=10)

        # Map Widget
        self.map_widget = tkintermapview.TkinterMapView(self.main_frame, corner_radius=10)
        self.map_widget.set_tile_server("https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", max_zoom=25)
        self.map_widget.grid(row=1, column=0, sticky="nsew")

        # 3. Intelligence Hub (Right Side)
        self.intel_frame = ctk.CTkFrame(self, width=400, corner_radius=10, fg_color="#0f1219", border_color="#18E63B", border_width=1)
        self.intel_frame.grid(row=0, column=2, rowspan=1, padx=10, pady=10, sticky="nsew")
        self.intel_frame.grid_rowconfigure(1, weight=1)

        self.intel_label = ctk.CTkLabel(self.intel_frame, text="DUAL INTEL GRID", font=ctk.CTkFont(size=14, weight="bold"), text_color="#18E63B")
        self.intel_label.grid(row=0, column=0, pady=10)

        # Tabview for Online/Offline separation
        self.tabview = ctk.CTkTabview(self.intel_frame, fg_color="#0f1219", segmented_button_selected_color="#18E63B", 
                                       segmented_button_selected_hover_color="#14c431", segmented_button_unselected_color="#0b0e14")
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.tabview.add("ONLINE")
        self.tabview.add("OFFLINE")

        self.target_list = tk.Listbox(self.tabview.tab("ONLINE"), bg="#0f1219", fg="#18E63B", font=("Courier", 12), borderwidth=0, highlightthickness=0)
        self.target_list.pack(fill="both", expand=True)
        self.target_list.bind("<<ListboxSelect>>", self.add_ip_location_online)
        self.target_list.bind("<Double-Button-1>", self.browser_load_url_online)

        self.offline_list = tk.Listbox(self.tabview.tab("OFFLINE"), bg="#0f1219", fg="#ff4d4d", font=("Courier", 12), borderwidth=0, highlightthickness=0)
        self.offline_list.pack(fill="both", expand=True)
        self.offline_list.bind("<<ListboxSelect>>", self.add_ip_location_offline)
        
        self.info_box = ctk.CTkTextbox(self.intel_frame, height=200, fg_color="#0b0e14", text_color="#18E63B", font=("Courier", 12), border_color="#18E63B", border_width=1)
        self.info_box.grid(row=2, column=0, sticky="ew", padx=10, pady=10)

        # 4. Console Log (Bottom)
        self.console_frame = ctk.CTkFrame(self, height=150, corner_radius=0, fg_color="#05070a", border_width=1, border_color="#18E63B")
        self.console_frame.grid(row=1, column=1, columnspan=2, sticky="ew")
        
        self.console_text = ctk.CTkTextbox(self.console_frame, height=120, fg_color="transparent", text_color="#18E63B", font=("Courier", 11))
        self.console_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.log_to_console("ZenceFil SOC Terminal Aktif. Sistem Gözetimi Başlatıldı.")

    def create_stat_card(self, master, label, value):
        card = ctk.CTkFrame(master, width=120, height=60, fg_color="#0f1219", border_color="#18E63B", border_width=1)
        card.grid_propagate(False)
        lbl = ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=8, weight="bold"), text_color="#18E63B")
        lbl.pack(pady=(5, 0))
        val = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=16, weight="bold"), text_color="#18E63B")
        val.pack()
        card.val_label = val # store reference to update
        return card

    def add_country_buttons(self):
        # Project HADES: Cyber Intelligence Fusion
        btn_tr = ctk.CTkButton(self.scroll_frame, text="TR DARBE MODU", command=lambda: self.clear_and_execute_webcam("TR"),
                            fg_color="#D32F2F", text_color="#FFFFFF", anchor="center", hover_color="#B71C1C",
                            font=ctk.CTkFont(size=14, weight="bold"), height=40)
        btn_tr.pack(fill="x", padx=10, pady=(15, 5))

        btn_il = ctk.CTkButton(self.scroll_frame, text="IL DARBE MODU", command=lambda: self.clear_and_execute_webcam("IL"),
                            fg_color="#1E88E5", text_color="#FFFFFF", anchor="center", hover_color="#1565C0",
                            font=ctk.CTkFont(size=14, weight="bold"), height=40)
        btn_il.pack(fill="x", padx=10, pady=5)

        btn_ir = ctk.CTkButton(self.scroll_frame, text="IR DARBE MODU", command=lambda: self.clear_and_execute_webcam("IR"),
                            fg_color="#388E3C", text_color="#FFFFFF", anchor="center", hover_color="#2E7D32",
                            font=ctk.CTkFont(size=14, weight="bold"), height=40)
        btn_ir.pack(fill="x", padx=10, pady=(5, 15))
        
        # Descriptive label for HADES
        desc = ctk.CTkLabel(self.scroll_frame, text="IoT Dorking + Stealth Pulse\nFusion Intelligence", 
                            font=ctk.CTkFont(size=11, weight="bold"), text_color="#D32F2F")
        desc.pack(pady=5)

    def log_to_console(self, msg):
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.console_text.insert("end", f"[{timestamp}] >> {msg}\n")
        self.console_text.see("end")

    def update_slider_label(self, value):
        self.stat_card_intensity.val_label.configure(text=str(int(value)))
        GozcuConfiguration.GOZCU_DEFAULT_COUNT = int(value)

    def clear_and_execute_webcam(self, country):
        self.target_list.delete(0, tk.END)
        self.offline_list.delete(0, tk.END)
        self.info_box.delete("1.0", "end")
        self.stat_card_targets.val_label.configure(text="...")
        self.stat_card_online.val_label.configure(text="...")
        self.stat_card_offline.val_label.configure(text="...")
        
        depth = int(self.slider.get())
        
        # Project HADES Message
        burst_msg = f"PROJECT HADES PROTOKOLÜ BAŞLATILDI: {country} | Fusion Intelligence"
        ZenceFilVoice.speak(f"{country} üzerinde Hades protokolü ve görünmez port taraması başlatıldı.")
            
        self.log_to_console(burst_msg)
        self.log_to_console("Multi-Vector Discovery motoru ısındırılıyor...")
        
        def run_crawl():
            GozcuConfiguration.num_webcams_found = 0
            GozcuConfiguration.webcams_found = []
            
            # Start the multi-brand burst (Turbo scaling)
            discovery_workers = 100 if self.turbo_var.get() else 60
            
            # Setup Live Callback
            def on_found(cam_url):
                # Verify status in background to avoid UI freeze
                def verify():
                    try:
                        is_online = GozcuWebcam.check_status(cam_url)
                        if is_online:
                            self.after(0, lambda: self.target_list.insert(0, f"[ONLINE] {cam_url}"))
                            # Update counter
                            current = self.stat_card_online.val_label.cget("text")
                            if current == "...": current = 0
                            else: current = int(current)
                            self.after(0, lambda: self.stat_card_online.val_label.configure(text=str(current + 1)))
                            self.after(0, lambda: self.stat_card_online.val_label.configure(text=str(current + 1)))
                            
                            # 📝 Auto-Log to File (User Request)
                            try:
                                with open("online_findings.txt", "a") as f:
                                    f.write(f"{cam_url}\n")
                            except: pass
                        else:
                            # Optional: Show offline in real-time or just skip to keep UI clean
                            pass 
                    except: pass
                        
                threading.Thread(target=verify, daemon=True).start()

            # Execute Crawl with Callback
            found = GozcuWebcam.crawl(country, max_workers=discovery_workers, ui_callback=on_found)
            
            # Deduplicate
            found = sorted(list(set(GozcuConfiguration.webcams_found)))
            online_targets = []
            offline_targets = []

            self.log_to_console(f"Keşif tamamlandı. {len(found)} IP analiz ediliyor (Heartbeat Pulse)...")

            # Status Checking with Burst Concurrency (Turbo Support)
            max_status_workers = 100 if self.turbo_var.get() else 40
            def check_and_categorize(url):
                if GozcuWebcam.check_status(url):
                    online_targets.append(url)
                else:
                    offline_targets.append(url)

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_status_workers) as status_executor:
                status_executor.map(check_and_categorize, found)

            # Update UI safely
            def update_ui():
                self.target_list.delete(0, tk.END)
                self.offline_list.delete(0, tk.END)
                
                for idx, cam in enumerate(sorted(online_targets), 1):
                    self.target_list.insert(tk.END, f"{idx}. [ONLINE] {cam}")
                
                for idx, cam in enumerate(sorted(offline_targets), 1):
                    self.offline_list.insert(tk.END, f"{idx}. [OFFLINE] {cam}")
                
                self.stat_card_targets.val_label.configure(text=str(len(found)))
                self.stat_card_online.val_label.configure(text=str(len(online_targets)))
                self.stat_card_offline.val_label.configure(text=str(len(offline_targets)))
                
                self.log_to_console(f"ANALİZ TAMAMLANDI. CANLI: {len(online_targets)} | ÇEVRİMDIŞI: {len(offline_targets)}")
                ZenceFilVoice.notify_scan_complete(len(online_targets), country)

            self.after(0, update_ui)

        threading.Thread(target=run_crawl, daemon=True).start()

    def add_ip_location_online(self, event):
        self.handle_target_selection(self.target_list)

    def add_ip_location_offline(self, event):
        self.handle_target_selection(self.offline_list)

    def handle_target_selection(self, listbox):
        try:
            selection = listbox.curselection()
            if not selection: return
            idx = selection[0]
            item = listbox.get(idx)
            
            # Strip status prefixes like [ONLINE] or [OFFLINE]
            clean_item = re.sub(r'^\d+\.\s+\[(ONLINE|OFFLINE)\]\s+', '', item)
            
            ip = re.search(r'http://([^:/\s]+)', clean_item).group(1) if "http" in clean_item else clean_item
            self.log_to_console(f"Hedef Analizi: {ip}")
            ZenceFilVoice.speak(f"Hedef {ip} analiz ediliyor.")
            
            self.info_box.delete("1.0", "end")
            self.info_box.insert("end", f"--- TARGET INTELLIGENCE ---\nIP: {ip}\n")
            
            import ipapi
            loc = ipapi.location(ip=ip)
            if loc:
                self.info_box.insert("end", f"ŞEHİR: {loc.get('city')}\n")
                self.info_box.insert("end", f"ÜLKE: {loc.get('country_name')}\n")
                self.info_box.insert("end", f"ISP: {loc.get('org')}\n")
                
                # Markers
                lat, lon = loc.get('latitude'), loc.get('longitude')
                self.map_widget.set_position(lat, lon)
                self.map_widget.set_zoom(12)
                self.markers.append(self.map_widget.set_marker(lat, lon, text=f"{ip} ({loc.get('city')})"))
            
            # Brand Analysis
            threading.Thread(target=self.smart_brand_check, args=(ip,)).start()
            
        except Exception as e:
            self.log_to_console(f"Analiz Hatası: {e}")

    def browser_load_url_online(self, event):
        selection = self.target_list.curselection()
        if not selection: return
        item = self.target_list.get(selection[0])
        url = re.sub(r'^\d+\.\s+\[ONLINE\]\s+', '', item)
        self.log_to_console(f"Tarayıcı Açılıyor: {url}")
        webbrowser.open(url)

    def browser_load_url_offline(self, event):
        self.log_to_console("Sistem ÇEVRİMDIŞI. Bağlantı kurulamadı.")
        ZenceFilVoice.speak("Sistem çevrimdışı durumda. Bağlantı kurulamıyor.")

    def smart_brand_check(self, ip):
        try:
            resp = requests.get(f"http://{ip}", timeout=3, headers={'User-Agent': random.choice(Agents.useragent)})
            brand = ZenceFilSmartAnalyze.detect_brand(resp.headers, resp.text)
            self.info_box.insert("end", f"MARKA: {brand}\n")
            self.log_to_console(f"Cihaz Kimliği: {brand}")
        except:
            self.info_box.insert("end", "MARKA: BİLİNMEYEN (Offline/Timeout)\n")

    def open_web_browser(self, url):
        try:
            self.log_to_console(f"Canlı Yayın Akışı Açılıyor: {url}")
            ZenceFilVoice.speak("Canlı yayın başlatılıyor. Establishing connection.")
            
            # Using webbrowser for maximum compatibility with various security protocols and players
            webbrowser.open_new(url)
            
            self.log_to_console("Bağlantı talebi tarayıcıya iletildi. Hedef aktif.")
        except Exception as e:
            self.log_to_console(f"HATA: Tarayıcı açılamadı: {e}")

    def browser_load_url(self, event):
        try:
            selection = self.target_list.curselection()
            if not selection: 
                self.log_to_console("UYARI: Öncelikle bir hedef seçmelisiniz.")
                return
            
            item = self.target_list.get(selection[0])
            
            # More robust URL extraction: handle indexing and trailing slashes
            match = re.search(r'(https?://\d+\.\d+\.\d+\.\d+:\d+/?|https?://\S+)', item)
            if match:
                selected_url = match.group(0).strip()
                self.open_web_browser(selected_url)
            else:
                self.log_to_console("HATA: Seçilen metinde geçerli bir URL tespit edilemedi.")
                ZenceFilVoice.speak("Hata. Geçerli bir URL bulunamadı.")
        except Exception as e:
            self.log_to_console(f"Analiz Hatası (URL Loading): {e}")

    def write_file_handler(self):
        from datetime import datetime
        logfilename = f'ZenceFilLog_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        with open(logfilename, "w") as f:
            f.write(f"ZenceFil SOC LOG\nDate: {datetime.now()}\n\n")
            items = self.target_list.get(0, "end")
            for item in items: f.write(item + "\n")
        messagebox.showinfo("Başarılı", f"Log kaydedildi: {logfilename}")
        self.log_to_console(f"Log dosyası oluşturuldu: {logfilename}")

    def load_logfile(self):
        filename = fd.askopenfilename(title='ZenceFil Log Yükle', filetypes=[('Log Files', '*.log'), ('All Files', '*.*')])
        if filename:
            self.target_list.delete(0, "end")
            with open(filename, "r") as f:
                for line in f: self.target_list.insert("end", line.strip())
            self.log_to_console(f"Log yüklendi: {filename}")

    def get_platform_title(self):
        return f"ZenceFil Gözcü | v{__version__}"

if __name__ == "__main__":
    app = ZenceFilDashboard()
    app.mainloop()