import pyscreenshot
import os

class ScreenScanner:
    def __init__(self):
        self.image_folder = os.path.abspath("images")
        os.makedirs(self.image_folder, exist_ok=True)
        self.output_path = os.path.join(self.image_folder, "capture.png")
        # This will hold our specific (Left, Top, Right, Bottom) coordinates
        self.crop_box = None 

    def set_area(self, x, y, w, h):
        """Saves the coordinates drawn by the Snipping tool."""
        # pyscreenshot requires (left, top, right, bottom)
        self.crop_box = (x, y, x + w, y + h)

    def capture_screen(self):
        """Snaps a picture of the exact zone, or full screen if no zone is set."""
        if self.crop_box:
            image = pyscreenshot.grab(bbox=self.crop_box)
        else:
            image = pyscreenshot.grab()
            
        image.save(self.output_path)
        return self.output_path