import easyocr
import cv2
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
        
        # Initialize Online Translator
        self.translator_online = GoogleTranslator(source='ko', target='en')
        
        # Initialize Offline Translator
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
            return []

        results = []
        korean_texts = []
        
        print(f"[Engine]: Extracting text from {len(bubbles)} bubble(s)...")
        for b in bubbles:
            crop_img = b['crop']
            
            upscaled = cv2.resize(crop_img, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
            gray = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)
            smooth = cv2.bilateralFilter(gray, 9, 75, 75)
            binary = cv2.adaptiveThreshold(smooth, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)
            
            ocr_result = self.reader.readtext(binary, detail=0, paragraph=True, adjust_contrast=0.5)
            
            if ocr_result:
                korean_texts.append(" ".join(ocr_result))
            else:
                korean_texts.append("") 

        if not any(korean_texts):
            return []

        print(f"[Engine]: Translating using {self.mode.upper()} mode...")
        
        if self.mode == "online":
            # Batch process for high speed over the network
            english_texts = self.translator_online.translate_batch(korean_texts)
        else:
            # Local process using hardware
            english_texts = []
            for text in korean_texts:
                if text.strip() and self.translator_offline:
                    english_texts.append(self.translator_offline.translate(text))
                else:
                    english_texts.append("")

        for kr, en in zip(korean_texts, english_texts):
            if kr.strip(): 
                results.append({'original': kr, 'translation': en})
                
        return results