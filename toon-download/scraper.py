import os
import re
import time
from io import BytesIO
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

NHENTAI_GALLERY_RE = re.compile(r"https?://(?:www\.)?nhentai\.net/g/(\d+)", re.I)
READER_PAGE_RE = re.compile(r"/g/\d+/\d+/?($|\?)")
PAGE_COUNTER_RE = re.compile(r"\b(\d+)\s*(?:/|of)\s*(\d+)\b", re.I)
SKIP_SRC_TOKENS = ("logo", "avatar", "icon", "sprite", "spinner", "loading", "favicon", "blank.gif")
EXT_BY_CODE = {"j": "jpg", "p": "png", "g": "gif", "w": "webp", "a": "avif"}
DEFAULT_IMAGE_SERVERS = [
    "https://i1.nhentai.net",
    "https://i2.nhentai.net",
    "https://i3.nhentai.net",
    "https://i4.nhentai.net",
]
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

CURRENT_IMAGE_JS = r"""
return (() => {
  function absolute(src) {
    if (!src) return "";
    try { return new URL(src, location.href).href; } catch (e) { return ""; }
  }
  function fromImage(img) {
    if (!img) return "";
    const src = img.getAttribute("data-src")
      || img.getAttribute("data-original")
      || img.getAttribute("data-lazy-src")
      || img.currentSrc
      || img.src;
    if (!src || src.startsWith("data:") || src.startsWith("blob:")) return "";
    return absolute(src);
  }
  const preferred = [
    "#image-container img",
    "img#img",
    ".reader-main img",
    "#manga-reading-image",
    ".manga-page img",
    "img.fit-horizontal",
    "img.fit-vertical"
  ];
  for (const sel of preferred) {
    const found = fromImage(document.querySelector(sel));
    if (found) return found;
  }
  let best = "";
  let area = 0;
  for (const img of document.images) {
    const src = fromImage(img);
    if (!src) continue;
    const w = img.naturalWidth || img.width || 0;
    const h = img.naturalHeight || img.height || 0;
    if (w >= 400 && h >= 400 && w * h > area) {
      area = w * h;
      best = src;
    }
  }
  return best;
})();
"""

CLICK_NEXT_JS = r"""
return (() => {
  const bad = /chapter|comment|login|favorite|random/i;
  const selectors = [
    "a.next",
    "button.next",
    ".next-page",
    "a.next-page",
    "#next",
    ".nav-next a",
    ".nav-next",
    "a[rel='next']",
    ".pager .next a",
    "button[aria-label='Next']",
    "a[aria-label='Next']",
    "#image-container a"
  ];
  function usable(el) {
    if (!el) return false;
    const style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden") return false;
    const label = (el.innerText || "") + " " + (el.getAttribute("aria-label") || "")
      + " " + (el.id || "") + " " + (el.className || "");
    if (bad.test(label)) return false;
    if (el.classList.contains("disabled") || el.getAttribute("aria-disabled") === "true") return false;
    return true;
  }
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (usable(el)) {
      el.click();
      return "yes";
    }
  }
  if (document.querySelector("#image-container, img#img, .reader-main")) {
    const event = new KeyboardEvent("keydown", {
      key: "ArrowRight", code: "ArrowRight", keyCode: 39, which: 39, bubbles: true
    });
    document.dispatchEvent(event);
    window.dispatchEvent(event);
    return "key";
  }
  return "no";
})();
"""

READER_SIGNALS_JS = r"""
return (() => {
  const imgs = Array.from(document.images || []);
  const big = imgs.filter(img => (img.naturalWidth || img.width) >= 400 && (img.naturalHeight || img.height) >= 400);
  const text = ((document.body && document.body.innerText) || "").slice(0, 8000);
  const next = document.querySelector("a.next, button.next, #next, a[rel='next'], .next-page, #image-container a");
  return {
    scrollHeight: document.documentElement.scrollHeight || document.body.scrollHeight || 0,
    innerHeight: window.innerHeight || 1,
    imgCount: imgs.length,
    bigImgCount: big.length,
    lazyCount: document.querySelectorAll("img[data-src], img[data-lazy-src], img[data-original]").length,
    hasStrip: !!document.querySelector(".reading-content, .page-break, .long-strip, .chapter-content"),
    hasReader: !!document.querySelector("#image-container, img#img, .reader-main, .manga-page"),
    hasNext: !!next,
    snippet: text
  };
})();
"""

