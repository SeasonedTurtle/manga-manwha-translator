import os
import hashlib


def image_digest(image):
    return hashlib.md5(image.tobytes()).hexdigest()


def image_is_blank(image, variance_limit=12):
    """True when the frame is a solid flash, not a drawn page.

    Animated spinners never stay on one digest, so this only rejects the
    stable white or black frame some click-readers show between pages.
    """
    small = image.convert("L").resize((32, 32))
    pixels = list(small.tobytes())
    mean = sum(pixels) / len(pixels)
    variance = sum((pixel - mean) ** 2 for pixel in pixels) / len(pixels)
    return variance < variance_limit


class FrameWatch:
    """Wait until a scrolled or clicked page has stopped changing."""

    def __init__(self):
        self.digest = None
        self.since = None
        self.translated = None
        self.blank = False

    def reset(self):
        self.digest = None
        self.since = None
        self.translated = None
        self.blank = False

    def update(self, digest, blank, now):
        if digest != self.digest:
            self.digest = digest
            self.since = now
        self.blank = blank

    def ready(self, now, settle_seconds):
        if self.digest is None or self.since is None:
            return False
        if self.blank or self.digest == self.translated:
            return False
        return (now - self.since) >= settle_seconds

    def mark_translated(self):
        self.translated = self.digest


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
        self.watch = FrameWatch()

    def set_area(self, x, y, w, h):
        self.crop_box = (x, y, x + w, y + h)
        self.last_hash = None
        self.watch.reset()

    def _grab(self):
        import pyscreenshot
        if self.crop_box:
            return pyscreenshot.grab(bbox=self.crop_box)
        return pyscreenshot.grab()

    def capture_screen(self, update_memory=False):
        """Standard capture. If update_memory is True, it syncs the hash so it doesn't falsely trigger later."""
        image = self._grab()
        image.save(self.output_path)

        # Sync the memory after a translation so it starts fresh!
        if update_memory:
            self.last_hash = image_digest(image)
            self.watch.mark_translated()

        return self.output_path

    def capture_and_check(self):
        """Used ONLY by the Smart Scroll monitor to check if you are moving."""
        image = self._grab()
        image.save(self.output_path)
        current_hash = image_digest(image)

        did_change = (current_hash != self.last_hash)
        self.last_hash = current_hash

        return self.output_path, did_change

    def observe(self, now):
        """Capture the target and record whether this frame is still moving."""
        image = self._grab()
        image.save(self.output_path)
        digest = image_digest(image)
        self.watch.update(digest, image_is_blank(image), now)
        self.last_hash = digest
        return self.output_path

    def page_is_ready(self, now, settle_seconds):
        return self.watch.ready(now, settle_seconds)

    def mark_translated(self):
        self.watch.mark_translated()
        self.last_hash = self.watch.translated