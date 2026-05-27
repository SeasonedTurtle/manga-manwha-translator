import cv2
import numpy as np
from deep_translator import GoogleTranslator
import easyocr
import re

class TranslationEngine:
    def __init__(self, mode="korean"):
        self.mode = mode.lower()
        print(f"[Engine]: Booting AI Models in {self.mode.upper()} mode...")
        self.translator = GoogleTranslator(source='auto', target='en')
        
        # GPU IS ENABLED FOR MAXIMUM SPEED
        self.kocr = easyocr.Reader(['ko'], gpu=True)
        print("[Engine]: Ready.")

    def is_korean(self, text):
        return bool(re.search("[\uac00-\ud7a3]", text))

    def process_image(self, image_path, sort_direction="top_to_bottom"):
        print(f"[Engine]: Scanning screen...")
        img = cv2.imread(image_path)
        if img is None: return []
            
        # --- OPENCV ACCURACY UPGRADE ---
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Double the image size to read tiny text
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        # Force maximum contrast
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
        # Feed the CLEANED image to the AI
        ocr_results = self.kocr.readtext(thresh)
        # -------------------------------
        
        valid_lines = []
        for bbox, raw_text, confidence in ocr_results:
            if self.is_korean(raw_text) and confidence > 0.2:
                # Divide coordinates by 2 because we doubled the image size!
                x = int(bbox[0][0] / 2)
                y = int(bbox[0][1] / 2)
                valid_lines.append({"x": x, "y": y, "text": raw_text})
                
        if not valid_lines: return []

        # Sort top-to-bottom
        if sort_direction == "top_to_bottom":
            valid_lines.sort(key=lambda item: item['y'])
        
        # SMART CLUSTERING: Merge lines if they are physically close
        clustered_bubbles = []
        for line in valid_lines:
            if not clustered_bubbles:
                clustered_bubbles.append(line)
                continue
                
            last = clustered_bubbles[-1]
            vertical_gap = line['y'] - last['y']
            horizontal_shift = abs(line['x'] - last['x'])
            
            if vertical_gap < 100 and horizontal_shift < 100:
                last['text'] += " " + line['text'] 
                last['y'] = line['y']
            else:
                clustered_bubbles.append(line)

        # TRANSLATE
        final_results = []
        for bubble in clustered_bubbles:
            translated_text = self.translator.translate(text=bubble['text'])
            final_results.append({
                "original": bubble['text'], 
                "translation": translated_text
            })
            
        return final_results