import os
import sys
import threading

class ZenceFilVoice:
    """
    ZenceFil Voice Assistant: Provides high-tech audio feedback.
    Optimized for MacOS 'say' command, but extensible.
    """
    
    @staticmethod
    def speak(text):
        def _speak():
            # Zencefil Efendi's signature style: Hybrid TR/EN
            # MacOS 'say' command is very clean for this.
            if sys.platform == "darwin":
                # Using 'Yelda' for Turkish or 'Siri' for English-like Turkish
                os.system(f'say "{text}"')
            else:
                # Fallback for other OS if needed, but primarily for Mac as per user info
                pass

        threading.Thread(target=_speak, daemon=True).start()

    @staticmethod
    def notify_scan_complete(count, country):
        msg = f"Tarama tamamlandı. {country} bölgesinde {count} adet target tespit edildi. ZenceFil SOC Terminali gözetlemeye hazır."
        ZenceFilVoice.speak(msg)

    @staticmethod
    def notify_target_selected(ip):
        msg = f"Hedef {ip} seçildi. Intelligence Hub üzerinden veriler ayıklanıyor. Analyzing metadata."
        ZenceFilVoice.speak(msg)

    @staticmethod
    def notify_system_start():
        msg = "ZenceFil SOC Dashboard başlatıldı. Sistem aktif. Gözetleme terminali hazır."
        ZenceFilVoice.speak(msg)
