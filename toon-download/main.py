import os
import time
from dotenv import load_dotenv

from scraper import MangaScraper
from stitcher import MangaStitcher
from translator import MangaTranslator
from typesetter import MangaTypesetter

# Load the hidden variables from the .env file
load_dotenv()

# Pull variables securely
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BASE_URL = os.getenv("BASE_URL")

def process_single_chapter(chapter_num, scraper, stitcher, translator, typesetter):
    """Processes a single chapter end-to-end."""
    print(f"\n=========================================")
    print(f"=== INITIATING PROTOCOL FOR CHAPTER {chapter_num} ===")
    print(f"=========================================\n")
    
    # ACQUISITION 
    image_paths = scraper.download_chapter(BASE_URL, chapter_num)
    if not image_paths:
        print(f"[System Error]: Scraper failed on Chapter {chapter_num}. Skipping.")
        return False

    # IMAGE STITCHING 
    print(f"\n[System]: Compressing Chapter {chapter_num} into strips...")
    strip_paths = stitcher.stitch_chapter(chapter_number=chapter_num, images_per_strip=5)
    if not strip_paths:
        print(f"[System Error]: Stitching failed on Chapter {chapter_num}. Skipping.")
        return False
        
    # TRANSLATION 
    print(f"\n[System]: Deploying Gemini Translation Engine for Chapter {chapter_num}...")
    translator.process_chapter(chapter_number=chapter_num)

    # INPAINTING & TYPESETTING ---
    print(f"\n[System]: Commencing typesetting and PDF compilation for Chapter {chapter_num}...")
    typesetter.process_chapter(chapter_number=chapter_num)
    
    print(f"\n[System]: Chapter {chapter_num} SUCCESSFUL.")
    return True

def bulk_run(start_chapter, end_chapter):
    # Check if the user is a knower or impacient loser
    if not GEMINI_API_KEY or GEMINI_API_KEY == "insert_your_api_key_here":
        print("\n[System Halt]: Please insert a valid Gemini API key into your .env file.")
        return
        
    if not BASE_URL or BASE_URL == "insert_base_manga_url_here":
        print("\n[System Halt]: Please insert a valid target BASE_URL into your .env file.")
        return

    print("=== STARTING THE AUTOMATED BATCH PIPELINE ===")
    
    # Initialize all engines once to save overhead
    scraper = MangaScraper()
    stitcher = MangaStitcher()
    translator = MangaTranslator(api_key=GEMINI_API_KEY)
    typesetter = MangaTypesetter()

    successful_chapters = []
    failed_chapters = []

    for i in range(start_chapter, end_chapter + 1):
        chapter_str = str(i)
        
        try:
            success = process_single_chapter(chapter_str, scraper, stitcher, translator, typesetter)
            if success:
                successful_chapters.append(chapter_str)
            else:
                failed_chapters.append(chapter_str)
        except Exception as e:
            print(f"\n[CRITICAL ERROR]: Chapter {chapter_str} encountered a fatal exception: {e}")
            failed_chapters.append(chapter_str)
            
        # --- BATCH PACING (Crucial for not getting banned) ---
        if i != end_chapter:
            print("\n[System]: Cooling down for 60 seconds before next chapter...")
            print("[System]: This prevents IP bans and resets API burst limits.")
            time.sleep(60)

    # Final Report
    print("\n=========================================")
    print("=== BATCH PROCESSING COMPLETE ===")
    print(f"Successfully processed: {len(successful_chapters)} chapters")
    if failed_chapters:
        print(f"Failed chapters requiring manual review: {', '.join(failed_chapters)}")
    print("=========================================")

if __name__ == "__main__":
    # Select range of chapters to run
    # usually do 8-9 at a time unless you pay for an api
    start = 21
    end = 25
    bulk_run(start, end)