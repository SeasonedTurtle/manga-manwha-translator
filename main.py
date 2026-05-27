import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread, pyqtSignal
from ui import TranslatorPanel, Snipper
from scanner import ScreenScanner
from engine import TranslationEngine

class AIWorkerThread(QThread):
    finished = pyqtSignal(list)

    def __init__(self, engine, img_path):
        super().__init__()
        self.engine = engine
        self.img_path = img_path

    def run(self):
        bubble_data = self.engine.process_image(self.img_path)
        self.finished.emit(bubble_data)

class MangaTranslatorApp:
    def __init__(self):
        print("\n=== STARTING ZONE TRANSLATOR ===")
        self.scanner = ScreenScanner()
        self.engine = TranslationEngine(start_mode="offline")
        
        self.panel = TranslatorPanel()
        
        self.panel.on_capture_requested.connect(self.start_translation)
        self.panel.on_clear_requested.connect(self.panel.clear_translations)
        self.panel.on_snip_requested.connect(self.start_snip_mode)
        self.panel.on_mode_toggled.connect(self.toggle_translation_mode)

    def run(self):
        print("\n[App]: Ready.")
        screen = QApplication.primaryScreen().geometry()
        self.panel.move(screen.width() - 400, 50)
        self.panel.show()

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
        print("[App]: Snip mode active. Draw a box on the screen!")
        self.snipper = Snipper()
        self.snipper.on_area_selected.connect(self.save_snip_area)
        self.snipper.show()

    def save_snip_area(self, rect):
        x, y, w, h = rect
        self.scanner.set_area(x, y, w, h)
        print(f"[App]: Area locked in! ({w}x{h} pixels). You can now translate.")

    def start_translation(self):
        self.panel.clear_translations()
        
        self.panel.translate_btn.setText("Translating...")
        self.panel.translate_btn.setEnabled(False)
        QApplication.processEvents()
        
        print("\n[App]: Snapping targeted area...")
        img_path = self.scanner.capture_screen() 
        
        print("[App]: AI Processing...")
        self.worker = AIWorkerThread(self.engine, img_path)
        self.worker.finished.connect(self.on_translation_finished)
        self.worker.start()

    def on_translation_finished(self, bubble_data):
        if bubble_data:
            for index, bubble in enumerate(bubble_data, 1):
                self.panel.add_translation(index, bubble['original'], bubble['translation'])
        else:
            self.panel.add_translation(1, "No text found.", "Could not detect valid Korean in the targeted zone.")
            
        self.panel.translate_btn.setText("Translate Area")
        self.panel.translate_btn.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    translator = MangaTranslatorApp()
    translator.run()
    sys.exit(app.exec())