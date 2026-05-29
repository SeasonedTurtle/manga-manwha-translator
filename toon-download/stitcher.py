import os
from PIL import Image

class MangaStitcher:
    def __init__(self, input_dir="raw_chapters", output_dir="stitched_chapters"):
        self.input_dir = input_dir
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def stitch_chapter(self, chapter_number, images_per_strip=5, max_height=10000):
        chapter_folder = os.path.join(self.input_dir, f"chapter_{chapter_number}")
        output_folder = os.path.join(self.output_dir, f"chapter_{chapter_number}")
        os.makedirs(output_folder, exist_ok=True)

        if not os.path.exists(chapter_folder):
            print(f"[Stitcher]: Error - Target folder {chapter_folder} does not exist.")
            return []

        # 1. Gather and sort files to keep exact reading order
        all_files = [f for f in os.listdir(chapter_folder) if f.startswith("page_") and f.endswith(".jpg")]
        all_files.sort()
        
        if not all_files:
            print(f"[Stitcher]: No valid 'page_*.jpg' files found in {chapter_folder}.")
            return []

        full_paths = [os.path.join(chapter_folder, f) for f in all_files]
        print(f"[Stitcher]: Found {len(full_paths)} panels. Compiling into strips...")

        strip_paths = []
        current_batch = []
        strip_index = 1

        for file_path in full_paths:
            current_batch.append(file_path)
            
            # Check if it's time to process the current batch
            if len(current_batch) == images_per_strip:
                strip_path = self._create_vertical_strip(current_batch, output_folder, strip_index, max_height)
                strip_paths.append(strip_path)
                current_batch = []
                strip_index += 1

        # Process any leftover images that didn't fill a complete batch
        if current_batch:
            strip_path = self._create_vertical_strip(current_batch, output_folder, strip_index, max_height)
            strip_paths.append(strip_path)

        print(f"[Stitcher]: Finished! Condensed {len(full_paths)} panels into {len(strip_paths)} strips.")
        return strip_paths

    def _create_vertical_strip(self, img_paths, output_folder, index, max_height):
        # Open all images in the current batch
        images = [Image.open(p) for p in img_paths]

        # 2. Normalize Widths (Manhwa panels can sometimes vary slightly in width)
        # We find the most common width (the first image) and scale others to match it
        target_width = images[0].width
        normalized_images = []
        
        total_height = 0
        for img in images:
            if img.width != target_width:
                # Calculate new height to maintain aspect ratio
                scale_ratio = target_width / img.width
                new_height = int(img.height * scale_ratio)
                img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
            
            normalized_images.append(img)
            total_height += img.height

        # Failsafe: Truncate height if it exceeds safe API limits
        if total_height > max_height:
            print(f"  -> [Warning]: Strip {index} height ({total_height}px) exceeds limit. Capping at {max_height}px.")
            total_height = max_height

        # 3. Create a blank canvas canvas
        # Determine the canvas mode (RGB is standard for color manhwa)
        canvas_mode = normalized_images[0].mode if normalized_images[0].mode in ('RGB', 'RGBA') else 'RGB'
        strip_canvas = Image.new(canvas_mode, (target_width, total_height))

        # 4. Paste images vertically sequentially
        current_y = 0
        for img in normalized_images:
            if current_y + img.height > total_height:
                break # Stop pasting if we run out of canvas due to max_height restriction
            strip_canvas.paste(img, (0, current_y))
            current_y += img.height

        # Save the finalized strip
        output_path = os.path.join(output_folder, f"strip_{index:03d}.jpg")
        strip_canvas.save(output_path, "JPEG", quality=85)
        
        print(f"  -> Saved strip_{index:03d}.jpg (Contains {len(img_paths)} panels)")
        return output_path