from PyQt6.QtWidgets import (QWidget, QPushButton, QVBoxLayout, QLabel, 
                             QScrollArea, QFrame, QRubberBand, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPoint

class Snipper(QWidget):
    """A transparent, full-screen overlay for selecting a screen area."""
    on_area_selected = pyqtSignal(tuple)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 100);") 
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        
        self.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self.origin = QPoint()

    def mousePressEvent(self, event):
        self.origin = event.pos()
        self.rubber_band.setGeometry(QRect(self.origin, self.origin))
        self.rubber_band.show()

    def mouseMoveEvent(self, event):
        self.rubber_band.setGeometry(QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        self.rubber_band.hide()
        rect = self.rubber_band.geometry()
        self.on_area_selected.emit((rect.x(), rect.y(), rect.width(), rect.height()))
        self.close()

class TranslatorPanel(QWidget):
    """The unified control bar and translation display panel."""
    on_capture_requested = pyqtSignal()
    on_clear_requested = pyqtSignal()
    on_snip_requested = pyqtSignal()
    on_mode_toggled = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manga Translator")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        self.resize(350, 750) 
        
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        self.snip_btn = QPushButton("Set Translation Area")
        self.snip_btn.setStyleSheet("padding: 10px; font-size: 14px; font-weight: bold; background-color: #2196F3; color: white; border-radius: 5px;")
        self.snip_btn.clicked.connect(self.on_snip_requested.emit)
        
        self.mode_btn = QPushButton("Mode: OFFLINE")
        self.mode_btn.setStyleSheet("padding: 10px; font-size: 14px; font-weight: bold; background-color: #9C27B0; color: white; border-radius: 5px;")
        self.mode_btn.clicked.connect(self.on_mode_toggled.emit)
        
        self.translate_btn = QPushButton("Translate Area")
        self.translate_btn.setStyleSheet("padding: 15px; font-size: 16px; font-weight: bold; background-color: #4CAF50; color: white; border-radius: 5px;")
        self.translate_btn.clicked.connect(self.on_capture_requested.emit)
        
        self.clear_btn = QPushButton("Clear Panel")
        self.clear_btn.setStyleSheet("padding: 10px; font-size: 14px; font-weight: bold; background-color: #FF9800; color: white; border-radius: 5px;")
        self.clear_btn.clicked.connect(self.on_clear_requested.emit)
        
        self.quit_btn = QPushButton("Quit")
        self.quit_btn.setStyleSheet("padding: 10px; font-size: 14px; background-color: #f44336; color: white; border-radius: 5px;")
        self.quit_btn.clicked.connect(QApplication.quit)
        
        self.layout.addWidget(self.snip_btn)
        self.layout.addWidget(self.mode_btn)
        self.layout.addWidget(self.translate_btn)
        self.layout.addWidget(self.clear_btn)
        self.layout.addWidget(self.quit_btn)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("margin-top: 5px; margin-bottom: 5px;")
        self.layout.addWidget(line)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout()
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_widget.setLayout(self.scroll_layout)
        self.scroll.setWidget(self.scroll_widget)
        
        self.layout.addWidget(self.scroll)

    def add_translation(self, index, original, translation):
        card = QFrame()
        card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 5px; } QLabel { border: none; background: transparent; }")
        card_layout = QVBoxLayout()
        
        header = QLabel(f"<b>Bubble {index}</b>")
        header.setStyleSheet("color: #333; font-size: 14px;")
        
        en_text = QLabel(f"<span style='color: #000; font-size: 16px; font-weight: bold;'>{translation}</span>")
        en_text.setWordWrap(True)
        
        kr_text = QLabel(f"<span style='color: #666; font-size: 12px;'>{original}</span>")
        kr_text.setWordWrap(True)
        
        card_layout.addWidget(header)
        card_layout.addWidget(en_text)
        card_layout.addWidget(kr_text)
        card.setLayout(card_layout)
        
        self.scroll_layout.addWidget(card)

    def clear_translations(self):
        for i in reversed(range(self.scroll_layout.count())): 
            widget = self.scroll_layout.itemAt(i).widget()
            if widget: widget.setParent(None)