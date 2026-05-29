import os
import time
from engine import TranslationEngine

def run_engine_test():
    print("\n=== UNIT TEST 2: THE STITCHED BRAIN ===")
    
    test_image = os.path.abspath("images/capture.png")
    
    if not os.path.exists(test_image):
        print(f"❌ FAIL: Could not find {test_image}.")
        return
        
    try:
        print("Booting up the Translation Engine...")
        engine = TranslationEngine(start_mode="offline") 
        
        # --- THE WARM-UP RUN ---
        print("\n🔥 Waking up GPU (Cold Start)...")
        engine.process_image(test_image) 
        print("GPU is awake and VRAM is locked.")
        
        # --- THE TRUE SPEED RUN ---
        print(f"\nProcessing real image in {engine.mode.upper()} mode...")
        process_start = time.perf_counter()
        
        result = engine.process_image(test_image)
        
        process_end = time.perf_counter()
        execution_time = process_end - process_start
        
        if result:
            print(f"\n✅ PASS: Engine read and translated the image!")
            print(f"⚡ TRUE PROCESSING SPEED: {execution_time:.3f} seconds\n")
            
            for index, bubble in enumerate(result, 1):
                print(f"Bubble {index}: {bubble['translation']}")
                
    except Exception as e:
        print(f"\n❌ FAIL: Engine crashed. Error: {e}")

if __name__ == "__main__":
    run_engine_test()