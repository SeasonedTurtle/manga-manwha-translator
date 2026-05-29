from PyQt6.QtWidgets import (QWidget, QPushButton, QVBoxLayout, QLabel, 
                             QScrollArea, QFrame, QRubberBand, QApplication, 
                             QComboBox, QHBoxLayout, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPoint, QPropertyAnimation, pyqtProperty
from PyQt6.QtGui import QPainter, QColor

class ToggleSwitch(QCheckBox):
    """A custom iOS-style toggle switch to replace standard checkboxes."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._position = 0

    @pyqtProperty(float)
    def position(self):
        return self._position

    @position.setter
    def position(self, pos):
        self._position = pos
        self.update()

    def hitButton(self, pos: QPoint):
        return self.contentsRect().contains(pos)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background
        p.setPen(Qt.PenStyle.NoPen)
        rect = QRect(0, 0, self.width(), self.height())
        
        if self.isChecked():
            p.setBrush(QColor("#4CAF50")) # Green when Webtoon Mode
        else:
            p.setBrush(QColor("#555555")) # Dark grey when Manga Mode
            
        p.drawRoundedRect(0, 0, rect.width(), rect.height(), 14, 14)
        
        # Draw the sliding circle
        p.setBrush(QColor("#ffffff"))
        # Move circle based on checked state
        x_pos = self.width() - 26 if self.isChecked() else 2
        p.drawEllipse(x_pos, 2, 24, 24)

class Snipper(QWidget):
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
    on_capture_once_requested = pyqtSignal() 
    on_live_requested = pyqtSignal()         
    on_clear_requested = pyqtSignal()
    on_snip_requested = pyqtSignal()
    on_mode_toggled = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manga Translator")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        self.resize(370, 750) 
        
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        self.snip_btn = QPushButton("1. Set Target Area")
        self.snip_btn.setStyleSheet("padding: 10px; font-size: 14px; font-weight: bold; background-color: #2196F3; color: white; border-radius: 5px;")
        self.snip_btn.clicked.connect(self.on_snip_requested.emit)
        
        self.mode_btn = QPushButton("Mode: OFFLINE")
        self.mode_btn.setStyleSheet("padding: 10px; font-size: 14px; font-weight: bold; background-color: #9C27B0; color: white; border-radius: 5px;")
        self.mode_btn.clicked.connect(self.on_mode_toggled.emit)

        self.translate_once_btn = QPushButton("2. Translate Area (Once)")
        self.translate_once_btn.setStyleSheet("padding: 10px; font-size: 14px; font-weight: bold; background-color: #FFC107; color: black; border-radius: 5px;")
        self.translate_once_btn.clicked.connect(self.on_capture_once_requested.emit)
        
        self.live_btn = QPushButton("3. Start Live Translate")
        self.live_btn.setStyleSheet("padding: 15px; font-size: 16px; font-weight: bold; background-color: #4CAF50; color: white; border-radius: 5px;")
        self.live_btn.clicked.connect(self.on_live_requested.emit)
        
        # --- THE NEW SETTINGS ROW ---
        settings_layout = QHBoxLayout()
        
        # 1. The Toggle Switch
        self.read_toggle = ToggleSwitch()
        self.read_toggle.setChecked(True) # Default to Webtoon (Green)
        
        # 2. The Dynamic Label
        self.toggle_label = QLabel("Vertical Webtoon")
        self.toggle_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.read_toggle.toggled.connect(self.update_toggle_label)
        
        # 3. The Speed Dropdown
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["Fast (1s)", "Normal (2s)", "Slow (3s)", "Very Slow (4s)"])
        self.speed_combo.setCurrentIndex(1) # Default to Normal (2s)
        self.speed_combo.setStyleSheet("padding: 5px; font-size: 12px; border: 1px solid #ccc; border-radius: 3px;")
        
        settings_layout.addWidget(self.read_toggle)
        settings_layout.addWidget(self.toggle_label)
        settings_layout.addStretch() # Pushes dropdown to the right
        settings_layout.addWidget(self.speed_combo)
        
        self.clear_btn = QPushButton("Clear Panel")
        self.clear_btn.setStyleSheet("padding: 10px; font-size: 14px; font-weight: bold; background-color: #607D8B; color: white; border-radius: 5px;")
        self.clear_btn.clicked.connect(self.on_clear_requested.emit)
        
        self.layout.addWidget(self.snip_btn)
        self.layout.addWidget(self.mode_btn)
        self.layout.addWidget(self.translate_once_btn)
        self.layout.addWidget(self.live_btn)
        self.layout.addLayout(settings_layout) # Added below Live button
        self.layout.addWidget(self.clear_btn)
        
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

    def update_toggle_label(self, is_checked):
        if is_checked:
            self.toggle_label.setText("Vertical Webtoon")
        else:
            self.toggle_label.setText("Horizontal Manga")

    def add_translation(self, index, original, translation):
        card = QFrame()
        card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 5px; } QLabel { border: none; background: transparent; }")
        card_layout = QVBoxLayout()
        
        header = QLabel(f"<b>Bubble {index}</b>")
        header.setStyleSheet("color: #888; font-size: 12px;")
        
        en_text = QLabel(f"<span style='color: #000; font-size: 16px; font-weight: bold;'>{translation}</span>")
        en_text.setWordWrap(True)
        
        kr_text = QLabel(f"<span style='color: #666; font-size: 12px;'>{original}</span>")
        kr_text.setWordWrap(True)
        
        card_layout.addWidget(header)
        card_layout.addWidget(en_text)
        card_layout.addWidget(kr_text)
        card.setLayout(card_layout)
        
        self.scroll_layout.addWidget(card)
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())

    def clear_translations(self):
        for i in reversed(range(self.scroll_layout.count())): 
            widget = self.scroll_layout.itemAt(i).widget()
            if widget: widget.setParent(None)