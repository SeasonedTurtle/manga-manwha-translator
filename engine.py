import easyocr
import cv2
import numpy as np
import argostranslate.package
import argostranslate.translate
from deep_translator import GoogleTranslator
from detector import BubbleDetector

class TranslationEngine:
    def __init__(self, start_mode="offline"):
        print("[Engine]: Spinning up EasyOCR with GPU acceleration...")
        self.reader = easyocr.Reader(['ko'], gpu=True)
        self.detector = BubbleDetector(model_path="comic-speech-bubble-detector.pt")
        
        self.mode = start_mode
        
        self.translator_online = GoogleTranslator(source='ko', target='en')
        
        print("[Engine]: Checking offline translator models...")
        self._setup_offline_translator()

    def _setup_offline_translator(self):
        argostranslate.package.update_package_index()
        available_packages = argostranslate.package.get_available_packages()
        
        package_to_install = next(
            filter(lambda x: x.from_code == 'ko' and x.to_code == 'en', available_packages), None
        )
        
        if package_to_install:
            installed = argostranslate.package.get_installed_packages()
            is_installed = any(p.from_code == 'ko' and p.to_code == 'en' for p in installed)
            
            if not is_installed:
                print("[Engine]: Downloading Korean -> English offline model...")
                argostranslate.package.install_from_path(package_to_install.download())
                
        installed_languages = argostranslate.translate.get_installed_languages()
        ko = next((lang for lang in installed_languages if lang.code == 'ko'), None)
        en = next((lang for lang in installed_languages if lang.code == 'en'), None)
        
        if ko and en:
            self.translator_offline = ko.get_translation(en)
        else:
            self.translator_offline = None

    def process_image(self, img_path):
        bubbles = self.detector.extract_bubbles(img_path)
        
        if not bubbles:
            print("[Engine]: No bubbles found in this area.")
            return # Stops the stream

        processed_crops = []
        
        print(f"[Engine]: Preparing {len(bubbles)} bubble(s) for the GPU...")
        
        for b in bubbles:
            crop_img = b['crop']
            
            if crop_img.size == 0:
                continue
                
            upscaled = cv2.resize(crop_img, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
            gray = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)
            smooth = cv2.bilateralFilter(gray, 9, 75, 75)
            binary = cv2.adaptiveThreshold(smooth, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)
            
            padded = cv2.copyMakeBorder(binary, 0, 50, 0, 0, cv2.BORDER_CONSTANT, value=[255, 255, 255])
            processed_crops.append(padded)

        if not processed_crops:
            return # Stops the stream

        max_width = max(img.shape[1] for img in processed_crops)

        uniform_crops = []
        for img in processed_crops:
            pad_right = max_width - img.shape[1]
            uniform_img = cv2.copyMakeBorder(img, 0, 0, 0, pad_right, cv2.BORDER_CONSTANT, value=[255, 255, 255])
            uniform_crops.append(uniform_img)

        master_image = cv2.vconcat(uniform_crops)

        print("[Engine]: Firing GPU OCR on master image...")
        korean_texts = self.reader.readtext(
            master_image, 
            detail=0, 
            paragraph=True, 
            adjust_contrast=0.5,
            text_threshold=0.95,  # Default is 0.4. This forces EasyOCR to be 70% confident before guessing.
            mag_ratio=1.5        # slightly improves image quality for the AI's internal reader
        )

        if not korean_texts:
            return # Stops the stream

        korean_texts = [text for text in korean_texts if text.strip()]

        if not korean_texts:
            return # Stops the stream

        print(f"[Engine]: Translating using {self.mode.upper()} mode...")
        
        if self.mode == "online":
            english_texts = self.translator_online.translate_batch(korean_texts)
            for kr, en in zip(korean_texts, english_texts):
                yield {'original': kr, 'translation': en} 
        else:
            for kr in korean_texts:
                if self.translator_offline:
                    en = self.translator_offline.translate(kr)
                else:
                    en = "[Offline Error]"
                yield {'original': kr, 'translation': en}