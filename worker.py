from PyQt6.QtCore import QThread, pyqtSignal

class AIWorkerThread(QThread):
    bubble_ready = pyqtSignal(int, dict) 
    finished_all = pyqtSignal(int) 
    clear_requested = pyqtSignal() 

    def __init__(self, engine, img_path):
        super().__init__()
        self.engine = engine
        self.img_path = img_path

    def run(self):
        count = 0
        for bubble in self.engine.process_image(self.img_path):
            # Only wipe the UI the exact millisecond the FIRST valid bubble is ready
            if count == 0:
                self.clear_requested.emit() 
                
            count += 1
            self.bubble_ready.emit(count, bubble)
            
        self.finished_all.emit(count)