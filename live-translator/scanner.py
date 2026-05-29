import pyscreenshot
import os
import hashlib

class ScreenScanner:
    def __init__(self):
        if os.path.exists("/dev/shm"):
            self.output_path = "/dev/shm/manga_capture.png"
            print("[Scanner]: ⚡ RAM Disk active.")
        else:
            self.image_folder = os.path.abspath("images")
            os.makedirs(self.image_folder, exist_ok=True)
            self.output_path = os.path.join(self.image_folder, "capture.png")
            print("[Scanner]: RAM Disk not found. Using SSD folder.")
            
        self.crop_box = None 
        self.last_hash = None 

    def set_area(self, x, y, w, h):
        self.crop_box = (x, y, x + w, y + h)
        self.last_hash = None 

    def capture_screen(self, update_memory=False):
        """Standard capture. If update_memory is True, it syncs the hash so it doesn't falsely trigger later."""
        if self.crop_box:
            image = pyscreenshot.grab(bbox=self.crop_box)
        else:
            image = pyscreenshot.grab()
            
        image.save(self.output_path)
        
        # Sync the memory after a translation so it starts fresh!
        if update_memory:
            with open(self.output_path, "rb") as f:
                self.last_hash = hashlib.md5(f.read()).hexdigest()
                
        return self.output_path

    def capture_and_check(self):
        """Used ONLY by the Smart Scroll monitor to check if you are moving."""
        self.capture_screen(update_memory=False)
        
        with open(self.output_path, "rb") as f:
            current_hash = hashlib.md5(f.read()).hexdigest()
            
        did_change = (current_hash != self.last_hash)
        self.last_hash = current_hash
        
        return self.output_path, did_change