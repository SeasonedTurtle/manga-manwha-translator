import time

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from ui import TranslatorPanel, Snipper
from scanner import ScreenScanner
from engine import TranslationEngine
from worker import AIWorkerThread

class MangaTranslatorApp:
    def __init__(self):
        print("\n=== STARTING MANGA TRANSLATOR ===")
        self.scanner = ScreenScanner()
        self.engine = TranslationEngine(start_mode="offline") 
        
        self.panel = TranslatorPanel()
        
        self.is_live = False
        self.is_processing = False 
        
        self.panel.on_clear_requested.connect(self.panel.clear_translations)
        self.panel.on_snip_requested.connect(self.start_snip_mode)
        self.panel.on_mode_toggled.connect(self.toggle_translation_mode)
        self.panel.on_capture_once_requested.connect(self.translate_manual_once)
        self.panel.on_live_requested.connect(self.toggle_live_mode)

    def run(self):
        print("\n[App]: Ready.")
        screen = QApplication.primaryScreen().geometry()
        self.panel.move(screen.width() - 400, 50)
        self.panel.show()
        
    def get_speed_ms(self):
        text = self.panel.speed_combo.currentText()
        if "1s" in text: return 1000
        if "2s" in text: return 2000
        if "3s" in text: return 3000
        if "4s" in text: return 4000
        return 2000

    def toggle_translation_mode(self):
        if self.engine.mode == "offline":
            self.engine.mode = "online"
            self.panel.mode_btn.setText("Mode: ONLINE")
            self.panel.mode_btn.setStyleSheet("padding: 10px; font-size: 14px; font-weight: bold; background-color: #00BCD4; color: white; border-radius: 5px;")
            print("[App]: Switched to Online Google Translation.")
        else:
            self.engine.mode = "offline"
            self.panel.mode_btn.setText("Mode: OFFLINE")
            self.panel.mode_btn.setStyleSheet("padding: 10px; font-size: 14px; font-weight: bold; background-color: #9C27B0; color: white; border-radius: 5px;")
            print("[App]: Switched to Offline Local Translation.")

    def start_snip_mode(self):
        if self.is_live: self.toggle_live_mode()
        self.snipper = Snipper()
        self.snipper.on_area_selected.connect(self.save_snip_area)
        self.snipper.show()

    def save_snip_area(self, rect):
        x, y, w, h = rect
        self.scanner.set_area(x, y, w, h)
        print(f"[App]: Area locked in! ({w}x{h} pixels).")

    def translate_manual_once(self):
        if not self.scanner.crop_box:
            self.panel.add_translation(1, "Error", "Please click '1. Set Target Area' first.")
            return

        if self.is_processing: return
        if self.is_live: self.toggle_live_mode()

        print("\n[App]: 📸 Manual capture triggered!")
        self.panel.translate_once_btn.setText("Translating...")
        QApplication.processEvents()

        img_path = self.scanner.capture_screen(update_memory=True)
        self.execute_translation_job(img_path, manual=True)

    def toggle_live_mode(self):
        if not self.scanner.crop_box:
            self.panel.add_translation(1, "Error", "Please click '1. Set Target Area' first.")
            return

        self.is_live = not self.is_live
        
        if self.is_live:
            self.panel.live_btn.setText("🔴 STOP Live Translate")
            self.panel.live_btn.setStyleSheet("padding: 15px; font-size: 16px; font-weight: bold; background-color: #f44336; color: white; border-radius: 5px;")
            
            self.panel.translate_once_btn.setEnabled(False) 
            self.panel.read_toggle.setEnabled(False)
            self.panel.speed_combo.setEnabled(False)
            
            print("[App]: 🔴 Live Mode Started. Beginning Sequential Loop...")
            # Fire the very first frame to kick off the loop
            self.execute_live_translation() 
        else:
            self.panel.live_btn.setText("3. Start Live Translate")
            self.panel.live_btn.setStyleSheet("padding: 15px; font-size: 16px; font-weight: bold; background-color: #4CAF50; color: white; border-radius: 5px;")
            
            self.panel.translate_once_btn.setEnabled(True) 
            self.panel.read_toggle.setEnabled(True)
            self.panel.speed_combo.setEnabled(True)
            
            print("[App]: ⏹️ Live Mode Stopped.")

    def reading_order(self):
        return "vertical" if self.panel.read_toggle.isChecked() else "horizontal"

    def settle_seconds(self):
        """Vertical strips need a real pause. A clicked page only needs the image to finish loading."""
        seconds = self.get_speed_ms() / 1000
        if self.reading_order() == "horizontal":
            return min(seconds, 0.8)
        return seconds

    def execute_live_translation(self):
        # Safety catch: If user clicked STOP while we were in cooldown, abort the loop!
        if not self.is_live: return
        if self.is_processing: return

        self.scanner.observe(time.time())
        if not self.scanner.page_is_ready(time.time(), self.settle_seconds()):
            QTimer.singleShot(250, self.execute_live_translation)
            return

        self.scanner.mark_translated()
        self.is_processing = True
        print("\n[App]: 🤖 Page settled. Starting AI Processing...")
        self.execute_translation_job(self.scanner.output_path, manual=False)

    def execute_translation_job(self, img_path, manual=False):
        self.is_processing = True
        
        self.worker = AIWorkerThread(self.engine, img_path, order=self.reading_order())
        self.worker.clear_requested.connect(self.panel.clear_translations)
        self.worker.bubble_ready.connect(self.on_bubble_ready)
        
        if manual:
            self.worker.finished_all.connect(self.on_manual_finished)
        else:
            self.worker.finished_all.connect(self.on_live_frame_finished)
            
        self.worker.start()

    def on_bubble_ready(self, index, bubble):
        self.panel.add_translation(index, bubble['original'], bubble['translation'])

    def on_manual_finished(self, total_count):
        self.is_processing = False
        self.panel.translate_once_btn.setText("2. Translate Area (Once)")
        if total_count == 0:
            self.panel.clear_translations()
            self.panel.add_translation(1, "No text found.", "Could not detect valid Korean.")

    def on_live_frame_finished(self, total_count):
        self.is_processing = False
        
        # The page is already marked, so the loop only fires again after the next
        # scroll pause or the next clicked page.
        if self.is_live:
            print("[App]: ✅ Translation shown. Watching for the next page.")
            QTimer.singleShot(250, self.execute_live_translation)