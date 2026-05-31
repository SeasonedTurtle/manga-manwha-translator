import os
import time
import json
import re 
import google.generativeai as genai
from PIL import Image

# Import your telemetry tracker
from quota_tracker import log_api_call 

class MangaTranslator:
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

        strips = [f for f in os.listdir(chapter_dir) if f.endswith(".jpg")]
        strips.sort()

        print(f"[Translator]: Found {len(strips)} strips. Engaging translation protocol...")

        for strip_file in strips:
            image_path = os.path.join(chapter_dir, strip_file)
            json_path = os.path.join(chapter_dir, strip_file.replace(".jpg", ".json"))

            if os.path.exists(json_path):
                print(f"[Translator]: Skipping {strip_file} - JSON already exists.")
                continue

            print(f"[Translator]: Analyzing {strip_file}...")
            
            # --- DYNAMIC RETRY LOOP ---
            max_retries = 3
            attempts = 0
            
            while attempts < max_retries:
                try:
                    img = Image.open(image_path)
                    result_json = self._call_gemini(img)
                    
                    with open(json_path, 'w', encoding='utf-8') as f:
                        f.write(result_json)
                        
                    print(f"  -> [OK] Translations extracted and saved.")
                    log_api_call(1) # Log successful API call
                    
                    # Normal pacing cooldown
                    print("  -> Cooling down for 5 seconds to respect RPM limits...")
                    time.sleep(5)
                    break # Break out of the retry loop if successful!
                    
                except Exception as e:
                    error_str = str(e)
                    
                    # Look for the exact quota violation pattern Google sends
                    if "quota_metric" in error_str and "retry_delay" in error_str:
                        # Use Regex to extract the number of seconds
                        match = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)\s*\}", error_str)
                        
                        if match:
                            delay_seconds = int(match.group(1))
                            safe_sleep = delay_seconds + 2 # Add a 2-second buffer
                            
                            print(f"\n  -> [API LIMIT HIT]: Google requested a {delay_seconds}s cooldown.")
                            print(f"  -> Entering hibernation for {safe_sleep} seconds...")
                            
                            time.sleep(safe_sleep)
                            attempts += 1
                            print("  -> Waking up. Retrying image...")
                            continue # Jump back to the top of the while loop and try again!

                    # If it's a completely different error, or we ran out of retries:
                    print(f"  -> [!] Fatal error translating {strip_file}. Error: {error_str[:150]}...")
                    break # Break out of the retry loop and move to the next image
            
        print(f"\n[Translator]: Chapter {chapter_number} text extraction complete!")
            
    def _call_gemini(self, img):
        # The Upgraded Memory Module Prompt
        prompt = """
        You are an expert Manhwa/Webtoon translator. Analyze this vertical comic strip.
        Identify every speech bubble, text box, and floating text containing Korean.
        
        CRITICAL SERIES CONTEXT:
        - Maintain a casual, modern tone. 
        - Character Names: Translate consistently based on common manhwa conventions if names appear.
        
        For each text region, provide:
        1. "box_2d": The bounding box tightened STRICTLY around the text itself (do not include the empty space or the tail of the speech bubble), using normalized coordinates from 0 to 1000.
        2. "korean": The original Korean text.
        3. "english": Your accurate, natural-sounding English translation.

        Output ONLY a JSON array of objects.
        """
        
        response = self.model.generate_content([prompt, img])
        return response.text