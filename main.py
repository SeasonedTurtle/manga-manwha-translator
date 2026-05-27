import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread, pyqtSignal
from ui import FloatingButton, SidePanel, Snipper
from scanner import ScreenScanner
from engine import TranslationEngine

class AIWorkerThread(QThread):
    finished = pyqtSignal(list)

    def __init__(self, engine, img_path):
        super().__init__()
        self.engine = engine
        self.img_path = img_path

    def run(self):
        bubble_data = self.engine.process_image(self.img_path, sort_direction="top_to_bottom")
        self.finished.emit(bubble_data)

class MangaTranslatorApp:
    def __init__(self):
        print("\n=== STARTING ZONE TRANSLATOR ===")
        self.scanner = ScreenScanner()
        self.engine = TranslationEngine(mode="korean")
        
        self.ui = FloatingButton()
        self.panel = SidePanel()
        
        # Connect the buttons
        self.ui.on_capture_requested.connect(self.start_translation)
        self.ui.on_clear_requested.connect(self.panel.clear_translations)
        self.ui.on_snip_requested.connect(self.start_snip_mode) # Connect Snip Button

    def run(self):
        print("\n[App]: Ready.")
        self.ui.show()
        screen = QApplication.primaryScreen().geometry()
        self.panel.move(screen.width() - 400, 50)
        self.panel.show()

    def start_snip_mode(self):
        """Launches the full-screen selection overlay."""
        print("[App]: 🎯 Snip mode active. Draw a box on the screen!")
        self.snipper = Snipper()
        self.snipper.on_area_selected.connect(self.save_snip_area)
        self.snipper.show()

    def save_snip_area(self, rect):
        """Saves the coordinates drawn by the user to the scanner."""
        x, y, w, h = rect
        self.scanner.set_area(x, y, w, h)
        print(f"[App]: ✅ Area locked in! ({w}x{h} pixels). You can now spam 'Translate Area'.")

    def start_translation(self):
        self.panel.clear_translations()
        
        self.ui.btn.setText("⏳ Translating...")
        self.ui.btn.setEnabled(False)
        QApplication.processEvents()
        
        # Takes a picture of ONLY the drawn box!
        print("\n[App]: 📸 Snapping targeted area...")
        img_path = self.scanner.capture_screen() 
        
        print("[App]: 🧠 AI Processing...")
        self.worker = AIWorkerThread(self.engine, img_path)
        self.worker.finished.connect(self.on_translation_finished)
        self.worker.start()

    def on_translation_finished(self, bubble_data):
        if bubble_data:
            for index, bubble in enumerate(bubble_data, 1):
                self.panel.add_translation(index, bubble['original'], bubble['translation'])
        else:
            self.panel.add_translation(1, "No text found.", "Could not detect valid Korean in the targeted zone.")
            
        self.ui.btn.setText("📸 Translate Area")
        self.ui.btn.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    translator = MangaTranslatorApp()
    translator.run()
    sys.exit(app.exec())