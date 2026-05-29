import os
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from DrissionPage import ChromiumPage, ChromiumOptions

class MangaScraper:
    def __init__(self, output_dir="raw_chapters"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.session = requests.Session()

    def _sync_browser_state(self, page):
        """Steals the Cookies and User-Agent safely across all DrissionPage versions."""
        try:
            raw_cookies = page.cookies()
            cookie_dict = {}
            
            # Safely parse the cookies whether DrissionPage returned a list or a dict
            if isinstance(raw_cookies, list):
                for cookie in raw_cookies:
                    if 'name' in cookie and 'value' in cookie:
                        cookie_dict[cookie['name']] = cookie['value']
            elif isinstance(raw_cookies, dict):
                cookie_dict = raw_cookies
                
            self.session.cookies.update(cookie_dict)
        except Exception as e:
            print(f"[Scraper Warning]: Cookie sync hiccuped. Attempting to proceed anyway. ({e})")
        
        try:
            # Grab the exact browser fingerprint
            user_agent = page.run_js("return navigator.userAgent;")
            self.session.headers.update({
                "User-Agent": user_agent,
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                "Referer": page.url
            })
        except Exception as e:
            print(f"[Scraper Warning]: User-Agent sync failed. ({e})")
        
        print("[Scraper]: Synced browser state. Bypassing hotlink protections...")

    def _scroll_to_bottom(self, page):
        """Systematic deep-scroll to force all lazy-loaded images to render."""
        print("[Scraper]: Initiating deep-scroll to force lazy-loading...")
        previous_height = 0
        
        # Failsafe counter to prevent infinite loops on weirdly coded sites
        max_scrolls = 50 
        scroll_count = 0
        
        while scroll_count < max_scrolls:
            page.scroll.down(800)
            time.sleep(0.8) # Crucial wait time for the image chunks to pop in
            
            current_height = page.run_js('return document.body.scrollHeight;')
            
            if current_height == previous_height:
                # Do one final small scroll and wait just to be absolutely sure
                page.scroll.to_bottom()
                time.sleep(2) 
                break
                
            previous_height = current_height
            scroll_count += 1
            
        print("[Scraper]: Reached the true bottom of the page.")

    def _download_single_image(self, src, file_path, index):
        """Worker function for concurrent downloading."""
        try:
            response = self.session.get(src.strip(), timeout=15)
            if response.status_code == 200:
                with open(file_path, "wb") as f:
                    f.write(response.content)
                return index, file_path, True, None
            else:
                return index, src, False, f"HTTP {response.status_code}"
        except Exception as e:
            return index, src, False, str(e)

    def download_chapter(self, base_url, chapter_number):
        base_url = base_url.rstrip('/')
        full_url = f"{base_url}/{chapter_number}/"
        
        chapter_dir = os.path.join(self.output_dir, f"chapter_{chapter_number}")
        os.makedirs(chapter_dir, exist_ok=True)

        print(f"[Scraper]: Spinning up DrissionPage to hit: {full_url}")
        
        co = ChromiumOptions()
        co.set_browser_path('/usr/bin/google-chrome')
        # co.headless(True)
        
        try:
            page = ChromiumPage(co)
            page.get(full_url)
            
            # Sync session and trigger lazy loads immediately
            self._sync_browser_state(page)
            self._scroll_to_bottom(page)

            print("[Scraper]: Hunting for comic panels...")
            images = page.eles('.reading-content img') or page.eles('.page-break img') or page.eles('tag:img')

            valid_sources = []
            for img in images:
                src = img.attr('data-src') or img.attr('src')
                if src and src.startswith("http") and "logo" not in src.lower() and "avatar" not in src.lower():
                    valid_sources.append(src)

            print(f"[Scraper]: Found {len(valid_sources)} clean panels. Initiating hyper-threaded download...")

            downloaded_files = []
            failed_downloads = []
            
            # Spin up 5 concurrent workers
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_url = {
                    executor.submit(
                        self._download_single_image, 
                        src, 
                        os.path.join(chapter_dir, f"page_{idx:03d}.jpg"), 
                        idx
                    ): src for idx, src in enumerate(valid_sources, 1)
                }
                
                for future in as_completed(future_to_url):
                    idx, path_or_src, success, error = future.result()
                    if success:
                        downloaded_files.append((idx, path_or_src))
                        print(f"  -> [OK] Saved page_{idx:03d}.jpg")
                    else:
                        failed_downloads.append((idx, path_or_src))
                        print(f"  -> [!] Failed page_{idx:03d}.jpg ({error})")

        except Exception as e:
            print(f"[Scraper]: Critical failure during scraping: {e}")
            return []
        finally:
            try:
                page.quit()
            except:
                pass # Fail silently if the browser is already closed
            
        # Ensure they are sorted back into reading order since threads finish randomly
        downloaded_files.sort(key=lambda x: x[0])
        final_paths = [file for idx, file in downloaded_files]

        print(f"\n[Scraper]: Success! Ripped {len(final_paths)} pages to '{chapter_dir}'.")
        if failed_downloads:
            print(f"[Scraper]: Note - {len(failed_downloads)} images failed to download.")
            
        return final_paths