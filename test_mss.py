import mss
import mss.tools
import time
import os

def test_mss_speed():
    print("\n=== MSS Speed & Diagnostic Test ===")
    
    # 1. Ask Linux what display server is actually running
    session_type = os.environ.get("XDG_SESSION_TYPE", "unknown")
    print(f"🖥️  Current Display Session: {session_type.upper()}")
    
    if session_type.lower() == "wayland":
        print("⚠️  WARNING: You are still running Wayland! That is why the image is black.")
        print("   Wayland blocks background screenshots and returns black pixels for security.")
    
    try:
        # Fixed the deprecation warning (mss.MSS instead of mss.mss)
        with mss.MSS() as sct:
            # monitors[0] combines all connected screens into one massive picture
            monitor = sct.monitors[0] 
            
            start_time = time.perf_counter()
            sct_img = sct.grab(monitor)
            mss.tools.to_png(sct_img.rgb, sct_img.size, output="mss_test_capture.png")
            end_time = time.perf_counter()
            
        print(f"\n✅ Capture complete in {end_time - start_time:.4f} seconds")
        print(f"📸 Saved to: {os.path.abspath('mss_test_capture.png')}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    test_mss_speed()