import sys
from PyQt6.QtWidgets import QApplication
from app import MangaTranslatorApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Initialize and run the application
    translator = MangaTranslatorApp()
    translator.run()
    
    # Ensure a clean exit
    sys.exit(app.exec())