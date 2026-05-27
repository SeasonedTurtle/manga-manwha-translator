from ultralytics import YOLO

# --- SETUP ---
# Replace with the actual name of your YOLO weights file
model_path = "comic-speech-bubble-detector.pt"

# Replace with a picture of a manga page to test
test_image = "Screenshot 2026-05-26 at 23-52-28 Read The Hottie’s Good at Football RAW 56 - RawDEX.png" 
# -------------

print(f"Loading model: {model_path}...")
model = YOLO(model_path)

print("Running detection...")
# The model analyzes the image. 'conf=0.25' means it only accepts boxes it is 25% sure about.
results = model(test_image, conf=0.25)

print(f"Found {len(results[0].boxes)} text bubbles!")

# This will pop open a window showing the image with bounding boxes drawn over the text bubbles!
results[0].show()