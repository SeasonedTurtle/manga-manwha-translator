import unittest

from scraper import (
    build_chapter_url,
    collect_click_pages,
    detect_reader_mode,
    filter_image_sources,
    nhentai_gallery_id,
    nhentai_page_urls,
    save_as_jpeg,
)


class UrlTests(unittest.TestCase):
    def test_chapter_url_keeps_the_vertical_shape(self):
        self.assertEqual(
            build_chapter_url("https://rawdex.net/manga/title/", 24),
            "https://rawdex.net/manga/title/24/",
        )

    def test_gallery_id_from_gallery_and_reader_urls(self):
        self.assertEqual(nhentai_gallery_id("https://nhentai.net/g/123456/"), "123456")
        self.assertEqual(nhentai_gallery_id("https://nhentai.net/g/123456/3/"), "123456")
        self.assertIsNone(nhentai_gallery_id("https://rawdex.net/manga/title/24/"))


class GalleryUrlTests(unittest.TestCase):
    def test_v2_pages_are_ordered_and_mirrored_across_servers(self):
        gallery = {
            "media_id": "9",
            "pages": [
                {"number": 2, "path": "galleries/9/2.webp"},
                {"number": 1, "path": "galleries/9/1.jpg"},
            ],
        }
        urls = nhentai_page_urls(gallery, ["https://i1.nhentai.net", "https://i2.nhentai.net"])
        self.assertEqual(urls[0][0], "https://i1.nhentai.net/galleries/9/1.jpg")
        self.assertEqual(urls[1][1], "https://i2.nhentai.net/galleries/9/2.webp")

    def test_legacy_type_codes(self):
        gallery = {
            "media_id": "42",
            "images": {"pages": [{"t": "j"}, {"t": "p"}]},
        }
        urls = nhentai_page_urls(gallery, ["https://i3.nhentai.net"])
        self.assertEqual(
            urls,
            [
                ["https://i3.nhentai.net/galleries/42/1.jpg"],
                ["https://i3.nhentai.net/galleries/42/2.png"],
            ],
        )


class ModeTests(unittest.TestCase):
    def test_long_strip_stays_vertical(self):
        signals = {
            "scrollHeight": 12000,
            "innerHeight": 900,
            "bigImgCount": 1,
            "lazyCount": 8,
            "hasStrip": True,
            "hasReader": False,
            "hasNext": True,
            "snippet": "Page 1 / 40",
        }
        self.assertEqual(detect_reader_mode(signals), "vertical")

    def test_single_image_reader_is_horizontal(self):
        signals = {
            "scrollHeight": 1000,
            "innerHeight": 900,
            "bigImgCount": 1,
            "lazyCount": 0,
            "hasStrip": False,
            "hasReader": True,
            "hasNext": True,
            "snippet": "1 / 24",
        }
        self.assertEqual(detect_reader_mode(signals), "horizontal")

    def test_reader_url_is_horizontal_even_without_signals(self):
        self.assertEqual(detect_reader_mode({}, "https://nhentai.net/g/9/1/"), "horizontal")

    def test_unknown_short_page_stays_vertical(self):
        signals = {
            "scrollHeight": 1200,
            "innerHeight": 900,
            "bigImgCount": 2,
            "lazyCount": 0,
            "hasStrip": False,
            "hasReader": False,
            "hasNext": False,
            "snippet": "",
        }
        self.assertEqual(detect_reader_mode(signals), "vertical")


class ClickTests(unittest.TestCase):
    def test_clicks_until_the_reader_stops(self):
        pages = ["a.jpg", "b.jpg", "c.jpg"]
        state = {"index": 0}

        def read_image():
            return pages[state["index"]]

        def click_next():
            if state["index"] >= len(pages) - 1:
                return False
            state["index"] += 1
            return True

        def wait_for_change(previous):
            return read_image() != previous

        self.assertEqual(collect_click_pages(read_image, click_next, wait_for_change), pages)

    def test_stops_when_the_click_does_not_change_the_image(self):
        def read_image():
            return "only.jpg"

        self.assertEqual(
            collect_click_pages(read_image, lambda: True, lambda previous: False),
            ["only.jpg"],
        )

    def test_stops_when_the_gallery_loops(self):
        pages = ["a.jpg", "b.jpg", "a.jpg"]
        state = {"index": 0}

        def read_image():
            return pages[state["index"]]

        def click_next():
            state["index"] += 1
            return True

        self.assertEqual(
            collect_click_pages(read_image, click_next, lambda previous: True),
            ["a.jpg", "b.jpg"],
        )


class FilterTests(unittest.TestCase):
    def test_drops_ui_images_and_duplicates(self):
        sources = [
            "//cdn.example/page1.jpg",
            "https://cdn.example/logo.png",
            "https://cdn.example/page1.jpg",
            "blob:page",
        ]
        self.assertEqual(
            filter_image_sources(sources, "https://reader.example/chapter/1/"),
            ["https://cdn.example/page1.jpg"],
        )


class JpegTests(unittest.TestCase):
    def test_png_bytes_are_stored_as_jpeg(self):
        from io import BytesIO
        from PIL import Image

        buffer = BytesIO()
        Image.new("RGBA", (8, 8), (255, 0, 0, 128)).save(buffer, "PNG")
        path = "/tmp/scraper-page.jpg"
        self.assertTrue(save_as_jpeg(buffer.getvalue(), path))
        with Image.open(path) as saved:
            self.assertEqual(saved.format, "JPEG")
            self.assertEqual(saved.size, (8, 8))


if __name__ == "__main__":
    unittest.main()
