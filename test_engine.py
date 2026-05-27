import os
import time
from engine import TranslationEngine

def run_engine_test():
    print("\n=== UNIT TEST 2: THE BRAIN ===")
    
    test_image = os.path.abspath("images/capture.png")
    
    if not os.path.exists(test_image):
        print(f"❌ FAIL: Could not find {test_image}.")
        return
        
    try:
        # Time the engine initialization (Loading models into VRAM)
        print("Booting up the Translation Engine...")
        init_start = time.perf_counter()
        engine = TranslationEngine(mode="korean") 
        init_end = time.perf_counter()
        print(f"⏱️ Engine Boot Time: {init_end - init_start:.3f} seconds")
        
        print("\nProcessing image...")
        # Time the actual AI execution and network request
        process_start = time.perf_counter()
        result = engine.process_image(test_image)
        process_end = time.perf_counter()
        
        execution_time = process_end - process_start
        
        if result:
            print("\n✅ PASS: Engine successfully read and translated the image!")
            print(f"⚡ Processing Speed: {execution_time:.3f} seconds")
        else:
            print("\n⚠️ PARTIAL: Engine ran perfectly, but found zero readable text in the image.")
            print(f"⚡ Processing Speed: {execution_time:.3f} seconds")
            
    except Exception as e:
        print(f"\n❌ FAIL: Engine crashed. Error: {e}")

if __name__ == "__main__":
    run_engine_test()