EMBEDDED_GALLERY_JS = r"""
return (() => {
  if (window._gallery) {
    try { return JSON.stringify(window._gallery); } catch (e) {}
  }
  return "";
})();
"""


def build_chapter_url(base_url, chapter_number):
    return f"{str(base_url).rstrip('/')}/{chapter_number}/"


def nhentai_gallery_id(url):
    if not url:
        return None
    match = NHENTAI_GALLERY_RE.search(str(url))
    return match.group(1) if match else None


def normalize_image_url(src, page_url=""):
    if not src:
        return ""
    src = str(src).strip()
    if src.startswith("data:") or src.startswith("blob:"):
        return ""
    absolute = urljoin(page_url, src) if page_url else src
    if absolute.startswith("http://") or absolute.startswith("https://"):
        return absolute
    return ""


def is_content_image(src):
    if not src:
        return False
    filename = src.lower().split("?", 1)[0].rsplit("/", 1)[-1]
    return not any(token in filename for token in SKIP_SRC_TOKENS)


def filter_image_sources(sources, page_url=""):
    cleaned = []
    seen = set()
    for src in sources:
        absolute = normalize_image_url(src, page_url)
        if not absolute or not is_content_image(absolute) or absolute in seen:
            continue
        seen.add(absolute)
        cleaned.append(absolute)
    return cleaned


def nhentai_page_urls(gallery, servers=None):
    """Build full-size page URLs from an nhentai gallery payload.

    Accepts the API v2 shape (pages[].path) and the older images.pages[].t shape.
    Each entry is a list of candidate URLs, one per image server.
    """
    if not isinstance(gallery, dict):
        return []
    hosts = [host.rstrip("/") for host in (servers or DEFAULT_IMAGE_SERVERS) if host]
    if not hosts:
        hosts = list(DEFAULT_IMAGE_SERVERS)

    pages = gallery.get("pages")
    if isinstance(pages, list) and pages and isinstance(pages[0], dict) and pages[0].get("path"):
        ordered = sorted(pages, key=lambda page: page.get("number") or 0)
        urls = []
        for page in ordered:
            path = str(page.get("path") or "").lstrip("/")
            if not path:
                continue
            urls.append([f"{host}/{path}" for host in hosts])
        if urls:
            return urls

    media_id = gallery.get("media_id")
    legacy = gallery.get("images") if isinstance(gallery.get("images"), dict) else None
    legacy_pages = legacy.get("pages") if isinstance(legacy, dict) else None
    if not media_id or not isinstance(legacy_pages, list):
        return []

    urls = []
    for index, page in enumerate(legacy_pages, 1):
        if not isinstance(page, dict):
            continue
        ext = EXT_BY_CODE.get(str(page.get("t", "")).lower())
        if not ext:
            continue
        path = f"galleries/{media_id}/{index}.{ext}"
        urls.append([f"{host}/{path}" for host in hosts])
    return urls


def detect_reader_mode(signals, url=""):
    """Choose vertical scroll or horizontal click from a loaded reader page.

    Vertical is the default so existing long-strip chapters keep their current path.
    Horizontal requires a positive reader signal, not just a short page.
    """
    signals = signals or {}
    if READER_PAGE_RE.search(url or ""):
        return "horizontal"

    view_height = signals.get("innerHeight") or 1
    ratio = (signals.get("scrollHeight") or 0) / max(view_height, 1)
    if (
        signals.get("hasStrip")
        or signals.get("lazyCount", 0) >= 4
        or signals.get("bigImgCount", 0) >= 4
        or ratio >= 3
    ):
        return "vertical"

    few_images = signals.get("bigImgCount", 0) <= 1
    snippet = signals.get("snippet") or ""
    counter = PAGE_COUNTER_RE.search(snippet)
    has_counter = bool(counter and int(counter.group(2)) > 1)
    if signals.get("hasReader") and few_images and ratio < 2.5:
        return "horizontal"
    if signals.get("hasNext") and few_images and has_counter and ratio < 1.6:
        return "horizontal"
    return "vertical"


