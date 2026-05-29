import os
import time
import json
import google.generativeai as genai
from PIL import Image

class MangaTranslator:
    # Notice we default to the model with the best free daily limit from your list
    def __init__(self, api_key, model_name="gemini-3.1-flash-lite", input_dir="stitched_chapters"):
        genai.configure(api_key=api_key)
        self.input_dir = input_dir
        
        print(f"[Translator]: Booting up Gemini Vision API ({model_name})...")
        # Enforce strict JSON output
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={"response_mime_type": "application/json"}
        )

    def process_chapter(self, chapter_number):
        chapter_dir = os.path.join(self.input_dir, f"chapter_{chapter_number}")
        if not os.path.exists(chapter_dir):
            print(f"[Translator]: Error - Cannot find {chapter_dir}. Did you stitch them?")
            return

        # Grab only the stitched images
        strips = [f for f in os.listdir(chapter_dir) if f.endswith(".jpg")]
        strips.sort()

        print(f"[Translator]: Found {len(strips)} strips. Engaging translation protocol...")

        for strip_file in strips:
            image_path = os.path.join(chapter_dir, strip_file)
            json_path = os.path.join(chapter_dir, strip_file.replace(".jpg", ".json"))

            # Crash-Proofing: Skip if we already translated it
            if os.path.exists(json_path):
                print(f"[Translator]: Skipping {strip_file} - JSON already exists.")
                continue

            print(f"[Translator]: Analyzing {strip_file}...")
            
            try:
                img = Image.open(image_path)
                result_json = self._call_gemini(img)
                
                # Save the JSON data alongside the image
                with open(json_path, 'w', encoding='utf-8') as f:
                    f.write(result_json)
                    
                print(f"  -> [OK] Translations extracted and saved to {strip_file.replace('.jpg', '.json')}")
                
            except Exception as e:
                print(f"  -> [!] Failed to translate {strip_file}. Error: {e}")
            
            # Rate Limit Protection: Wait 5 seconds to ensure we stay under 15 RPM
            print("  -> Cooling down for 5 seconds to respect API limits...")
            time.sleep(5) 
            
        print(f"\n[Translator]: Chapter {chapter_number} text extraction complete!")
            
    def _call_gemini(self, img):
        prompt = """
        You are an expert Manhwa/Webtoon translator. Analyze this vertical comic strip.
        Identify every speech bubble or text box containing Korean text. 
        
        For each text region, provide:
        1. "box_2d": The bounding box of the text area in the format [ymin, xmin, ymax, xmax] using normalized coordinates from 0 to 1000.
        2. "korean": The original Korean text.
        3. "english": Your accurate, natural-sounding English translation.

        Output ONLY a JSON array of objects. Example format:
        [
            {
                "box_2d": [150, 400, 200, 600],
                "korean": "무슨 일이야?",
                "english": "What's going on?"
            }
        ]
        """
        
        response = self.model.generate_content([prompt, img])
        return response.text