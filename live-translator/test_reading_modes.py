import unittest

from detector import sort_bubbles
from PIL import Image
from scanner import FrameWatch, image_is_blank


class SortTests(unittest.TestCase):
    def test_vertical_order_is_top_to_bottom_then_left_to_right(self):
        bubbles = [
            {"x": 40, "y": 200, "w": 10, "h": 10},
            {"x": 10, "y": 200, "w": 10, "h": 10},
            {"x": 10, "y": 20, "w": 10, "h": 10},
        ]
        ordered = [(bubble["x"], bubble["y"]) for bubble in sort_bubbles(bubbles, "vertical")]
        self.assertEqual(ordered, [(10, 20), (10, 200), (40, 200)])

    def test_horizontal_order_reads_the_right_column_first(self):
        bubbles = [
            {"x": 40, "y": 20, "w": 80, "h": 40},
            {"x": 400, "y": 10, "w": 80, "h": 40},
            {"x": 420, "y": 200, "w": 80, "h": 40},
            {"x": 30, "y": 180, "w": 80, "h": 40},
        ]
        ordered = [(bubble["x"], bubble["y"]) for bubble in sort_bubbles(bubbles, "horizontal")]
        self.assertEqual(ordered, [(400, 10), (420, 200), (40, 20), (30, 180)])


class FrameWatchTests(unittest.TestCase):
    def test_waits_until_a_scrolled_frame_holds_still(self):
        watch = FrameWatch()
        watch.update("frame-a", blank=False, now=0)
        self.assertFalse(watch.ready(1.0, settle_seconds=2))
        self.assertTrue(watch.ready(2.0, settle_seconds=2))

    def test_a_click_resets_the_wait_and_a_repeat_does_not_translate_again(self):
        watch = FrameWatch()
        watch.update("page-1", blank=False, now=0)
        self.assertTrue(watch.ready(1, settle_seconds=1))
        watch.mark_translated()
        self.assertFalse(watch.ready(5, settle_seconds=1))

        watch.update("page-2", blank=False, now=6)
        self.assertFalse(watch.ready(6.2, settle_seconds=0.8))
        self.assertTrue(watch.ready(7, settle_seconds=0.8))

    def test_a_blank_loading_frame_is_not_ready(self):
        watch = FrameWatch()
        watch.update("white", blank=True, now=0)
        self.assertFalse(watch.ready(5, settle_seconds=1))

    def test_solid_flash_is_blank_and_a_drawn_page_is_not(self):
        self.assertTrue(image_is_blank(Image.new("RGB", (80, 80), "white")))
        drawn = Image.new("RGB", (80, 80), "white")
        for x in range(10, 70):
            drawn.putpixel((x, 40), (0, 0, 0))
        self.assertFalse(image_is_blank(drawn))


if __name__ == "__main__":
    unittest.main()