def collect_click_pages(read_image, click_next, wait_for_change, max_pages=1000):
    """Walk a click-to-advance reader until the next page stops changing."""
    sources = []
    seen = set()
    misses = 0
    while len(sources) < max_pages:
        src = read_image()
        if not src:
            misses += 1
            if misses >= 4 or not wait_for_change(None):
                break
            continue
        misses = 0
        if src in seen:
            break
        seen.add(src)
        sources.append(src)
        if not click_next():
            break
        if not wait_for_change(src):
            break
    return sources


def save_as_jpeg(content, file_path):
    """Store every panel as a real JPEG so the stitcher can open it."""
    try:
        from PIL import Image
    except ImportError:
        if content[:2] == b"\xff\xd8":
            with open(file_path, "wb") as handle:
                handle.write(content)
            return True
        return False

    with Image.open(BytesIO(content)) as img:
        if getattr(img, "is_animated", False):
            img.seek(0)
        frame = img.copy()
    if frame.mode not in ("RGB", "L"):
        frame = frame.convert("RGB")
    frame.save(file_path, "JPEG", quality=90)
    return True


class MangaScraper:
    def __init__(self, output_dir="raw_chapters"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        })
        self._image_servers = None

    def _sync_browser_state(self, page):
        """Steals the Cookies and User-Agent safely across all DrissionPage versions."""
        try:
            raw_cookies = page.cookies()
            cookie_dict = {}

            if isinstance(raw_cookies, list):
                for cookie in raw_cookies:
                    if "name" in cookie and "value" in cookie:
                        cookie_dict[cookie["name"]] = cookie["value"]
            elif isinstance(raw_cookies, dict):
                cookie_dict = raw_cookies

            self.session.cookies.update(cookie_dict)
        except Exception as e:
            print(f"[Scraper Warning]: Cookie sync hiccuped. Attempting to proceed anyway. ({e})")

        try:
            user_agent = page.run_js("return navigator.userAgent;")
            self.session.headers.update({
                "User-Agent": user_agent,
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                "Referer": page.url,
            })
        except Exception as e:
            print(f"[Scraper Warning]: User-Agent sync failed. ({e})")

        print("[Scraper]: Synced browser state. Bypassing hotlink protections...")

    def _scroll_to_bottom(self, page):
        """Systematic deep-scroll to force all lazy-loaded images to render."""
        print("[Scraper]: Initiating deep-scroll to force lazy-loading...")
        previous_height = 0
        max_scrolls = 50
        scroll_count = 0

        while scroll_count < max_scrolls:
            page.scroll.down(800)
            time.sleep(0.8)

            current_height = page.run_js("return document.body.scrollHeight;")

            if current_height == previous_height:
                page.scroll.to_bottom()
                time.sleep(2)
                break

            previous_height = current_height
            scroll_count += 1

        print("[Scraper]: Reached the true bottom of the page.")

    def _api_headers(self, referer):
        return {
            "User-Agent": self.session.headers.get("User-Agent", BROWSER_USER_AGENT),
            "Accept": "application/json",
            "Referer": referer,
        }

    def _image_server_list(self):
        if self._image_servers:
            return self._image_servers
        try:
            response = self.session.get(
                "https://nhentai.net/api/v2/cdn",
                timeout=15,
                headers=self._api_headers("https://nhentai.net/"),
            )
            if response.status_code == 200:
                servers = response.json().get("image_servers") or []
                if servers:
                    self._image_servers = servers
                    return servers
        except Exception as e:
            print(f"[Scraper Warning]: Could not read image servers ({e}).")
        self._image_servers = list(DEFAULT_IMAGE_SERVERS)
        return self._image_servers

    def _fetch_nhentai_sources(self, gallery_id):
        """Use the official gallery API. The site asks clients not to scrape HTML."""
        referer = f"https://nhentai.net/g/{gallery_id}/"
        try:
            response = self.session.get(
                f"https://nhentai.net/api/v2/galleries/{gallery_id}",
                timeout=20,
                headers=self._api_headers(referer),
            )
        except Exception as e:
            print(f"[Scraper Warning]: nhentai API request failed ({e}).")
            return []
        if response.status_code != 200:
            print(f"[Scraper Warning]: nhentai API returned HTTP {response.status_code}.")
            return []
        try:
            gallery = response.json()
        except ValueError as e:
            print(f"[Scraper Warning]: nhentai API returned invalid JSON ({e}).")
            return []
        return nhentai_page_urls(gallery, self._image_server_list())

    def _reader_signals(self, page):
        try:
            signals = page.run_js(READER_SIGNALS_JS) or {}
        except Exception as e:
            print(f"[Scraper Warning]: Could not inspect the reader ({e}).")
            return {}
        if isinstance(signals, str):
            import json
            try:
                signals = json.loads(signals)
            except ValueError:
                return {}
        return signals if isinstance(signals, dict) else {}

    def _current_reader_image(self, page):
        try:
            src = page.run_js(CURRENT_IMAGE_JS)
        except Exception:
            return ""
        sources = filter_image_sources([src], getattr(page, "url", ""))
        return sources[0] if sources else ""

    def _click_next_page(self, page):
        try:
            result = page.run_js(CLICK_NEXT_JS)
        except Exception as e:
            print(f"[Scraper Warning]: Next-page click failed ({e}).")
            return False
        return result in ("yes", "key")

    def _wait_for_image_change(self, page, previous, timeout=8):
        deadline = time.time() + timeout
        while time.time() < deadline:
            current = self._current_reader_image(page)
            if current and current != previous:
                time.sleep(0.35)
                return True
            time.sleep(0.25)
        return False

    def _embedded_sources(self, page):
        try:
            raw = page.run_js(EMBEDDED_GALLERY_JS) or ""
        except Exception:
            return []
        if not raw:
            return []
        try:
            import json
            gallery = json.loads(raw)
        except ValueError:
            return []
        return nhentai_page_urls(gallery, self._image_server_list())

    def _collect_vertical(self, page):
        print("[Scraper]: Hunting for comic panels...")
        images = page.eles(".reading-content img") or page.eles(".page-break img") or page.eles("tag:img")
        raw_sources = []
        for img in images:
            src = img.attr("data-src") or img.attr("data-lazy-src") or img.attr("data-original") or img.attr("src")
            raw_sources.append(src)
        return filter_image_sources(raw_sources, page.url)

    def _collect_horizontal(self, page):
        embedded = self._embedded_sources(page)
        if len(embedded) >= 2:
            print(f"[Scraper]: Found {len(embedded)} pages in the reader data.")
            return embedded

        print("[Scraper]: Clicking through horizontal pages...")

        def read_image():
            return self._current_reader_image(page)

        def click_next():
            return self._click_next_page(page)

        def wait_for_change(previous):
            return self._wait_for_image_change(page, previous)

        sources = collect_click_pages(read_image, click_next, wait_for_change)
        print(f"[Scraper]: Click-through collected {len(sources)} pages.")
        return sources

    def _download_single_image(self, srcs, file_path, index, referer):
        """Worker function for concurrent downloading."""
        if isinstance(srcs, str):
            srcs = [srcs]
        last_error = "no url"
        for src in srcs:
            try:
                response = self.session.get(
                    src.strip(),
                    timeout=20,
                    headers={"Referer": referer, "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"},
                )
                if response.status_code != 200 or not response.content:
                    last_error = f"HTTP {response.status_code}"
                    continue
                if save_as_jpeg(response.content, file_path):
                    return index, file_path, True, None
                last_error = "not an image"
            except Exception as e:
                last_error = str(e)
        return index, srcs[0] if srcs else "", False, last_error

    def _download_sources(self, sources, chapter_dir, referer):
        if not sources:
            print("[Scraper]: No pages found.")
            return []

        print(f"[Scraper]: Found {len(sources)} clean panels. Initiating hyper-threaded download...")
        downloaded_files = []
        failed_downloads = []

        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_url = {
                executor.submit(
                    self._download_single_image,
                    src,
                    os.path.join(chapter_dir, f"page_{idx:03d}.jpg"),
                    idx,
                    referer,
                ): src for idx, src in enumerate(sources, 1)
            }

            for future in as_completed(future_to_url):
                idx, path_or_src, success, error = future.result()
                if success:
                    downloaded_files.append((idx, path_or_src))
                    print(f"  -> [OK] Saved page_{idx:03d}.jpg")
                else:
                    failed_downloads.append((idx, path_or_src))
                    print(f"  -> [!] Failed page_{idx:03d}.jpg ({error})")

        downloaded_files.sort(key=lambda item: item[0])
        final_paths = [path for idx, path in downloaded_files]
        print(f"\n[Scraper]: Success! Ripped {len(final_paths)} pages to '{chapter_dir}'.")
        if failed_downloads:
            print(f"[Scraper]: Note - {len(failed_downloads)} images failed to download.")
        return final_paths

    def _download_with_browser(self, full_url, chapter_dir):
        print(f"[Scraper]: Spinning up DrissionPage to hit: {full_url}")
        from DrissionPage import ChromiumPage, ChromiumOptions
        co = ChromiumOptions()
        co.set_browser_path("/usr/bin/google-chrome")

        page = None
        sources = []
        referer = full_url
        try:
            page = ChromiumPage(co)
            page.get(full_url)
            self._sync_browser_state(page)
            referer = page.url or full_url

            forced = os.getenv("READER_MODE", "auto").strip().lower()
            if forced in ("vertical", "horizontal"):
                mode = forced
            else:
                mode = detect_reader_mode(self._reader_signals(page), page.url)
            print(f"[Scraper]: Reader mode: {mode}.")

            if mode == "horizontal":
                sources = self._collect_horizontal(page)
            else:
                self._scroll_to_bottom(page)
                sources = self._collect_vertical(page)
            referer = page.url or referer
        except Exception as e:
            print(f"[Scraper]: Critical failure during scraping: {e}")
            return []
        finally:
            try:
                if page is not None:
                    page.quit()
            except Exception:
                pass

        return self._download_sources(sources, chapter_dir, referer)

    def download_chapter(self, base_url, chapter_number):
        """Download one chapter from either a vertical strip or a click-through reader.

        Vertical chapters keep the existing `{base}/{chapter}/` URL. An nhentai gallery
        uses the same shape with the gallery id as the chapter number
        (`https://nhentai.net/g` + `123456`), and is fetched from the official API.
        Other one-page readers are detected in the browser and advanced with the next control.
        Set READER_MODE to `vertical` or `horizontal` to override detection.
        """
        full_url = build_chapter_url(base_url, chapter_number)
        chapter_dir = os.path.join(self.output_dir, f"chapter_{chapter_number}")
        os.makedirs(chapter_dir, exist_ok=True)

        gallery_id = nhentai_gallery_id(full_url) or nhentai_gallery_id(base_url)
        if gallery_id:
            print(f"[Scraper]: Horizontal gallery {gallery_id}. Asking the nhentai API for pages...")
            sources = self._fetch_nhentai_sources(gallery_id)
            if sources:
                print(f"[Scraper]: API returned {len(sources)} full-size pages.")
                saved = self._download_sources(
                    sources,
                    chapter_dir,
                    referer=f"https://nhentai.net/g/{gallery_id}/",
                )
                if saved:
                    return saved
                print("[Scraper]: API images did not save. Opening the click reader instead.")
            else:
                print("[Scraper]: API path missed. Opening the click reader instead.")
            full_url = f"https://nhentai.net/g/{gallery_id}/1/"

        return self._download_with_browser(full_url, chapter_dir)
