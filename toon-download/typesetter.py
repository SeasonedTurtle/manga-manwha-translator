import os
import json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

class MangaTypesetter:
    def __init__(self, input_dir="stitched_chapters", output_dir="final_chapters"):
        self.input_dir = input_dir
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def process_chapter(self, chapter_number):
        chapter_folder = os.path.join(self.input_dir, f"chapter_{chapter_number}")
        output_folder = os.path.join(self.output_dir, f"chapter_{chapter_number}")
        os.makedirs(output_folder, exist_ok=True)

        if not os.path.exists(chapter_folder):
            print(f"[Typesetter]: Error - Chapter folder {chapter_folder} not found.")
            return

        # Find all stitched image strips
        strips = [f for f in os.listdir(chapter_folder) if f.endswith(".jpg")]
        strips.sort()

        print(f"[Typesetter]: Found {len(strips)} strips to process. Starting canvas construction...")
        
        final_pdf_pages = []

        for strip_file in strips:
            image_path = os.path.join(chapter_folder, strip_file)
            json_path = os.path.join(chapter_folder, strip_file.replace(".jpg", ".json"))

            if not os.path.exists(json_path):
                print(f"[Typesetter]: Warning - Missing translation JSON for {strip_file}. Copying raw image...")
                raw_img = Image.open(image_path).convert("RGB")
                final_pdf_pages.append(raw_img)
                continue

            print(f"[Typesetter]: Typesetting {strip_file}...")
            
            # 1. Load image and translation mapping
            pil_img = Image.open(image_path).convert("RGB")
            with open(json_path, 'r', encoding='utf-8') as f:
                translations = json.load(f)

            # 2. Render modifications onto the image
            processed_img = self._typeset_strip(pil_img, translations)
            
            # Save individual translated strip
            output_strip_path = os.path.join(output_folder, strip_file)
            processed_img.save(output_strip_path, "JPEG", quality=90)
            final_pdf_pages.append(processed_img)
            
        # 3. Reconstruct into a single portable file (PDF)
        if final_pdf_pages:
            pdf_output_path = os.path.join(self.output_dir, f"Chapter_{chapter_number}_English.pdf")
            final_pdf_pages[0].save(
                pdf_output_path, 
                save_all=True, 
                append_images=final_pdf_pages[1:], 
                options={"quality": 85}
            )
            print(f"\n[Typesetter]: Success! Final compiled book saved to: {pdf_output_path}")

    def _typeset_strip(self, pil_img, translations):
        width, height = pil_img.size
        cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        # Step A: Clean bubbles with an aggressive Inpainting mask
        mask = np.zeros(cv_img.shape[:2], dtype=np.uint8)
        
        valid_boxes = []
        for item in translations:
            if "box_2d" not in item or not item["box_2d"]:
                continue
            
            ymin, xmin, ymax, xmax = item["box_2d"]
            ymin_px = int((ymin / 1000) * height)
            xmin_px = int((xmin / 1000) * width)
            ymax_px = int((ymax / 1000) * height)
            xmax_px = int((xmax / 1000) * width)
            
            valid_boxes.append((xmin_px, ymin_px, xmax_px, ymax_px, item.get("english", "")))
            
            # Draw the initial erasure zone
            cv2.rectangle(mask, (xmin_px, ymin_px), (xmax_px, ymax_px), 255, -1)

        # --- THE GHOSTING FIX: DILATE THE MASK ---
        # This expands the erase boxes by ~3 pixels to catch blurry text edges
        kernel = np.ones((3, 3), np.uint8)
        dilated_mask = cv2.dilate(mask, kernel, iterations=2)

        # Run Telea Inpainting with the expanded mask and a slightly larger radius (5)
        cleaned_cv_img = cv2.inpaint(cv_img, dilated_mask, 5, cv2.INPAINT_TELEA)
        
        clean_pil_img = Image.fromarray(cv2.cvtColor(cleaned_cv_img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(clean_pil_img)

        # Step B: Font Setup
        try:
            # Note: For even better results, download a free comic font like "CC Wild Words" 
            # or "Anime Ace" and point this path to it!
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            font = ImageFont.truetype(font_path, 18)
        except IOError:
            font = ImageFont.load_default()

        # Step C: Draw text with White Outlines
        for xmin, ymin, xmax, ymax, text in valid_boxes:
            box_width = xmax - xmin
            box_height = ymax - ymin
            
            wrapped_lines = self._wrap_text(text, font, box_width - 20)
            
            line_heights = []
            for line in wrapped_lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_heights.append(bbox[3] - bbox[1])
            
            total_text_height = sum(line_heights) + (len(wrapped_lines) - 1) * 4
            current_y = ymin + (box_height - total_text_height) // 2
            
            for i, line in enumerate(wrapped_lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                current_x = xmin + (box_width - line_width) // 2
                
                # --- THE CONTRAST FIX: STROKE WIDTH ---
                # Draw sharp black text with a 2-pixel white outline
                draw.text(
                    (current_x, current_y), 
                    line, 
                    fill=(0, 0, 0), 
                    font=font, 
                    stroke_width=2, 
                    stroke_fill=(255, 255, 255)
                )
                current_y += line_heights[i] + 4

        return clean_pil_img
        # Step C: Draw wrapped, centered English text over clean bubbles
        for xmin, ymin, xmax, ymax, text in valid_boxes:
            box_width = xmax - xmin
            box_height = ymax - ymin
            
            # Wrap text to fit the bubble width constraints safely
            wrapped_lines = self._wrap_text(text, font, box_width - 20)
            
            # Calculate total height of wrapped text block to center it vertically
            line_heights = []
            for line in wrapped_lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_heights.append(bbox[3] - bbox[1])
            
            total_text_height = sum(line_heights) + (len(wrapped_lines) - 1) * 4
            
            # Center alignment entry point calculation
            current_y = ymin + (box_height - total_text_height) // 2
            
            for i, line in enumerate(wrapped_lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                current_x = xmin + (box_width - line_width) // 2
                
                # Draw sharp black text
                draw.text((current_x, current_y), line, fill=(0, 0, 0), font=font)
                current_y += line_heights[i] + 4

        return clean_pil_img

    def _wrap_text(self, text, font, max_width):
        """Helper logic to split English strings into perfectly dimensioned lines."""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            # Probe font pixel bounding box requirements
            img = Image.new('RGB', (1, 1))
            probe_draw = ImageDraw.Draw(img)
            bbox = probe_draw.textbbox((0, 0), test_line, font=font)
            test_width = bbox[2] - bbox[0]

            if test_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                
        if current_line:
            lines.append(' '.join(current_line))
        return lines
    
if __name__ == "__main__":
    print("=== RUNNING STANDALONE TYPESETTER ===")
    # Initialize the engine
    engine = MangaTypesetter()
    # Point it at the chapter you already translated
    engine.process_chapter(chapter_number="1")