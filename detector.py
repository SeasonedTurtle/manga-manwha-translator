from ultralytics import YOLO
import cv2

class BubbleDetector:
    def __init__(self, model_path="your_bubble_detector.pt"):
        print(f"[Detector]: Booting YOLO model from {model_path}...")
        self.model = YOLO(model_path)
        print("[Detector]: YOLO ready.")

    def extract_bubbles(self, image_path, padding=5):
        """
        Scans an image, finds speech bubbles, and returns a list of cropped images.
        """
        print("[Detector]: Hunting for text bubbles...")
        
        # Run YOLO inference (verbose=False keeps the terminal clean)
        results = self.model(image_path, conf=0.25, verbose=False)
        
        # Load the raw image with OpenCV so we can slice it up
        img = cv2.imread(image_path)
        if img is None: return []

        bubbles = []
        
        for box in results[0].boxes:
            # YOLO returns xyxy coordinates (left, top, right, bottom)
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            
            # Apply padding so the OCR doesn't accidentally clip the edges of characters
            y1 = max(0, y1 - padding)
            x1 = max(0, x1 - padding)
            y2 = min(img.shape[0], y2 + padding)
            x2 = min(img.shape[1], x2 + padding)
            
            # Slice the original image using Numpy array slicing
            crop = img[y1:y2, x1:x2]
            
            bubbles.append({
                "x": x1,
                "y": y1,
                "w": x2 - x1,
                "h": y2 - y1,
                "crop": crop # The actual pixel data of JUST the text bubble
            })

        # Sort the bubbles top-to-bottom so the reading order makes sense in your UI
        bubbles.sort(key=lambda b: b['y'])
        
        return bubbles