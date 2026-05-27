import os
from engine import TranslationEngine

def run_engine_test():
    print("\n=== UNIT TEST 2: THE BRAIN ===")
    
    test_image = os.path.abspath("images/test_capture.png")
    
    if not os.path.exists(test_image):
        print(f"❌ FAIL: Could not find {test_image}.")
        return
        
    try:
        # Initializing the engine in Korean mode
        engine = TranslationEngine(mode="korean") 
        
        result = engine.process_image(test_image)
        
        if result:
            print("\n✅ PASS: Engine successfully read and translated the image!")
        else:
            print("\n⚠️ PARTIAL: Engine ran perfectly, but found zero readable text in the image.")
            
    except Exception as e:
        print(f"\n❌ FAIL: Engine crashed. Error: {e}")

if __name__ == "__main__":
    run_engine_test()