# Manga & Manhwa Screen Translator

A fast, lightweight desktop tool built with Python and PyQt6 that instantly translates Korean manga and manhwa directly from your screen. It features a custom drag-and-drop snipping tool, OpenCV image preprocessing to handle jagged comic fonts, and GPU-accelerated EasyOCR for near-instant text extraction.

## Requirements

* **OS:** Linux (Tested on Ubuntu/Debian) / Windows / macOS
* **Python:** Version 3.8 to 3.12
* **Hardware:** An NVIDIA GPU is highly recommended for real-time translation speeds.
* **Core Libraries:**
  * `PyQt6` (For the UI and transparent screen overlay)
  * `opencv-python` (For image cleaning and text isolation)
  * `easyocr` (For Korean text detection)
  * `torch` (PyTorch with CUDA 11.8 for GPU acceleration)
  * `deep-translator` (For text translation)
  * `pyscreenshot` (For targeted screen capturing)
  * `ultralytics` (For YOLOv8 bubble detection)

## How to install

**1. Clone the repository and navigate into it**
```bash
git clone https://github.com/SeasonedTurtle/manga-manwha-translator.git
cd manga-manwha-translator

2. Create and activate a virtual environment

python3 -m venv env
source env/bin/activate

3. Install the GPU-Accelerated version of PyTorch
(This step is crucial for fast OCR processing. Do not skip this if you have an NVIDIA GPU).

pip install --upgrade pip
pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu118

4. Install the remaining dependencies

pip install PyQt6 opencv-python easyocr deep-translator pyscreenshot ultralytics

5. Add the YOLO weights (Optional/Advanced)
If you are using the YOLO text bubble detector, ensure your your_bubble_detector.pt file is placed directly in the root folder of the project.

**How To Run**

Activate your environment and launch the main Python script:

source env/bin/activate
python main.py

How to use

    Launch the App: Run the script. A control panel and an empty translation side-panel will appear on your screen.

    Set Your Target Zone: Click the Set Translation Area button. Your screen will slightly dim. Click and drag a box specifically over the manga page on your browser/reader to lock in the camera's focus.

    Translate: Click Translate Area. The app will instantly scan the targeted zone, process the text, and output the English translations in the side panel.

    Read: Turn the page on your browser, and hit Translate Area again.

    Clear: Use the Clear Panel button to wipe old translations if the UI gets too cluttered.

Examples: /tmp/tmphtpvwfpq.PNG
